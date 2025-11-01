"""
Configuration settings for the Digital Twin Backend System
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import os


class Settings:
    """Application settings"""
    
    def __init__(self):
        # Application
        self.APP_NAME = "Digital Twin Workplace"
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        
        # API Settings
        self.API_HOST = os.getenv("API_HOST", "localhost")
        self.API_PORT = int(os.getenv("API_PORT", "8000"))
        
        # Database
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./digital_twins.db")
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Model Settings
        self.BASE_MODEL_NAME = os.getenv("BASE_MODEL_NAME", "microsoft/DialoGPT-medium")
        self.MODELS_DIR = os.getenv("MODELS_DIR", "./models")
        self.MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "1024"))
        
        # Agent Settings
        self.MANAGER_AGENT_ID = "manager"
        self.WORKER_AGENT_IDS = ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]
        self.MAX_NEGOTIATION_ROUNDS = 3
        self.TASK_TIMEOUT_MINUTES = 30
        
        # Scraping Settings
        self.SCRAPING_ENABLED = os.getenv("SCRAPING_ENABLED", "False").lower() == "true"
        self.SELENIUM_HEADLESS = os.getenv("SELENIUM_HEADLESS", "True").lower() == "true"
        self.SELENIUM_TIMEOUT = 30
        
        # Frontend Integration
        self.FRONTEND_API_URL = os.getenv("FRONTEND_API_URL", "http://localhost:3000")
        self.WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret")
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.getenv("LOG_FILE", "digital_twins.log")


class AgentConfig:
    """Configuration for individual agents"""
    
    def __init__(self, agent_id: str, person_name: str, capabilities: Dict[str, float]):
        self.agent_id = agent_id
        self.person_name = person_name
        self.capabilities = capabilities  # e.g., {"technical": 0.9, "creative": 0.6}
        self.model_path = f"{settings.MODELS_DIR}/{agent_id}_model"
        self.fine_tuned = False
        
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "person_name": self.person_name,
            "capabilities": self.capabilities,
            "model_path": self.model_path,
            "fine_tuned": self.fine_tuned
        }


@dataclass
class PersonTrainingConfig:
    """Complete training configuration for a real person"""
    person_name: str
    email: str
    agent_id: str
    
    # Social media account information
    whatsapp_phone: Optional[str] = None
    linkedin_profile: Optional[str] = None
    twitter_username: Optional[str] = None
    
    # Training preferences
    platforms_to_scrape: List[str] = field(default_factory=lambda: ["whatsapp", "linkedin"])
    max_messages_per_platform: int = 1000
    training_priority: int = 1  # 1=high, 5=low
    
    # Consent & status
    has_consent: bool = False
    consent_token: Optional[str] = None
    consent_expires: Optional[datetime] = None
    
    # Training status
    data_scraped: bool = False
    model_trained: bool = False
    last_training_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "person_name": self.person_name,
            "email": self.email,
            "agent_id": self.agent_id,
            "whatsapp_phone": self.whatsapp_phone,
            "linkedin_profile": self.linkedin_profile,
            "twitter_username": self.twitter_username,
            "platforms_to_scrape": self.platforms_to_scrape,
            "max_messages_per_platform": self.max_messages_per_platform,
            "training_priority": self.training_priority,
            "has_consent": self.has_consent,
            "consent_token": self.consent_token,
            "consent_expires": self.consent_expires.isoformat() if self.consent_expires else None,
            "data_scraped": self.data_scraped,
            "model_trained": self.model_trained,
            "last_training_date": self.last_training_date.isoformat() if self.last_training_date else None
        }


# Global settings instance
settings = Settings()

# Example agent configurations (customize based on real people)
AGENT_CONFIGS = {
    "manager": AgentConfig("manager", "Manager", {"leadership": 0.9, "coordination": 0.95}),
    "agent_1": AgentConfig("agent_1", "Eddie Lake", {"technical": 0.8, "documentation": 0.9}),
    "agent_2": AgentConfig("agent_2", "Jamik Tashpulatov", {"technical": 0.95, "architecture": 0.9}),
    "agent_3": AgentConfig("agent_3", "Sarah Johnson", {"creative": 0.8, "frontend": 0.7}),
    "agent_4": AgentConfig("agent_4", "Mike Chen", {"backend": 0.9, "database": 0.8}),
    "agent_5": AgentConfig("agent_5", "Lisa Wong", {"qa": 0.85, "testing": 0.9}),
}

# Enhanced training configurations with social media accounts
# This integrates with the agent_training_config.json file
PERSON_TRAINING_CONFIGS = {
    "agent_1": PersonTrainingConfig(
        person_name="Eddie Lake",
        email="eddie.lake@company.com",
        agent_id="agent_1",
        whatsapp_phone="+44-7700-900123",
        linkedin_profile="eddie-lake-dev",
        twitter_username="@eddieLakeDev",
        platforms_to_scrape=["whatsapp", "linkedin"],
        training_priority=1
    ),
    "agent_2": PersonTrainingConfig(
        person_name="Jamik Tashpulatov",
        email="jamik.t@company.com",
        agent_id="agent_2",
        whatsapp_phone="+44-7700-900456",
        linkedin_profile="jamik-tashpulatov",
        twitter_username="@jamikT_dev",
        platforms_to_scrape=["whatsapp", "linkedin", "twitter"],
        training_priority=1
    ),
    "agent_3": PersonTrainingConfig(
        person_name="Sarah Johnson",
        email="sarah.j@company.com",
        agent_id="agent_3",
        linkedin_profile="sarah-johnson-design",
        twitter_username="@sarahDesigns",
        platforms_to_scrape=["linkedin", "twitter"],
        training_priority=2
    ),
    "agent_4": PersonTrainingConfig(
        person_name="Mike Chen",
        email="mike.c@company.com",
        agent_id="agent_4",
        whatsapp_phone="+44-7700-900321",
        linkedin_profile="mike-chen-backend",
        platforms_to_scrape=["whatsapp", "linkedin"],
        training_priority=2
    ),
    "agent_5": PersonTrainingConfig(
        person_name="Lisa Wong",
        email="lisa.w@company.com",
        agent_id="agent_5",
        whatsapp_phone="+44-7700-900654",
        linkedin_profile="lisa-wong-qa",
        platforms_to_scrape=["whatsapp", "linkedin"],
        training_priority=3
    )
}
