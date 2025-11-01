"""
Fine-tuning Orchestration System for Digital Twin Agents
Handles data preprocessing, model training, and agent personality development
"""
import asyncio
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import shutil

# ML/AI imports (optional)
try:
    import torch
    from transformers import (
        AutoTokenizer, 
        AutoModelForCausalLM,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling
    )
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, TaskType
    import pandas as pd
    ML_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  ML libraries not available: {e}")
    print("💡 Install with: pip install torch transformers datasets peft pandas")
    torch = None
    ML_AVAILABLE = False

from scraping.scraper import ScrapedMessage, scrape_person_data, create_consent
from config.settings import settings, AGENT_CONFIGS, AgentConfig
from communication.shared_knowledge import AgentCapabilities


class FineTuningOrchestrator:
    """Main orchestrator for fine-tuning digital twin agents"""
    
    def __init__(self):
        self.models_dir = Path(settings.MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.data_dir = Path("data/training")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Training configuration
        self.base_model_name = settings.BASE_MODEL_NAME
        self.max_length = settings.MAX_CONTEXT_LENGTH
        
        # LoRA configuration for efficient fine-tuning
        self.lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=8,  # Rank
            lora_alpha=32,
            lora_dropout=0.1,
            target_modules=["q_proj", "v_proj"]  # Target attention layers
        )
        
        self.training_history = {}
    
    async def setup_person_for_training(
        self, 
        person_name: str, 
        email: str,
        platforms: List[str] = None
    ) -> Dict[str, Any]:
        """Complete setup for a person's digital twin training"""
        
        print(f"🎯 Setting up digital twin training for {person_name}")
        
        try:
            # Step 1: Create consent record
            consent_token = create_consent(person_name, email, platforms)
            
            # Step 2: Scrape social media data
            if settings.SCRAPING_ENABLED:
                print(f"🔍 Scraping social media data for {person_name}...")
                scraped_data_file = await scrape_person_data(person_name, consent_token, platforms)
                print(f"✅ Data scraped and saved to: {scraped_data_file}")
            else:
                print("⚠️  Scraping disabled in settings. Using existing data if available.")
                scraped_data_file = None
            
            # Step 3: Process scraped data for training
            training_data = await self._process_scraped_data(person_name, scraped_data_file)
            
            # Step 4: Analyze communication patterns
            capabilities = await self._analyze_communication_patterns(training_data)
            
            # Step 5: Create agent configuration
            agent_config = self._create_agent_config(person_name, capabilities)
            
            # Save analyzed capabilities for later use in deployment
            capabilities_dict = {
                "technical_skills": capabilities.technical_skills,
                "preferred_task_types": capabilities.preferred_task_types,
                "work_style": capabilities.work_style,
                "communication_style": capabilities.communication_style
            }
            
            return {
                "person_name": person_name,
                "consent_token": consent_token,
                "scraped_data_file": scraped_data_file,
                "training_samples": len(training_data) if training_data else 0,
                "capabilities": capabilities_dict,
                "training_analyzed_capabilities": capabilities_dict,  # For deployment use
                "agent_config": agent_config.to_dict(),
                "ready_for_training": len(training_data) > 50 if training_data else False
            }
            
        except Exception as e:
            print(f"❌ Setup failed for {person_name}: {e}")
            return {
                "person_name": person_name,
                "error": str(e),
                "ready_for_training": False
            }
    
    async def fine_tune_agent(
        self, 
        person_name: str,
        agent_id: str = None,
        resume_from_checkpoint: bool = False
    ) -> Dict[str, Any]:
        """Fine-tune a model for a specific person"""
        
        print(f"🧠 Starting fine-tuning for {person_name}")
        
        if not ML_AVAILABLE:
            return {
                "person_name": person_name,
                "status": "failed",
                "error": "ML libraries not installed. Run: pip install torch transformers datasets peft",
                "ready_for_deployment": False
            }
        
        try:
            # Load training data
            training_data = await self._load_training_data(person_name)
            
            if not training_data or len(training_data) < 50:
                raise ValueError(f"Insufficient training data for {person_name} (need at least 50 samples)")
            
            # Prepare model and tokenizer
            print("🔄 Loading base model and tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
            
            # Add padding token if missing
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            # Apply LoRA
            print("🔧 Applying LoRA configuration...")
            model = get_peft_model(model, self.lora_config)
            model.print_trainable_parameters()
            
            # Prepare dataset
            print("📊 Preparing training dataset...")
            dataset = self._prepare_training_dataset(training_data, tokenizer)
            
            # Split dataset
            train_size = int(0.8 * len(dataset))
            train_dataset = dataset.select(range(train_size))
            eval_dataset = dataset.select(range(train_size, len(dataset)))
            
            # Configure training
            output_dir = self.models_dir / f"{person_name}_model"
            output_dir.mkdir(exist_ok=True)
            
            training_args = TrainingArguments(
                output_dir=str(output_dir),
                overwrite_output_dir=True,
                num_train_epochs=3,
                per_device_train_batch_size=4,
                per_device_eval_batch_size=4,
                gradient_accumulation_steps=2,
                eval_strategy="steps",
                eval_steps=100,
                save_steps=200,
                save_total_limit=2,
                load_best_model_at_end=True,
                logging_dir=str(output_dir / "logs"),
                logging_steps=50,
                learning_rate=5e-4,
                warmup_steps=100,
                fp16=torch.cuda.is_available(),
                dataloader_drop_last=True,
                report_to=None,  # Disable wandb/tensorboard
                remove_unused_columns=False
            )
            
            # Data collator
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=tokenizer,
                mlm=False,
                return_tensors="pt"
            )
            
            # Initialize trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                data_collator=data_collator,
                tokenizer=tokenizer
            )
            
            # Resume from checkpoint if requested
            if resume_from_checkpoint:
                checkpoint_path = self._find_latest_checkpoint(output_dir)
                if checkpoint_path:
                    print(f"🔄 Resuming from checkpoint: {checkpoint_path}")
            
            # Start training
            print("🚀 Starting fine-tuning...")
            start_time = datetime.now()
            
            trainer.train(resume_from_checkpoint=checkpoint_path if resume_from_checkpoint else None)
            
            end_time = datetime.now()
            training_duration = (end_time - start_time).total_seconds()
            
            # Save final model
            print("💾 Saving fine-tuned model...")
            trainer.save_model()
            tokenizer.save_pretrained(str(output_dir))
            
            # Update agent configuration only if training succeeded
            if agent_id:
                AGENT_CONFIGS[agent_id].model_path = str(output_dir)
                AGENT_CONFIGS[agent_id].fine_tuned = True
            
            # Record training history
            self.training_history[person_name] = {
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_seconds": training_duration,
                "train_samples": len(train_dataset),
                "eval_samples": len(eval_dataset),
                "model_path": str(output_dir),
                "final_eval_loss": trainer.state.log_history[-1].get("eval_loss", "N/A")
            }
            
            print(f"✅ Fine-tuning completed for {person_name}")
            print(f"⏱️  Training duration: {training_duration:.1f} seconds")
            print(f"📁 Model saved to: {output_dir}")
            
            return {
                "person_name": person_name,
                "status": "completed",
                "model_path": str(output_dir),
                "training_duration": training_duration,
                "train_samples": len(train_dataset),
                "eval_samples": len(eval_dataset),
                "ready_for_deployment": True
            }
            
        except Exception as e:
            print(f"❌ Fine-tuning failed for {person_name}: {e}")
            return {
                "person_name": person_name,
                "status": "failed",
                "error": str(e),
                "ready_for_deployment": False
            }
    
    async def batch_fine_tune_all_agents(self) -> Dict[str, Any]:
        """Fine-tune all configured agents"""
        
        print("🎯 Starting batch fine-tuning for all agents")
        
        results = {}
        
        for agent_id, agent_config in AGENT_CONFIGS.items():
            if agent_id == "manager":  # Skip manager for now
                continue
            
            print(f"\n🔄 Processing {agent_id} ({agent_config.person_name})")
            
            try:
                # Setup person for training
                setup_result = await self.setup_person_for_training(
                    agent_config.person_name,
                    f"{agent_config.person_name.lower().replace(' ', '.')}@company.com"  # Mock email
                )
                
                if setup_result.get("ready_for_training"):
                    # Fine-tune the model
                    training_result = await self.fine_tune_agent(
                        agent_config.person_name,
                        agent_id
                    )
                    results[agent_id] = training_result
                else:
                    results[agent_id] = {
                        "person_name": agent_config.person_name,
                        "status": "skipped",
                        "reason": "Not ready for training",
                        "setup_result": setup_result
                    }
                
            except Exception as e:
                print(f"❌ Failed to process {agent_id}: {e}")
                results[agent_id] = {
                    "person_name": agent_config.person_name,
                    "status": "error",
                    "error": str(e)
                }
        
        # Summary
        successful = len([r for r in results.values() if r.get("status") == "completed"])
        total = len(results)
        
        print(f"\n📊 Batch fine-tuning summary:")
        print(f"  Successful: {successful}/{total}")
        print(f"  Failed: {total - successful}/{total}")
        
        return {
            "batch_summary": {
                "total_agents": total,
                "successful": successful,
                "failed": total - successful,
                "completed_at": datetime.now().isoformat()
            },
            "individual_results": results
        }
    
    async def _process_scraped_data(self, person_name: str, scraped_data_file: Optional[str]) -> List[Dict[str, Any]]:
        """Process scraped social media data into training format"""
        
        if not scraped_data_file or not os.path.exists(scraped_data_file):
            print(f"⚠️  No scraped data file found for {person_name}")
            return []
        
        print(f"📊 Processing scraped data for {person_name}")
        
        try:
            with open(scraped_data_file, 'r', encoding='utf-8') as f:
                scraped_data = json.load(f)
            
            training_samples = []
            
            # Process each platform's data
            for platform, messages in scraped_data.get("data", {}).items():
                print(f"📱 Processing {len(messages)} messages from {platform}")
                
                for message_data in messages:
                    message = ScrapedMessage.from_dict(message_data)
                    
                    # Skip non-text messages or very short messages
                    if (message.message_type != "text" or 
                        not message.content or 
                        len(message.content.strip()) < 10):
                        continue
                    
                    # Create training sample
                    if message.sender == person_name:  # Only use messages sent by the person
                        # Create input-output pair for fine-tuning
                        # This is simplified - real implementation would be more sophisticated
                        training_sample = {
                            "input": f"Respond in the style of {person_name}:",
                            "output": message.content,
                            "platform": platform,
                            "conversation_context": message.conversation_id,
                            "metadata": message.metadata
                        }
                        
                        training_samples.append(training_sample)
            
            print(f"✅ Created {len(training_samples)} training samples for {person_name}")
            
            # Save processed training data
            training_file = self.data_dir / f"{person_name}_training_data.json"
            with open(training_file, 'w', encoding='utf-8') as f:
                json.dump(training_samples, f, indent=2, ensure_ascii=False)
            
            return training_samples
            
        except Exception as e:
            print(f"❌ Error processing scraped data: {e}")
            return []
    
    async def _analyze_communication_patterns(self, training_data: List[Dict[str, Any]]) -> AgentCapabilities:
        """Analyze communication patterns to determine agent capabilities"""
        
        if not training_data:
            return AgentCapabilities()
        
        print("🔍 Analyzing communication patterns...")
        
        # Extract messages for analysis
        messages = [sample["output"] for sample in training_data]
        
        # Simple pattern analysis (this would be more sophisticated in practice)
        technical_keywords = ['api', 'database', 'server', 'code', 'bug', 'deploy', 'git', 'technical']
        creative_keywords = ['design', 'creative', 'idea', 'concept', 'visual', 'brand', 'style']
        leadership_keywords = ['team', 'meeting', 'decision', 'strategy', 'plan', 'coordinate']
        
        # Count occurrences
        total_messages = len(messages)
        technical_count = sum(1 for msg in messages if any(kw in msg.lower() for kw in technical_keywords))
        creative_count = sum(1 for msg in messages if any(kw in msg.lower() for kw in creative_keywords))
        leadership_count = sum(1 for msg in messages if any(kw in msg.lower() for kw in leadership_keywords))
        
        # Calculate skill levels
        technical_skill = min(technical_count / total_messages * 2, 1.0)  # Scale to 0-1
        creative_skill = min(creative_count / total_messages * 2, 1.0)
        leadership_skill = min(leadership_count / total_messages * 2, 1.0)
        
        # Analyze communication style
        avg_message_length = sum(len(msg.split()) for msg in messages) / total_messages
        formal_indicators = sum(1 for msg in messages if any(word in msg.lower() for word in ['please', 'thank you', 'regards']))
        casual_indicators = sum(1 for msg in messages if any(word in msg.lower() for word in ['hey', 'awesome', 'cool', '!'*2]))
        
        formality = formal_indicators / total_messages
        casualness = casual_indicators / total_messages
        
        # Determine work style preferences
        collaborative_indicators = sum(1 for msg in messages if any(word in msg.lower() for word in ['we', 'team', 'together', 'collaborate']))
        independent_indicators = sum(1 for msg in messages if any(word in msg.lower() for word in ['i', 'my', 'myself', 'alone']))
        
        collaboration_score = collaborative_indicators / total_messages
        independence_score = independent_indicators / total_messages
        
        capabilities = AgentCapabilities(
            technical_skills={
                "technical": technical_skill,
                "creative": creative_skill,
                "leadership": leadership_skill,
                "communication": 0.7  # Base level
            },
            preferred_task_types=self._infer_preferred_tasks(technical_skill, creative_skill, leadership_skill),
            work_style={
                "collaborative": collaboration_score > independence_score,
                "independent": independence_score > collaboration_score,
                "detail_oriented": avg_message_length > 15,  # Longer messages suggest detail orientation
                "fast_paced": avg_message_length < 10  # Shorter messages suggest fast pace
            },
            communication_style={
                "formal": formality,
                "casual": casualness,
                "verbose": avg_message_length > 20,
                "concise": avg_message_length < 8
            }
        )
        
        print(f"📊 Communication analysis complete:")
        print(f"  Technical skill: {technical_skill:.2f}")
        print(f"  Creative skill: {creative_skill:.2f}")
        print(f"  Leadership skill: {leadership_skill:.2f}")
        print(f"  Avg message length: {avg_message_length:.1f} words")
        print(f"  Formality: {formality:.2f}")
        
        return capabilities
    
    def _infer_preferred_tasks(self, technical: float, creative: float, leadership: float) -> List[str]:
        """Infer preferred task types from skill analysis"""
        
        preferred = []
        
        if technical > 0.3:
            preferred.extend(["Technical content", "API Documentation", "System Architecture"])
        
        if creative > 0.3:
            preferred.extend(["Visual", "Design", "Creative content"])
        
        if leadership > 0.3:
            preferred.extend(["Planning", "Coordination", "Team management"])
        
        # Default categories
        if not preferred:
            preferred = ["Narrative", "General"]
        
        return preferred
    
    def _create_agent_config(self, person_name: str, capabilities: AgentCapabilities) -> AgentConfig:
        """Create agent configuration from analyzed capabilities"""
        
        # Generate agent ID from person name
        agent_id = person_name.lower().replace(' ', '_')
        
        return AgentConfig(
            agent_id=agent_id,
            person_name=person_name,
            capabilities=capabilities.technical_skills
        )
    
    async def _load_training_data(self, person_name: str) -> List[Dict[str, Any]]:
        """Load training data for a person"""
        
        training_file = self.data_dir / f"{person_name}_training_data.json"
        
        if not training_file.exists():
            return []
        
        try:
            with open(training_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading training data: {e}")
            return []
    
    def _prepare_training_dataset(self, training_data: List[Dict[str, Any]], tokenizer) -> Dataset:
        """Prepare training dataset for fine-tuning"""
        
        # Create input-output pairs in chat format
        formatted_data = []
        
        for sample in training_data:
            # Create conversation format
            conversation = f"{sample['input']} {sample['output']}"
            
            # Tokenize
            tokenized = tokenizer(
                conversation,
                truncation=True,
                padding=True,
                max_length=self.max_length,
                return_tensors=None
            )
            
            # Add labels (same as input_ids for causal LM)
            tokenized["labels"] = tokenized["input_ids"].copy()
            
            formatted_data.append(tokenized)
        
        return Dataset.from_list(formatted_data)
    
    def _find_latest_checkpoint(self, output_dir: Path) -> Optional[str]:
        """Find the latest checkpoint in the output directory"""
        
        checkpoint_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith('checkpoint-')]
        
        if not checkpoint_dirs:
            return None
        
        # Sort by checkpoint number
        checkpoint_dirs.sort(key=lambda x: int(x.name.split('-')[1]))
        
        return str(checkpoint_dirs[-1])
    
    def get_training_status(self) -> Dict[str, Any]:
        """Get status of all training jobs"""
        
        return {
            "training_history": self.training_history,
            "models_available": [d.name for d in self.models_dir.iterdir() if d.is_dir()],
            "base_model": self.base_model_name,
            "models_dir": str(self.models_dir)
        }


# CLI functions for easy usage
async def setup_agent_data(person_name: str, email: str, platforms: List[str] = None):
    """CLI function to setup agent data collection"""
    
    orchestrator = FineTuningOrchestrator()
    result = await orchestrator.setup_person_for_training(person_name, email, platforms)
    
    print("\n📋 Setup Results:")
    print(json.dumps(result, indent=2))
    
    return result


async def train_agent(person_name: str, agent_id: str = None):
    """CLI function to train a single agent"""
    
    orchestrator = FineTuningOrchestrator()
    result = await orchestrator.fine_tune_agent(person_name, agent_id)
    
    print("\n📋 Training Results:")
    print(json.dumps(result, indent=2))
    
    return result


async def train_all_agents():
    """CLI function to train all agents"""
    
    orchestrator = FineTuningOrchestrator()
    results = await orchestrator.batch_fine_tune_all_agents()
    
    print("\n📋 Batch Training Results:")
    print(json.dumps(results, indent=2))
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup" and len(sys.argv) >= 4:
            person_name = sys.argv[2]
            email = sys.argv[3]
            platforms = sys.argv[4:] if len(sys.argv) > 4 else None
            asyncio.run(setup_agent_data(person_name, email, platforms))
            
        elif command == "train" and len(sys.argv) >= 3:
            person_name = sys.argv[2]
            agent_id = sys.argv[3] if len(sys.argv) > 3 else None
            asyncio.run(train_agent(person_name, agent_id))
            
        elif command == "train_all":
            asyncio.run(train_all_agents())
            
        else:
            print("Usage:")
            print("  python finetuning.py setup <person_name> <email> [platform1] [platform2] ...")
            print("  python finetuning.py train <person_name> [agent_id]")
            print("  python finetuning.py train_all")
    else:
        print("🎯 Digital Twin Fine-tuning System")
        print("Run with --help for usage instructions")
