"""
Configuration settings for the Digital Twin Backend System
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Digital Twin Workplace"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API Settings
    API_HOST: str = Field(default="localhost", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./digital_twins.db", env="DATABASE_URL")
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Model Settings
    BASE_MODEL_NAME: str = Field(default="microsoft/DialoGPT-medium", env="BASE_MODEL_NAME")
    MODELS_DIR: str = Field(default="./models", env="MODELS_DIR")
    MAX_CONTEXT_LENGTH: int = Field(default=1024, env="MAX_CONTEXT_LENGTH")
    
    # Agent Settings
    MANAGER_AGENT_ID: str = "manager"
    WORKER_AGENT_IDS: List[str] = ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]
    MAX_NEGOTIATION_ROUNDS: int = 3
    TASK_TIMEOUT_MINUTES: int = 30
    
    # Scraping Settings
    SCRAPING_ENABLED: bool = Field(default=False, env="SCRAPING_ENABLED")
    SELENIUM_HEADLESS: bool = Field(default=True, env="SELENIUM_HEADLESS")
    SELENIUM_TIMEOUT: int = 30
    
    # Frontend Integration
    FRONTEND_API_URL: str = Field(default="http://localhost:3000", env="FRONTEND_API_URL")
    WEBHOOK_SECRET: str = Field(default="your-webhook-secret", env="WEBHOOK_SECRET")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="digital_twins.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


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
    "agent_3": AgentConfig("agent_3", "Agent_3", {"creative": 0.8, "frontend": 0.7}),
    "agent_4": AgentConfig("agent_4", "Agent_4", {"backend": 0.9, "database": 0.8}),
    "agent_5": AgentConfig("agent_5", "Agent_5", {"qa": 0.85, "testing": 0.9}),
}
