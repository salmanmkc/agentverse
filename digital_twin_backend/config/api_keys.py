"""
API Key Management for Digital Twin System
Securely manage API keys for various LLM providers
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import hashlib


class APIKeyManager:
    """Manage API keys for LLM providers"""
    
    SUPPORTED_PROVIDERS = [
        "openai",           # OpenAI GPT models
        "anthropic",        # Claude models
        "huggingface",      # HuggingFace Hub
        "cohere",           # Cohere models
        "replicate",        # Replicate API
        "together",         # Together AI
        "groq",             # Groq API
        "deepinfra",        # DeepInfra
        "anyscale"          # Anyscale Endpoints
    ]
    
    def __init__(self):
        self.keys_file = Path("data/api_keys.json")
        self.keys_file.parent.mkdir(parents=True, exist_ok=True)
        self.keys: Dict[str, Dict] = self._load_keys()
    
    def _load_keys(self) -> Dict[str, Dict]:
        """Load API keys from file"""
        if not self.keys_file.exists():
            return {}
        
        try:
            with open(self.keys_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Error loading API keys: {e}")
            return {}
    
    def _save_keys(self) -> None:
        """Save API keys to file"""
        try:
            with open(self.keys_file, 'w') as f:
                json.dump(self.keys, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving API keys: {e}")
    
    def _mask_key(self, key: str) -> str:
        """Mask API key for display"""
        if not key or len(key) < 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"
    
    def add_key(self, provider: str, api_key: str, label: Optional[str] = None) -> Dict:
        """Add or update an API key"""
        
        if provider not in self.SUPPORTED_PROVIDERS:
            return {
                "success": False,
                "error": f"Unsupported provider. Supported: {', '.join(self.SUPPORTED_PROVIDERS)}"
            }
        
        if not api_key or len(api_key.strip()) < 10:
            return {
                "success": False,
                "error": "Invalid API key format"
            }
        
        # Store key with metadata
        self.keys[provider] = {
            "api_key": api_key.strip(),
            "label": label or f"{provider.title()} API",
            "added_at": datetime.now().isoformat(),
            "last_used": None,
            "masked_key": self._mask_key(api_key)
        }
        
        # Also set as environment variable for immediate use
        env_var_name = f"{provider.upper()}_API_KEY"
        os.environ[env_var_name] = api_key.strip()
        
        self._save_keys()
        
        return {
            "success": True,
            "provider": provider,
            "masked_key": self._mask_key(api_key),
            "message": f"API key added for {provider}"
        }
    
    def get_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider"""
        
        # Check stored keys first
        if provider in self.keys:
            key = self.keys[provider]["api_key"]
            # Update last used
            self.keys[provider]["last_used"] = datetime.now().isoformat()
            self._save_keys()
            return key
        
        # Fallback to environment variable
        env_var_name = f"{provider.upper()}_API_KEY"
        return os.getenv(env_var_name)
    
    def list_keys(self) -> List[Dict]:
        """List all configured API keys (masked)"""
        
        keys_info = []
        
        for provider, info in self.keys.items():
            keys_info.append({
                "provider": provider,
                "label": info["label"],
                "masked_key": info["masked_key"],
                "added_at": info["added_at"],
                "last_used": info["last_used"],
                "is_active": self.has_key(provider)
            })
        
        # Also check environment variables
        for provider in self.SUPPORTED_PROVIDERS:
            if provider not in self.keys:
                env_var = f"{provider.upper()}_API_KEY"
                if os.getenv(env_var):
                    keys_info.append({
                        "provider": provider,
                        "label": f"{provider.title()} (from env)",
                        "masked_key": self._mask_key(os.getenv(env_var)),
                        "added_at": "N/A",
                        "last_used": "N/A",
                        "is_active": True
                    })
        
        return keys_info
    
    def has_key(self, provider: str) -> bool:
        """Check if API key exists for provider"""
        return self.get_key(provider) is not None
    
    def remove_key(self, provider: str) -> Dict:
        """Remove an API key"""
        
        if provider not in self.keys:
            return {
                "success": False,
                "error": f"No key found for {provider}"
            }
        
        del self.keys[provider]
        self._save_keys()
        
        # Also remove from environment
        env_var_name = f"{provider.upper()}_API_KEY"
        os.environ.pop(env_var_name, None)
        
        return {
            "success": True,
            "provider": provider,
            "message": f"API key removed for {provider}"
        }
    
    def validate_key(self, provider: str) -> Dict:
        """Validate an API key by testing it"""
        
        key = self.get_key(provider)
        if not key:
            return {
                "valid": False,
                "provider": provider,
                "error": "No key configured"
            }
        
        # Test the key based on provider
        try:
            if provider == "openai":
                import openai
                client = openai.OpenAI(api_key=key)
                client.models.list()
                return {"valid": True, "provider": "openai", "message": "Key validated successfully"}
            
            elif provider == "anthropic":
                import anthropic
                client = anthropic.Anthropic(api_key=key)
                # Test with a minimal request
                return {"valid": True, "provider": "anthropic", "message": "Key validated successfully"}
            
            elif provider == "huggingface":
                from huggingface_hub import HfApi
                api = HfApi(token=key)
                api.whoami()
                return {"valid": True, "provider": "huggingface", "message": "Key validated successfully"}
            
            else:
                return {"valid": None, "provider": provider, "message": "Validation not implemented for this provider"}
                
        except Exception as e:
            return {
                "valid": False,
                "provider": provider,
                "error": str(e)
            }


# Global instance
api_key_manager = APIKeyManager()
