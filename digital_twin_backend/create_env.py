#!/usr/bin/env python3
"""
Create .env file with default settings
"""
from pathlib import Path

def create_env_file():
    """Create .env file with default settings"""
    
    env_content = """# Digital Twin Backend Environment Configuration
# Copy this file to .env and update values as needed

# Application Settings
DEBUG=true
APP_NAME="Digital Twin Workplace"

# API Configuration
API_HOST=localhost
API_PORT=8000

# Database Configuration
DATABASE_URL=sqlite:///./digital_twins.db
REDIS_URL=redis://localhost:6379

# Model Configuration
BASE_MODEL_NAME=microsoft/DialoGPT-medium
MODELS_DIR=./models
MAX_CONTEXT_LENGTH=1024

# Scraping Configuration  
SCRAPING_ENABLED=true
SELENIUM_HEADLESS=false
SELENIUM_TIMEOUT=30

# Frontend Integration
FRONTEND_API_URL=http://localhost:3000
WEBHOOK_SECRET=your-webhook-secret

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=digital_twins.log

# Optional: Hugging Face Hub Configuration (for downloading models)
# HF_TOKEN=your_huggingface_token

# Optional: OpenAI API Key (if using OpenAI models as fallback)
# OPENAI_API_KEY=your_openai_key
"""
    
    env_file = Path(".env")
    
    if env_file.exists():
        print(f"⚠️  .env file already exists")
        choice = input("Overwrite? (y/n): ").strip().lower()
        if choice != 'y':
            print("❌ Cancelled")
            return False
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created .env file with default settings")
    print("💡 Edit the file to customize your configuration")
    
    return True

if __name__ == "__main__":
    create_env_file()
