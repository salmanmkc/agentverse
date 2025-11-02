#!/usr/bin/env python3
"""
Evaluation Script for Fine-tuned Model
Tests persona fidelity with held-out prompts
"""
import os
import json
import torch
from pathlib import Path
from typing import List, Dict, Any
import random

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import bitsandbytes as bnb
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install transformers peft bitsandbytes")
    raise


class ModelEvaluator:
    """Evaluate fine-tuned model on held-out prompts"""
    
    def __init__(
        self,
        base_model_name: str,
        adapter_path: str,
        persona_name: str = "Ryan Lin"
    ):
        """
        Initialize evaluator
        
        Args:
            base_model_name: Base model name/path
            adapter_path: Path to LoRA adapter
            persona_name: Persona name for evaluation
        """
        self.base_model_name = base_model_name
        self.adapter_path = adapter_path
        self.persona_name = persona_name
        self.model = None
        self.tokenizer = None
    
    def load_model(self):
        """Load base model and adapter"""
        print(f"📥 Loading base model: {self.base_model_name}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_name,
            trust_remote_code=True
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model with 4-bit quantization for inference
        self.model = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            trust_remote_code=True,
            load_in_4bit=True,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        
        # Load adapter
        print(f"📥 Loading adapter from: {self.adapter_path}")
        self.model = PeftModel.from_pretrained(self.model, self.adapter_path)
        self.model.eval()
        
        print("✅ Model loaded")
    
    def generate_response(
        self,
        prompt: str,
        max_length: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True
    ) -> str:
        """Generate response to prompt"""
        # Format prompt with persona
        full_prompt = f"SYSTEM: You are {self.persona_name}. Respond as {self.persona_name} would in a professional workplace context.\nUSER: {prompt}\nASSISTANT:"
        
        # Tokenize
        inputs = self.tokenizer(
            full_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1024
        ).to(self.model.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        # Decode
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract assistant response
        if "ASSISTANT:" in generated_text:
            response = generated_text.split("ASSISTANT:")[-1].strip()
        else:
            response = generated_text[len(full_prompt):].strip()
        
        return response
    
    def evaluate_prompts(
        self,
        prompts: List[Dict[str, Any]],
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluate model on list of prompts
        
        Args:
            prompts: List of prompt dictionaries with 'prompt' and optional 'expected_topic'
            save_results: Whether to save results to file
        """
        print(f"🔍 Evaluating {len(prompts)} prompts...")
        
        results = []
        
        for i, prompt_data in enumerate(prompts):
            prompt = prompt_data.get('prompt', prompt_data) if isinstance(prompt_data, dict) else prompt_data
            expected_topic = prompt_data.get('expected_topic', '') if isinstance(prompt_data, dict) else ''
            
            print(f"\n⏳ [{i+1}/{len(prompts)}] Prompt: {prompt[:60]}...")
            
            response = self.generate_response(prompt)
            
            result = {
                'prompt': prompt,
                'expected_topic': expected_topic,
                'response': response,
                'response_length': len(response),
            }
            
            results.append(result)
            
            print(f"✅ Generated response ({len(response)} chars)")
        
        # Summary
        avg_length = sum(r['response_length'] for r in results) / len(results)
        
        summary = {
            'total_prompts': len(prompts),
            'average_response_length': avg_length,
            'results': results
        }
        
        # Save results
        if save_results:
            output_file = Path(self.adapter_path) / "evaluation_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Results saved to {output_file}")
        
        return summary


def load_evaluation_prompts(filepath: str) -> List[Dict[str, Any]]:
    """Load evaluation prompts from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and 'prompts' in data:
        return data['prompts']
    else:
        return []


def create_default_prompts() -> List[Dict[str, Any]]:
    """Create default evaluation prompts"""
    return [
        {
            "prompt": "Please update the Q3 deck with week 2 metrics.",
            "expected_topic": "task_assignment"
        },
        {
            "prompt": "Can you review my code for the ML model?",
            "expected_topic": "code_review"
        },
        {
            "prompt": "What's your opinion on using transformers for this project?",
            "expected_topic": "technical_advice"
        },
        {
            "prompt": "Can we schedule a meeting to discuss the project timeline?",
            "expected_topic": "scheduling"
        },
        {
            "prompt": "I need help understanding the API documentation.",
            "expected_topic": "assistance_request"
        },
        {
            "prompt": "What's the status of the bug fix?",
            "expected_topic": "status_update"
        },
        {
            "prompt": "Can you explain quantum computing concepts to the team?",
            "expected_topic": "technical_explanation"
        },
        {
            "prompt": "Do you think we should extend the deadline?",
            "expected_topic": "decision_making"
        },
        {
            "prompt": "Can you provide feedback on my proposal?",
            "expected_topic": "feedback"
        },
        {
            "prompt": "What resources do we need for the upcoming project?",
            "expected_topic": "resource_planning"
        },
    ]


def main():
    """Main evaluation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate fine-tuned model')
    parser.add_argument(
        '--base-model',
        type=str,
        default='unsloth/gpt-oss-20b',
        help='Base model name or path'
    )
    parser.add_argument(
        '--adapter-path',
        type=str,
        required=True,
        help='Path to LoRA adapter'
    )
    parser.add_argument(
        '--persona-name',
        type=str,
        default='Ryan Lin',
        help='Persona name'
    )
    parser.add_argument(
        '--prompts-file',
        type=str,
        help='JSON file with evaluation prompts'
    )
    parser.add_argument(
        '--num-prompts',
        type=int,
        help='Number of prompts to evaluate (if using default)'
    )
    
    args = parser.parse_args()
    
    # Load prompts
    if args.prompts_file and Path(args.prompts_file).exists():
        prompts = load_evaluation_prompts(args.prompts_file)
    else:
        prompts = create_default_prompts()
        if args.num_prompts:
            prompts = random.sample(prompts, min(args.num_prompts, len(prompts)))
    
    # Create evaluator
    evaluator = ModelEvaluator(
        base_model_name=args.base_model,
        adapter_path=args.adapter_path,
        persona_name=args.persona_name
    )
    
    # Load model
    evaluator.load_model()
    
    # Evaluate
    results = evaluator.evaluate_prompts(prompts)
    
    print(f"\n✅ Evaluation complete!")
    print(f"📊 Evaluated {results['total_prompts']} prompts")
    print(f"📊 Average response length: {results['average_response_length']:.0f} characters")


if __name__ == '__main__':
    main()

