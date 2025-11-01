#!/usr/bin/env python3
"""
Complete Agent Training & Deployment Pipeline
From URLs → Scraped Data → Trained Models → Deployed Agents
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure we can import local modules
sys.path.insert(0, str(Path(__file__).parent))

try:
    from scraping.scraper import SocialMediaScraper, create_consent, ConsentManager
    from finetuning import FineTuningOrchestrator
    from config.settings import settings, AGENT_CONFIGS
    from communication.shared_knowledge import shared_knowledge, AgentCapabilities
    from communication.protocol import communication_protocol
    from agents.manager_agent import ManagerAgent
    from agents.worker_agent import WorkerAgent
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error("Make sure you're running from the digital_twin_backend directory")
    sys.exit(1)


class CompleteAgentPipeline:
    """End-to-end pipeline: URLs → Scraping → Training → Deployment"""
    
    def __init__(self, config_file: str = "agent_training_config.json"):
        self.config_file = Path(config_file)
        self.config = self.load_config()
        
        # Initialize components
        self.consent_manager = ConsentManager()
        self.fine_tuner = FineTuningOrchestrator()
        
        # Status tracking
        self.pipeline_status = {
            "started_at": datetime.now().isoformat(),
            "current_phase": "initialization",
            "agents_status": {},
            "deployed_agents": {},
            "pipeline_config": self.config["training_pipeline"]
        }
        
        # Create directories
        self.ensure_directories()
    
    def load_config(self) -> Dict[str, Any]:
        """Load training configuration"""
        if not self.config_file.exists():
            logger.error(f"❌ Config file not found: {self.config_file}")
            logger.info("🔧 Create agent_training_config.json with your team's information")
            sys.exit(1)
        
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        
        logger.info(f"✅ Loaded config for {len(config['agents'])} agents")
        return config
    
    def ensure_directories(self):
        """Create necessary directories"""
        dirs = [
            "data/scraped",
            "data/training", 
            "data/consent",
            "data/browser_profiles",
            "models",
            "logs"
        ]
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        logger.info("📁 Created necessary directories")
    
    def check_prerequisites(self) -> bool:
        """Check if system has necessary prerequisites"""
        logger.info("🔍 Checking prerequisites...")
        
        # Check for required packages
        required_packages = [
            'selenium', 'transformers', 'torch', 'datasets', 'peft'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.error(f"❌ Missing packages: {', '.join(missing_packages)}")
            logger.info("📦 Install with: pip install -r requirements.txt")
            return False
        
        # Check Chrome/ChromeDriver for scraping
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(options=options)
            driver.quit()
            logger.info("✅ Chrome/ChromeDriver available")
        except Exception as e:
            logger.warning(f"⚠️  Chrome/ChromeDriver issue: {e}")
            logger.info("   Scraping may require manual setup")
        
        logger.info("✅ Prerequisites check complete")
        return True
    
    async def phase_1_setup_consents(self) -> Dict[str, str]:
        """Phase 1: Setup consent for all agents"""
        
        logger.info("🔐 Phase 1: Setting up consent records...")
        self.pipeline_status["current_phase"] = "consent_setup"
        
        consent_tokens = {}
        
        for agent_id, agent_config in self.config["agents"].items():
            person_name = agent_config["person_name"]
            email = agent_config["email"]
            platforms = agent_config["scraping_config"]["platforms"]
            
            logger.info(f"📝 Setting up consent for {person_name}...")
            
            # Create consent token
            consent_token = self.consent_manager.create_consent_record(
                person_name=person_name,
                email=email,
                platforms=platforms,
                duration_days=30
            )
            
            consent_tokens[agent_id] = consent_token
            
            # Update status
            self.pipeline_status["agents_status"][agent_id] = {
                "person_name": person_name,
                "email": email,
                "consent_token": consent_token,
                "consent_setup": True,
                "platforms": platforms,
                "social_accounts": agent_config["social_accounts"]
            }
            
            logger.info(f"✅ Consent setup complete for {person_name} (Token: {consent_token[:8]}...)")
        
        return consent_tokens
    
    async def phase_2_scrape_data(self, consent_tokens: Dict[str, str]) -> Dict[str, str]:
        """Phase 2: Scrape social media data using provided URLs"""
        
        logger.info("🕸️  Phase 2: Scraping social media data...")
        self.pipeline_status["current_phase"] = "data_scraping"
        
        scraped_files = {}
        
        # Sort by scraping priority
        agents_by_priority = sorted(
            self.config["agents"].items(),
            key=lambda x: x[1]["scraping_config"]["scrape_priority"]
        )
        
        for agent_id, agent_config in agents_by_priority:
            person_name = agent_config["person_name"]
            social_accounts = agent_config["social_accounts"]
            scraping_config = agent_config["scraping_config"]
            
            logger.info(f"\n🔄 Scraping data for {person_name} (Priority {scraping_config['scrape_priority']})...")
            logger.info(f"   Platforms: {scraping_config['platforms']}")
            
            # Display account info for verification
            for platform in scraping_config["platforms"]:
                if platform == "whatsapp" and social_accounts.get('whatsapp_phone'):
                    logger.info(f"   📱 WhatsApp: {social_accounts['whatsapp_phone']}")
                elif platform == "linkedin" and social_accounts.get('linkedin_profile_url'):
                    logger.info(f"   🔗 LinkedIn: {social_accounts['linkedin_profile_url']}")
                elif platform == "twitter" and social_accounts.get('twitter_profile_url'):
                    logger.info(f"   🐦 Twitter: {social_accounts['twitter_profile_url']}")
            
            try:
                # Initialize scraper
                consent_token = consent_tokens[agent_id]
                scraper = SocialMediaScraper(person_name, consent_token)
                
                # Configure scraper with settings
                await scraper.initialize_driver()
                scraper.max_messages_per_platform = scraping_config["max_messages_per_platform"]
                scraper.scraping_delay = self.config["scraping_settings"].get("delay_between_platforms", 2)
                
                # Scrape platforms
                logger.info(f"🚀 Starting scraping for {person_name}...")
                scrape_results = await scraper.scrape_all_platforms(scraping_config["platforms"])
                
                # Save consolidated data
                scraped_file = await scraper.save_all_data()
                scraped_files[agent_id] = scraped_file
                
                total_messages = sum(len(messages) for messages in scrape_results.values())
                
                # Update status
                self.pipeline_status["agents_status"][agent_id].update({
                    "data_scraped": True,
                    "scraped_file": scraped_file,
                    "scrape_results": {
                        platform: len(messages) 
                        for platform, messages in scrape_results.items()
                    },
                    "total_messages": total_messages,
                    "scrape_completed_at": datetime.now().isoformat()
                })
                
                # Cleanup
                await scraper.close()
                
                logger.info(f"✅ Scraped {total_messages} messages for {person_name}")
                logger.info(f"   Data saved to: {scraped_file}")
                
                # Delay between agents
                if len(agents_by_priority) > 1:
                    delay = self.config["scraping_settings"].get("delay_between_platforms", 5)
                    logger.info(f"⏳ Waiting {delay}s before next agent...")
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"❌ Scraping failed for {person_name}: {e}")
                self.pipeline_status["agents_status"][agent_id].update({
                    "data_scraped": False,
                    "scrape_error": str(e),
                    "scrape_failed_at": datetime.now().isoformat()
                })
                
                # Continue with next agent
                continue
        
        return scraped_files
    
    async def phase_3_train_models(self, scraped_files: Dict[str, str]) -> Dict[str, Dict]:
        """Phase 3: Train models using scraped data"""
        
        logger.info("🧠 Phase 3: Training agent models...")
        self.pipeline_status["current_phase"] = "model_training"
        
        training_results = {}
        
        # Train in priority order
        agents_by_priority = sorted(
            self.config["agents"].items(),
            key=lambda x: x[1]["scraping_config"]["scrape_priority"]
        )
        
        for agent_id, agent_config in agents_by_priority:
            person_name = agent_config["person_name"]
            training_config = agent_config["training_config"]
            
            if not self.pipeline_status["agents_status"][agent_id].get("data_scraped"):
                logger.warning(f"⚠️  Skipping {person_name} - no scraped data")
                continue
            
            total_messages = self.pipeline_status["agents_status"][agent_id].get("total_messages", 0)
            if total_messages < 50:
                logger.warning(f"⚠️  Skipping {person_name} - insufficient data ({total_messages} messages)")
                continue
            
            logger.info(f"\n🔄 Training model for {person_name}...")
            logger.info(f"   Training data: {total_messages} messages")
            logger.info(f"   Epochs: {training_config['training_epochs']}")
            logger.info(f"   Learning rate: {training_config['learning_rate']}")
            logger.info(f"   Batch size: {training_config['batch_size']}")
            
            try:
                # Configure fine-tuner from config
                pipeline_config = self.config["training_pipeline"]
                self.fine_tuner.base_model_name = pipeline_config["base_model"]
                
                # Override LoRA config if specified
                if pipeline_config.get("use_lora", True):
                    from peft import LoraConfig, TaskType
                    self.fine_tuner.lora_config = LoraConfig(
                        task_type=TaskType.CAUSAL_LM,
                        inference_mode=False,
                        r=pipeline_config.get("lora_rank", 8),
                        lora_alpha=pipeline_config.get("lora_alpha", 32),
                        lora_dropout=0.1,
                        target_modules=["q_proj", "v_proj"]
                    )
                
                # Run fine-tuning
                training_start_time = time.time()
                
                result = await self.fine_tuner.fine_tune_agent(
                    person_name=person_name,
                    agent_id=agent_id,
                    resume_from_checkpoint=False
                )
                
                training_end_time = time.time()
                training_duration = training_end_time - training_start_time
                
                training_results[agent_id] = result
                
                if result.get("status") == "completed":
                    # Update status
                    self.pipeline_status["agents_status"][agent_id].update({
                        "model_trained": True,
                        "model_path": result["model_path"],
                        "training_duration": training_duration,
                        "train_samples": result.get("train_samples", 0),
                        "eval_samples": result.get("eval_samples", 0),
                        "training_completed_at": datetime.now().isoformat()
                    })
                    
                    logger.info(f"✅ Model training complete for {person_name}")
                    logger.info(f"   Training time: {training_duration:.1f}s")
                    logger.info(f"   Training samples: {result.get('train_samples', 'N/A')}")
                    logger.info(f"   Model saved to: {result['model_path']}")
                else:
                    logger.error(f"❌ Training failed for {person_name}: {result.get('error')}")
                    self.pipeline_status["agents_status"][agent_id].update({
                        "model_trained": False,
                        "training_error": result.get("error"),
                        "training_failed_at": datetime.now().isoformat()
                    })
                
            except Exception as e:
                logger.error(f"❌ Training failed for {person_name}: {e}")
                self.pipeline_status["agents_status"][agent_id].update({
                    "model_trained": False,
                    "training_error": str(e),
                    "training_failed_at": datetime.now().isoformat()
                })
        
        return training_results
    
    async def phase_4_deploy_agents(self, training_results: Dict[str, Dict]) -> Dict[str, Any]:
        """Phase 4: Deploy trained agents to the system"""
        
        logger.info("🚀 Phase 4: Deploying trained agents...")
        self.pipeline_status["current_phase"] = "deployment"
        
        try:
            # Initialize core systems
            logger.info("🔄 Initializing shared knowledge system...")
            await shared_knowledge.initialize()
            
            logger.info("🔄 Initializing communication protocol...")
            communication_protocol.shared_knowledge = shared_knowledge  
            await communication_protocol.initialize()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize core systems: {e}")
            return {}
        
        deployed_agents = {}
        
        # Deploy manager agent first
        logger.info("🔄 Deploying manager agent...")
        try:
            manager = ManagerAgent(
                shared_knowledge=shared_knowledge,
                worker_agent_ids=[aid for aid in self.config["agents"].keys()]
            )
            await manager.initialize()
            
            await communication_protocol.register_agent("manager", manager.receive_message)
            deployed_agents["manager"] = {
                "type": "manager", 
                "status": "deployed",
                "deployed_at": datetime.now().isoformat()
            }
            
            logger.info("✅ Manager agent deployed")
            
        except Exception as e:
            logger.error(f"❌ Manager agent deployment failed: {e}")
            return {}
        
        # Deploy worker agents
        for agent_id, agent_config in self.config["agents"].items():
            person_name = agent_config["person_name"]
            
            if not self.pipeline_status["agents_status"][agent_id].get("model_trained"):
                logger.warning(f"⚠️  Skipping deployment for {person_name} - model not trained")
                continue
            
            logger.info(f"🔄 Deploying agent for {person_name}...")
            
            try:
                # Get model path and create capabilities
                model_path = self.pipeline_status["agents_status"][agent_id]["model_path"]
                agent_role = agent_config["agent_role"]
                
                # Create capabilities from config
                capabilities = AgentCapabilities(
                    technical_skills={
                        skill: 0.8 for skill in agent_role["primary_skills"]
                    },
                    preferred_task_types=agent_role["task_preferences"],
                    work_style={
                        "collaborative": "collaborative" in agent_role["communication_style"],
                        "technical": "technical" in agent_role["communication_style"],
                        "creative": "creative" in agent_role["communication_style"]
                    },
                    communication_style={
                        "style": agent_role["communication_style"]
                    }
                )
                
                # Create worker agent
                worker = WorkerAgent(
                    agent_id=agent_id,
                    person_name=person_name,
                    shared_knowledge=shared_knowledge,
                    capabilities=capabilities,
                    model_path=model_path
                )
                
                await worker.initialize()
                await communication_protocol.register_agent(agent_id, worker.receive_message)
                
                deployed_agents[agent_id] = {
                    "type": "worker",
                    "person_name": person_name,
                    "model_path": model_path,
                    "status": "deployed",
                    "capabilities": agent_role["primary_skills"],
                    "deployed_at": datetime.now().isoformat()
                }
                
                # Update pipeline status
                self.pipeline_status["deployed_agents"][agent_id] = deployed_agents[agent_id]
                
                logger.info(f"✅ Agent deployed for {person_name}")
                logger.info(f"   Skills: {', '.join(agent_role['primary_skills'])}")
                
            except Exception as e:
                logger.error(f"❌ Deployment failed for {person_name}: {e}")
                deployed_agents[agent_id] = {
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                }
        
        self.pipeline_status["deployment_completed_at"] = datetime.now().isoformat()
        return deployed_agents
    
    def save_pipeline_status(self):
        """Save pipeline status to file"""
        status_file = Path("data/pipeline_status.json")
        
        # Add summary stats
        self.pipeline_status["summary"] = {
            "total_agents": len(self.config["agents"]),
            "consent_setup": len([s for s in self.pipeline_status["agents_status"].values() if s.get("consent_setup")]),
            "data_scraped": len([s for s in self.pipeline_status["agents_status"].values() if s.get("data_scraped")]),
            "models_trained": len([s for s in self.pipeline_status["agents_status"].values() if s.get("model_trained")]),
            "agents_deployed": len(self.pipeline_status["deployed_agents"])
        }
        
        with open(status_file, 'w') as f:
            json.dump(self.pipeline_status, f, indent=2, default=str)
        
        logger.info(f"💾 Pipeline status saved to {status_file}")
    
    async def run_complete_pipeline(self):
        """Run the complete end-to-end pipeline"""
        
        logger.info("🚀 Starting Complete Agent Training & Deployment Pipeline")
        logger.info("=" * 60)
        
        try:
            # Prerequisites check
            if not self.check_prerequisites():
                logger.error("❌ Prerequisites check failed. Please install required packages.")
                return
            
            # Phase 1: Setup consents
            logger.info("\n" + "="*60)
            consent_tokens = await self.phase_1_setup_consents()
            self.save_pipeline_status()
            
            # Phase 2: Scrape data (requires manual intervention for logins)
            logger.info("\n" + "="*60)
            logger.info("⚠️  MANUAL INTERVENTION REQUIRED")
            logger.info("You will need to manually login to the following accounts:")
            
            for agent_id, agent_config in self.config["agents"].items():
                person_name = agent_config["person_name"]
                social = agent_config["social_accounts"]
                platforms = agent_config["scraping_config"]["platforms"]
                
                logger.info(f"\n👤 {person_name}:")
                if "whatsapp" in platforms:
                    logger.info(f"   📱 WhatsApp Web - Phone: {social.get('whatsapp_phone', 'Not provided')}")
                if "linkedin" in platforms:
                    logger.info(f"   💼 LinkedIn - {social.get('linkedin_profile_url', 'Not provided')}")
                if "twitter" in platforms:
                    logger.info(f"   🐦 Twitter/X - {social.get('twitter_profile_url', 'Not provided')}")
            
            logger.info("\n📝 Make sure you have:")
            logger.info("   • Access to the social media accounts listed above")
            logger.info("   • Permission from each person to scrape their data")
            logger.info("   • Chrome browser installed for automated scraping")
            
            input("\n⏳ Press Enter when ready to start scraping...")
            
            scraped_files = await self.phase_2_scrape_data(consent_tokens)
            self.save_pipeline_status()
            
            # Phase 3: Train models
            logger.info("\n" + "="*60)
            training_results = await self.phase_3_train_models(scraped_files)
            self.save_pipeline_status()
            
            # Phase 4: Deploy agents
            logger.info("\n" + "="*60)
            if self.config["training_pipeline"]["auto_deploy_after_training"]:
                deployed_agents = await self.phase_4_deploy_agents(training_results)
                self.save_pipeline_status()
            else:
                logger.info("⚠️  Auto-deployment disabled in config")
                deployed_agents = {}
            
            # Final summary
            self.print_final_summary(deployed_agents)
            
        except KeyboardInterrupt:
            logger.info("⏹️  Pipeline stopped by user")
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.save_pipeline_status()
    
    def print_final_summary(self, deployed_agents: Dict[str, Any]):
        """Print final pipeline summary"""
        
        logger.info("\n" + "=" * 60)
        logger.info("🎯 PIPELINE COMPLETE - FINAL SUMMARY")
        logger.info("=" * 60)
        
        summary = self.pipeline_status["summary"]
        
        logger.info(f"📊 Pipeline Statistics:")
        logger.info(f"   Total agents configured: {summary['total_agents']}")
        logger.info(f"   Consent records created: {summary['consent_setup']}")
        logger.info(f"   Data successfully scraped: {summary['data_scraped']}")
        logger.info(f"   Models successfully trained: {summary['models_trained']}")
        logger.info(f"   Agents successfully deployed: {summary['agents_deployed']}")
        
        logger.info(f"\n👥 Individual Agent Status:")
        for agent_id, status in self.pipeline_status["agents_status"].items():
            person_name = status["person_name"]
            
            if status.get("model_trained") and agent_id in self.pipeline_status["deployed_agents"]:
                emoji = "✅"
                state = "READY TO USE"
                messages = status.get("total_messages", 0)
                model_path = status.get("model_path", "N/A")
                logger.info(f"   {emoji} {person_name} - {state}")
                logger.info(f"      📊 Training data: {messages} messages")
                logger.info(f"      🧠 Model: {Path(model_path).name if model_path != 'N/A' else 'N/A'}")
            elif status.get("model_trained"):
                emoji = "🧠"
                state = "TRAINED (not deployed)"
                logger.info(f"   {emoji} {person_name} - {state}")
            elif status.get("data_scraped"):
                emoji = "📱"
                state = "DATA SCRAPED (training failed)"
                logger.info(f"   {emoji} {person_name} - {state}")
            else:
                emoji = "❌"
                state = "FAILED"
                error = status.get("scrape_error") or status.get("training_error", "Unknown error")
                logger.info(f"   {emoji} {person_name} - {state}")
                logger.info(f"      Error: {error[:100]}...")
        
        # Success celebration or next steps
        if summary["agents_deployed"] > 0:
            logger.info(f"\n🎉 SUCCESS! {summary['agents_deployed']} digital twin agents are live!")
            logger.info("🚀 Your agents are ready to use:")
            logger.info("   • Start the API server: python main.py")
            logger.info("   • Test the system: python start.py")
            logger.info("   • Connect your frontend to: http://localhost:8000")
            logger.info("   • View status: cat data/pipeline_status.json")
        else:
            logger.info("\n⚠️  No agents were successfully deployed")
            logger.info("💡 Next steps:")
            logger.info("   • Check data/pipeline_status.json for detailed errors")
            logger.info("   • Verify social media login credentials")
            logger.info("   • Ensure sufficient training data was collected")
            logger.info("   • Re-run specific phases: python deploy_agents.py <phase>")


# CLI Interface
async def run_pipeline():
    """Run complete pipeline"""
    pipeline = CompleteAgentPipeline()
    await pipeline.run_complete_pipeline()

async def deploy_only():
    """Deploy already trained models"""
    pipeline = CompleteAgentPipeline()
    
    # Load existing status
    status_file = Path("data/pipeline_status.json")
    if not status_file.exists():
        logger.error("❌ No pipeline status found. Run complete pipeline first.")
        return
    
    with open(status_file, 'r') as f:
        pipeline.pipeline_status = json.load(f)
    
    # Mock training results for deployment
    training_results = {}
    for agent_id, status in pipeline.pipeline_status["agents_status"].items():
        if status.get("model_trained"):
            training_results[agent_id] = {"status": "completed"}
    
    if not training_results:
        logger.error("❌ No trained models found for deployment")
        return
    
    deployed = await pipeline.phase_4_deploy_agents(training_results)
    pipeline.print_final_summary(deployed)

async def check_status():
    """Check current pipeline status"""
    status_file = Path("data/pipeline_status.json")
    if not status_file.exists():
        logger.info("📝 No pipeline status found. Pipeline not yet run.")
        return
    
    with open(status_file, 'r') as f:
        status = json.load(f)
    
    logger.info("📊 Current Pipeline Status:")
    logger.info("=" * 40)
    
    if "summary" in status:
        summary = status["summary"]
        logger.info(f"Total agents: {summary['total_agents']}")
        logger.info(f"Consents setup: {summary['consent_setup']}")
        logger.info(f"Data scraped: {summary['data_scraped']}")
        logger.info(f"Models trained: {summary['models_trained']}")
        logger.info(f"Agents deployed: {summary['agents_deployed']}")
    
    logger.info(f"\nCurrent phase: {status.get('current_phase', 'Unknown')}")
    logger.info(f"Started at: {status.get('started_at', 'Unknown')}")
    
    logger.info("\n👥 Agent Details:")
    for agent_id, agent_status in status.get("agents_status", {}).items():
        person_name = agent_status.get("person_name", agent_id)
        consent = "✅" if agent_status.get("consent_setup") else "❌"
        scraped = "✅" if agent_status.get("data_scraped") else "❌"
        trained = "✅" if agent_status.get("model_trained") else "❌"
        deployed = "✅" if agent_id in status.get("deployed_agents", {}) else "❌"
        
        logger.info(f"  {person_name}: Consent{consent} Scraped{scraped} Trained{trained} Deployed{deployed}")


def main():
    """Main CLI interface"""
    
    commands = {
        "run": ("Run complete pipeline", run_pipeline),
        "deploy": ("Deploy already trained models", deploy_only),
        "status": ("Check pipeline status", check_status)
    }
    
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        _, func = commands[sys.argv[1]]
        asyncio.run(func())
    else:
        print("🎯 Complete Agent Training & Deployment Pipeline")
        print("=" * 50)
        print("Usage:")
        for cmd, (desc, _) in commands.items():
            print(f"  python deploy_agents.py {cmd:<8} # {desc}")
        print("\nMake sure agent_training_config.json is configured first!")
        print("See the example config in the repository for reference.")


if __name__ == "__main__":
    main()
