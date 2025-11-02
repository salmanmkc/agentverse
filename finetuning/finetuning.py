#!/usr/bin/env python3
"""
QLoRA Fine-tuning Script for GPT-OSS-20B
Optimized for cloud GPU deployment (24GB+ VRAM)
"""
import os
import json
import torch
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling
    )
    from peft import (
        LoraConfig,
        get_peft_model,
        prepare_model_for_kbit_training,
        TaskType
    )
    from datasets import load_dataset
    import bitsandbytes as bnb
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install transformers accelerate peft datasets bitsandbytes")
    raise


@dataclass
class TrainingConfig:
    """Training configuration"""
    # Model
    model_name: str = "unsloth/gpt-oss-20b"  # or "gpt-oss-20b" if available on HF
    trust_remote_code: bool = True
    
    # Data
    train_file: str = "data/training/train.jsonl"
    validation_file: str = "data/training/valid.jsonl"
    
    # LoRA
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: list = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])
    
    # Quantization (QLoRA)
    load_in_4bit: bool = True
    load_in_8bit: bool = False
    bnb_4bit_compute_dtype: str = "float16"
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_use_double_quant: bool = True
    
    # Training
    output_dir: str = "./adapters/ryan_lin"
    per_device_train_batch_size: int = 1
    per_device_eval_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    num_train_epochs: int = 1
    max_steps: int = -1  # -1 to use epochs
    warmup_steps: int = 100
    logging_steps: int = 10
    eval_steps: int = 100
    save_steps: int = 500
    save_total_limit: int = 3
    evaluation_strategy: str = "steps"
    save_strategy: str = "steps"
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_loss"
    greater_is_better: bool = False
    
    # Sequence
    max_seq_length: int = 1024
    padding_side: str = "right"
    
    # Optimization
    gradient_checkpointing: bool = True
    optim: str = "paged_adamw_32bit"
    weight_decay: float = 0.01
    lr_scheduler_type: str = "cosine"
    
    # Other
    fp16: bool = True
    bf16: bool = False
    dataloader_num_workers: int = 4
    report_to: list = field(default_factory=list)  # ["tensorboard", "wandb"]
    
    # System
    seed: int = 42
    ddp_find_unused_parameters: bool = False


class FineTuner:
    """Fine-tune GPT-OSS-20B with QLoRA"""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.trainer = None
    
    def load_model_and_tokenizer(self):
        """Load model and tokenizer with quantization"""
        print(f"📥 Loading model: {self.config.model_name}")
        
        # Compute dtype for 4-bit
        compute_dtype = getattr(torch, self.config.bnb_4bit_compute_dtype)
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            trust_remote_code=self.config.trust_remote_code,
            padding_side=self.config.padding_side
        )
        
        # Add pad token if missing
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        
        # Load model with 4-bit quantization
        if self.config.load_in_4bit:
            print("🔧 Loading model in 4-bit (QLoRA)...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                trust_remote_code=self.config.trust_remote_code,
                load_in_4bit=True,
                device_map="auto",
                quantization_config={
                    "load_in_4bit": True,
                    "bnb_4bit_compute_dtype": compute_dtype,
                    "bnb_4bit_quant_type": self.config.bnb_4bit_quant_type,
                    "bnb_4bit_use_double_quant": self.config.bnb_4bit_use_double_quant,
                },
                torch_dtype=compute_dtype,
            )
        elif self.config.load_in_8bit:
            print("🔧 Loading model in 8-bit...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                trust_remote_code=self.config.trust_remote_code,
                load_in_8bit=True,
                device_map="auto",
            )
        else:
            print("🔧 Loading model in full precision (requires >40GB VRAM)...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                trust_remote_code=self.config.trust_remote_code,
                device_map="auto",
                torch_dtype=torch.bfloat16 if self.config.bf16 else torch.float16,
            )
        
        # Prepare model for k-bit training
        if self.config.load_in_4bit or self.config.load_in_8bit:
            self.model = prepare_model_for_kbit_training(self.model)
        
        # Enable gradient checkpointing
        if self.config.gradient_checkpointing:
            self.model.gradient_checkpointing_enable()
        
        print("✅ Model and tokenizer loaded")
    
    def setup_lora(self):
        """Setup LoRA adapters"""
        print(f"🔧 Setting up LoRA with r={self.config.lora_r}, alpha={self.config.lora_alpha}")
        
        lora_config = LoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            target_modules=self.config.lora_target_modules,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )
        
        self.model = get_peft_model(self.model, lora_config)
        
        # Print trainable parameters
        self.model.print_trainable_parameters()
        print("✅ LoRA adapters configured")
    
    def load_dataset(self):
        """Load and preprocess dataset"""
        print(f"📂 Loading dataset from {self.config.train_file}")
        
        # Load JSONL files
        def load_jsonl(filepath):
            data = []
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
            return data
        
        train_data = load_jsonl(self.config.train_file)
        valid_data = load_jsonl(self.config.validation_file)
        
        print(f"   Training examples: {len(train_data)}")
        print(f"   Validation examples: {len(valid_data)}")
        
        # Convert to dataset format
        train_dataset = [self._format_example(ex) for ex in train_data]
        valid_dataset = [self._format_example(ex) for ex in valid_data]
        
        return train_dataset, valid_dataset
    
    def _format_example(self, example: dict) -> str:
        """Format SFT example to prompt format"""
        instruction = example.get('instruction', '')
        input_text = example.get('input', '')
        output = example.get('output', '')
        
        # Build prompt
        if input_text:
            prompt = f"{instruction}\n{input_text}\n{output}"
        else:
            prompt = f"{instruction}\n{output}"
        
        return prompt
    
    def tokenize_dataset(self, examples: list):
        """Tokenize dataset"""
        print("🔤 Tokenizing dataset...")
        
        # Tokenize each example
        tokenized_list = []
        for ex in examples:
            # Tokenize single example
            tokenized = self.tokenizer(
                ex,
                truncation=True,
                max_length=self.config.max_seq_length,
                padding="max_length",
                return_tensors=None,
            )
            
            # Labels are same as input_ids for causal LM
            tokenized["labels"] = tokenized["input_ids"].copy()
            
            tokenized_list.append(tokenized)
        
        return tokenized_list
    
    def train(self):
        """Run training"""
        print("🚀 Starting training...")
        
        # Load model and tokenizer
        self.load_model_and_tokenizer()
        self.setup_lora()
        
        # Load dataset
        train_data, valid_data = self.load_dataset()
        
        # Tokenize
        train_tokenized = self.tokenize_dataset(train_data)
        valid_tokenized = self.tokenize_dataset(valid_data)
        
        # Convert to dataset format compatible with Trainer
        # Trainer can work with list of dicts, but we'll ensure proper format
        from datasets import Dataset
        
        # Convert list of dicts to Dataset
        train_dataset = Dataset.from_list(train_tokenized)
        eval_dataset = Dataset.from_list(valid_tokenized)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            per_device_eval_batch_size=self.config.per_device_eval_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            num_train_epochs=self.config.num_train_epochs,
            max_steps=self.config.max_steps if self.config.max_steps > 0 else -1,
            warmup_steps=self.config.warmup_steps,
            logging_steps=self.config.logging_steps,
            eval_steps=self.config.eval_steps,
            save_steps=self.config.save_steps,
            save_total_limit=self.config.save_total_limit,
            evaluation_strategy=self.config.evaluation_strategy,
            save_strategy=self.config.save_strategy,
            load_best_model_at_end=self.config.load_best_model_at_end,
            metric_for_best_model=self.config.metric_for_best_model,
            greater_is_better=self.config.greater_is_better,
            gradient_checkpointing=self.config.gradient_checkpointing,
            optim=self.config.optim,
            weight_decay=self.config.weight_decay,
            lr_scheduler_type=self.config.lr_scheduler_type,
            fp16=self.config.fp16,
            bf16=self.config.bf16,
            dataloader_num_workers=self.config.dataloader_num_workers,
            report_to=self.config.report_to,
            seed=self.config.seed,
            ddp_find_unused_parameters=self.config.ddp_find_unused_parameters,
        )
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,  # Causal LM, not masked LM
        )
        
        # Create trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
        )
        
        # Train
        print("\n🎯 Training started!")
        train_result = self.trainer.train()
        
        # Save final model
        print(f"\n💾 Saving final model to {self.config.output_dir}")
        self.trainer.save_model()
        self.tokenizer.save_pretrained(self.config.output_dir)
        
        # Save training metrics
        metrics_file = Path(self.config.output_dir) / "training_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(train_result.metrics, f, indent=2)
        
        print("✅ Training complete!")
        print(f"📊 Final metrics: {train_result.metrics}")


def main():
    """Main training function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fine-tune GPT-OSS-20B with QLoRA')
    parser.add_argument(
        '--model-name',
        type=str,
        default='unsloth/gpt-oss-20b',
        help='Model name or path'
    )
    parser.add_argument(
        '--train-file',
        type=str,
        default='data/training/train.jsonl',
        help='Training JSONL file'
    )
    parser.add_argument(
        '--validation-file',
        type=str,
        default='data/training/valid.jsonl',
        help='Validation JSONL file'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./adapters/ryan_lin',
        help='Output directory for adapters'
    )
    parser.add_argument(
        '--lora-r',
        type=int,
        default=16,
        help='LoRA rank'
    )
    parser.add_argument(
        '--lora-alpha',
        type=int,
        default=32,
        help='LoRA alpha'
    )
    parser.add_argument(
        '--learning-rate',
        type=float,
        default=2e-4,
        help='Learning rate'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1,
        help='Per-device batch size'
    )
    parser.add_argument(
        '--gradient-accumulation-steps',
        type=int,
        default=8,
        help='Gradient accumulation steps'
    )
    parser.add_argument(
        '--max-steps',
        type=int,
        default=-1,
        help='Maximum training steps (-1 for epochs)'
    )
    parser.add_argument(
        '--num-epochs',
        type=int,
        default=1,
        help='Number of training epochs'
    )
    parser.add_argument(
        '--no-4bit',
        action='store_true',
        help='Disable 4-bit quantization (use full precision or 8-bit)'
    )
    parser.add_argument(
        '--8bit',
        action='store_true',
        help='Use 8-bit quantization instead of 4-bit'
    )
    
    args = parser.parse_args()
    
    # Create config
    config = TrainingConfig(
        model_name=args.model_name,
        train_file=args.train_file,
        validation_file=args.validation_file,
        output_dir=args.output_dir,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        max_steps=args.max_steps,
        num_train_epochs=args.num_epochs,
        load_in_4bit=not args.no_4bit and not args.8bit,
        load_in_8bit=args.8bit,
    )
    
    # Create trainer and run
    trainer = FineTuner(config)
    trainer.train()


if __name__ == '__main__':
    main()

