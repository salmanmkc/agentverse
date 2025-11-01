#!/usr/bin/env python3
"""
Modular Agent Training Pipeline
Provides granular control over the training process
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure we can import local modules
sys.path.insert(0, str(Path(__file__).parent))

from scraping.scraper import create_consent, ConsentManager
from finetuning import FineTuningOrchestrator
from config.settings import AGENT_CONFIGS, AgentConfig


class ModularTrainingPipeline:
    """Modular pipeline for individual training steps"""
    
    def __init__(self, config_file: str = "agent_training_config.json"):
        self.config_file = Path(config_file)
        self.config = self.load_config()
        
        self.consent_manager = ConsentManager()
        self.fine_tuner = FineTuningOrchestrator()
        
        # Ensure directories exist
        Path("data/training_status").mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> Dict[str, Any]:
        """Load training configuration"""
        if not self.config_file.exists():
            logger.error(f"❌ Config file not found: {self.config_file}")
            return {"agents": {}}
        
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    async def create_consents_for_all(self) -> Dict[str, str]:
        """Create consent records for all configured agents"""
        
        logger.info("🔐 Creating consent records for all agents...")
        consent_tokens = {}
        
        for agent_id, agent_config in self.config.get("agents", {}).items():
            person_name = agent_config["person_name"]
            email = agent_config["email"]
            platforms = agent_config["scraping_config"]["platforms"]
            
            logger.info(f"📝 Creating consent for {person_name}...")
            
            consent_token = self.consent_manager.create_consent_record(
                person_name=person_name,
                email=email,
                platforms=platforms,
                duration_days=30
            )
            
            consent_tokens[agent_id] = consent_token
            
            # Save individual consent info
            consent_file = Path(f"data/training_status/{agent_id}_consent.json")
            consent_data = {
                "agent_id": agent_id,
                "person_name": person_name,
                "email": email,
                "platforms": platforms,
                "consent_token": consent_token,
                "created_at": datetime.now().isoformat()
            }
            
            with open(consent_file, 'w') as f:
                json.dump(consent_data, f, indent=2)
            
            logger.info(f"✅ Consent created for {person_name} (Token: {consent_token[:8]}...)")
        
        # Save consolidated consent info
        all_consents_file = Path("data/training_status/all_consents.json")
        with open(all_consents_file, 'w') as f:
            json.dump({
                "created_at": datetime.now().isoformat(),
                "consent_tokens": consent_tokens
            }, f, indent=2)
        
        logger.info(f"💾 All consent records saved")
        return consent_tokens
    
    async def scrape_agent_data(self, agent_id: str, consent_token: Optional[str] = None) -> Optional[str]:
        """Scrape data for a specific agent"""
        
        if agent_id not in self.config.get("agents", {}):
            logger.error(f"❌ Agent {agent_id} not found in config")
            return None
        
        agent_config = self.config["agents"][agent_id]
        person_name = agent_config["person_name"]
        
        # Get or load consent token
        if not consent_token:
            consent_file = Path(f"data/training_status/{agent_id}_consent.json")
            if consent_file.exists():
                with open(consent_file, 'r') as f:
                    consent_data = json.load(f)
                    consent_token = consent_data["consent_token"]
            else:
                logger.error(f"❌ No consent token found for {agent_id}")
                logger.info("   Run: python train_pipeline.py create-consents")
                return None
        
        logger.info(f"🕸️  Scraping data for {person_name}...")
        
        try:
            from scraping.scraper import scrape_person_data
            
            platforms = agent_config["scraping_config"]["platforms"]
            scraped_file = await scrape_person_data(
                person_name,
                consent_token,
                platforms
            )
            
            # Save scraping status
            scrape_status_file = Path(f"data/training_status/{agent_id}_scrape.json")
            scrape_status = {
                "agent_id": agent_id,
                "person_name": person_name,
                "scraped_at": datetime.now().isoformat(),
                "scraped_file": scraped_file,
                "platforms": platforms,
                "status": "completed"
            }
            
            with open(scrape_status_file, 'w') as f:
                json.dump(scrape_status, f, indent=2)
            
            logger.info(f"✅ Data scraped for {person_name}")
            logger.info(f"   File: {scraped_file}")
            
            return scraped_file
            
        except Exception as e:
            logger.error(f"❌ Scraping failed for {person_name}: {e}")
            
            # Save error status
            scrape_status_file = Path(f"data/training_status/{agent_id}_scrape.json")
            scrape_status = {
                "agent_id": agent_id,
                "person_name": person_name,
                "scraped_at": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            }
            
            with open(scrape_status_file, 'w') as f:
                json.dump(scrape_status, f, indent=2)
            
            return None
    
    async def train_agent_model(self, agent_id: str) -> Dict[str, Any]:
        """Train model for a specific agent"""
        
        if agent_id not in self.config.get("agents", {}):
            logger.error(f"❌ Agent {agent_id} not found in config")
            return {"status": "failed", "error": "Agent not found in config"}
        
        agent_config = self.config["agents"][agent_id]
        person_name = agent_config["person_name"]
        
        logger.info(f"🧠 Training model for {person_name}...")
        
        # Check if data was scraped
        scrape_status_file = Path(f"data/training_status/{agent_id}_scrape.json")
        if not scrape_status_file.exists():
            logger.error(f"❌ No scrape data found for {agent_id}")
            logger.info("   Run: python train_pipeline.py scrape <agent_id>")
            return {"status": "failed", "error": "No scrape data found"}
        
        with open(scrape_status_file, 'r') as f:
            scrape_status = json.load(f)
        
        if scrape_status.get("status") != "completed":
            logger.error(f"❌ Scraping was not successful for {agent_id}")
            return {"status": "failed", "error": "Scraping not completed"}
        
        try:
            # Configure fine-tuner from config
            if "training_pipeline" in self.config:
                pipeline_config = self.config["training_pipeline"]
                self.fine_tuner.base_model_name = pipeline_config.get("base_model", "microsoft/DialoGPT-medium")
            
            # Run fine-tuning
            result = await self.fine_tuner.fine_tune_agent(
                person_name=person_name,
                agent_id=agent_id,
                resume_from_checkpoint=False
            )
            
            # Save training status
            training_status_file = Path(f"data/training_status/{agent_id}_training.json")
            training_status = {
                "agent_id": agent_id,
                "person_name": person_name,
                "trained_at": datetime.now().isoformat(),
                "result": result,
                "config": agent_config["training_config"]
            }
            
            with open(training_status_file, 'w') as f:
                json.dump(training_status, f, indent=2, default=str)
            
            if result.get("status") == "completed":
                logger.info(f"✅ Model trained for {person_name}")
                logger.info(f"   Model path: {result['model_path']}")
                logger.info(f"   Training samples: {result.get('train_samples', 'N/A')}")
            else:
                logger.error(f"❌ Training failed for {person_name}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Training failed for {person_name}: {e}")
            
            # Save error status
            training_status_file = Path(f"data/training_status/{agent_id}_training.json")
            training_status = {
                "agent_id": agent_id,
                "person_name": person_name,
                "trained_at": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            }
            
            with open(training_status_file, 'w') as f:
                json.dump(training_status, f, indent=2)
            
            return {"status": "failed", "error": str(e)}
    
    async def scrape_all_agents(self) -> Dict[str, Optional[str]]:
        """Scrape data for all configured agents"""
        
        logger.info("🕸️  Scraping data for all agents...")
        
        results = {}
        
        # Load consent tokens
        all_consents_file = Path("data/training_status/all_consents.json")
        if not all_consents_file.exists():
            logger.error("❌ No consent records found")
            logger.info("   Run: python train_pipeline.py create-consents")
            return {}
        
        with open(all_consents_file, 'r') as f:
            consents_data = json.load(f)
            consent_tokens = consents_data["consent_tokens"]
        
        # Scrape each agent in order
        for agent_id in self.config.get("agents", {}).keys():
            if agent_id in consent_tokens:
                result = await self.scrape_agent_data(agent_id, consent_tokens[agent_id])
                results[agent_id] = result
            else:
                logger.error(f"❌ No consent token for {agent_id}")
                results[agent_id] = None
        
        return results
    
    async def train_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Train models for all configured agents"""
        
        logger.info("🧠 Training models for all agents...")
        
        results = {}
        
        for agent_id in self.config.get("agents", {}).keys():
            result = await self.train_agent_model(agent_id)
            results[agent_id] = result
        
        return results
    
    def show_training_status(self):
        """Show training status for all agents"""
        
        logger.info("📊 Training Status Summary")
        logger.info("=" * 50)
        
        status_dir = Path("data/training_status")
        if not status_dir.exists():
            logger.info("📝 No training status found")
            return
        
        agents = self.config.get("agents", {})
        if not agents:
            logger.info("📝 No agents configured")
            return
        
        for agent_id, agent_config in agents.items():
            person_name = agent_config["person_name"]
            
            # Check consent
            consent_file = status_dir / f"{agent_id}_consent.json"
            consent_status = "✅" if consent_file.exists() else "❌"
            
            # Check scraping
            scrape_file = status_dir / f"{agent_id}_scrape.json"
            scrape_status = "❌"
            if scrape_file.exists():
                with open(scrape_file, 'r') as f:
                    scrape_data = json.load(f)
                    scrape_status = "✅" if scrape_data.get("status") == "completed" else "❌"
            
            # Check training
            training_file = status_dir / f"{agent_id}_training.json"
            training_status = "❌"
            if training_file.exists():
                with open(training_file, 'r') as f:
                    training_data = json.load(f)
                    if isinstance(training_data.get("result"), dict):
                        training_status = "✅" if training_data["result"].get("status") == "completed" else "❌"
                    else:
                        training_status = "✅" if training_data.get("status") == "completed" else "❌"
            
            logger.info(f"👤 {person_name}")
            logger.info(f"   Consent: {consent_status}  Scraped: {scrape_status}  Trained: {training_status}")
    
    def clean_training_data(self, agent_id: Optional[str] = None):
        """Clean training data files"""
        
        status_dir = Path("data/training_status")
        if not status_dir.exists():
            logger.info("📝 No training status directory found")
            return
        
        if agent_id:
            # Clean specific agent
            files_to_remove = [
                f"{agent_id}_consent.json",
                f"{agent_id}_scrape.json", 
                f"{agent_id}_training.json"
            ]
            
            for filename in files_to_remove:
                file_path = status_dir / filename
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"🗑️  Removed {filename}")
            
            logger.info(f"✅ Cleaned training data for {agent_id}")
        else:
            # Clean all
            import shutil
            if status_dir.exists():
                shutil.rmtree(status_dir)
                logger.info("🗑️  Removed all training status data")


# CLI Commands
async def create_consents():
    """Create consent records"""
    pipeline = ModularTrainingPipeline()
    await pipeline.create_consents_for_all()

async def scrape_agent(agent_id: str):
    """Scrape data for specific agent"""
    pipeline = ModularTrainingPipeline()
    await pipeline.scrape_agent_data(agent_id)

async def scrape_all():
    """Scrape data for all agents"""
    pipeline = ModularTrainingPipeline()
    await pipeline.scrape_all_agents()

async def train_agent(agent_id: str):
    """Train specific agent"""
    pipeline = ModularTrainingPipeline()
    await pipeline.train_agent_model(agent_id)

async def train_all():
    """Train all agents"""
    pipeline = ModularTrainingPipeline()
    await pipeline.train_all_agents()

def show_status():
    """Show training status"""
    pipeline = ModularTrainingPipeline()
    pipeline.show_training_status()

def clean_data(agent_id: Optional[str] = None):
    """Clean training data"""
    pipeline = ModularTrainingPipeline()
    pipeline.clean_training_data(agent_id)

def main():
    """Main CLI interface"""
    
    if len(sys.argv) < 2:
        print("🎯 Modular Agent Training Pipeline")
        print("=" * 40)
        print("Usage:")
        print("  python train_pipeline.py create-consents          # Create consent records")
        print("  python train_pipeline.py scrape <agent_id>        # Scrape specific agent")
        print("  python train_pipeline.py scrape-all               # Scrape all agents")
        print("  python train_pipeline.py train <agent_id>         # Train specific agent")
        print("  python train_pipeline.py train-all                # Train all agents")
        print("  python train_pipeline.py status                   # Show training status")
        print("  python train_pipeline.py clean [agent_id]         # Clean training data")
        print("\nExample workflow:")
        print("  1. python train_pipeline.py create-consents")
        print("  2. python train_pipeline.py scrape-all")
        print("  3. python train_pipeline.py train-all")
        print("  4. python train_pipeline.py status")
        return
    
    command = sys.argv[1]
    
    if command == "create-consents":
        asyncio.run(create_consents())
    elif command == "scrape" and len(sys.argv) > 2:
        agent_id = sys.argv[2]
        asyncio.run(scrape_agent(agent_id))
    elif command == "scrape-all":
        asyncio.run(scrape_all())
    elif command == "train" and len(sys.argv) > 2:
        agent_id = sys.argv[2]
        asyncio.run(train_agent(agent_id))
    elif command == "train-all":
        asyncio.run(train_all())
    elif command == "status":
        show_status()
    elif command == "clean":
        agent_id = sys.argv[2] if len(sys.argv) > 2 else None
        clean_data(agent_id)
    else:
        print(f"❌ Unknown command: {command}")
        print("Run 'python train_pipeline.py' for help")


if __name__ == "__main__":
    main()
