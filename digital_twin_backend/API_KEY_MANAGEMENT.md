# 🔑 API Key Management - Complete Guide

## 🎯 **NEW: API Key Support Added!**

You can now use **cloud-based LLM APIs** for your agents instead of (or alongside) locally fine-tuned models!

## 🌐 **Supported Providers**

- **OpenAI** - GPT-4, GPT-3.5-turbo
- **Anthropic** - Claude 3 (Opus, Sonnet, Haiku)
- **HuggingFace** - Any HuggingFace Hub model
- **Cohere** - Command models
- **Groq** - Ultra-fast Llama/Mixtral inference
- **Together AI** - Open-source models
- **Replicate** - Various models
- **DeepInfra** - Inference API
- **Anyscale** - Endpoints

## 🔧 **How to Use API Keys**

### **1. Add an API Key**

```python
# MCP Tool Call
add_api_key(
  provider="openai",
  api_key="sk-proj-abc123...",
  label="OpenAI Production Key"
)

# Returns:
{
  "success": true,
  "provider": "openai",
  "masked_key": "sk-p...123",
  "message": "API key added for openai"
}
```

### **2. List Your API Keys**

```python
# MCP Tool Call
list_api_keys()

# Returns:
{
  "api_keys": [
    {
      "provider": "openai",
      "label": "OpenAI Production Key",
      "masked_key": "sk-p...123",
      "added_at": "2024-11-01T18:30:00",
      "last_used": "2024-11-01T19:15:00",
      "is_active": true
    },
    {
      "provider": "anthropic",
      "label": "Claude API",
      "masked_key": "sk-a...xyz",
      "added_at": "2024-11-01T18:35:00",
      "last_used": null,
      "is_active": true
    }
  ],
  "total": 2,
  "supported_providers": ["openai", "anthropic", "huggingface", ...]
}
```

### **3. Validate an API Key**

```python
# MCP Tool Call
validate_api_key("openai")

# Returns:
{
  "valid": true,
  "provider": "openai",
  "message": "Key validated successfully"
}
```

### **4. Check API Key Status**

```python
# MCP Tool Call
get_api_key_status("openai")

# Returns:
{
  "provider": "openai",
  "has_key": true,
  "key_info": {
    "provider": "openai",
    "masked_key": "sk-p...123",
    "added_at": "2024-11-01T18:30:00",
    "is_active": true
  }
}
```

### **5. Remove an API Key**

```python
# MCP Tool Call
remove_api_key("openai")

# Returns:
{
  "success": true,
  "provider": "openai",
  "message": "API key removed for openai"
}
```

## 🤖 **Configure Agents to Use APIs**

### **Option 1: Use GPT-4 for an Agent**

```python
# 1. Add OpenAI API key
add_api_key("openai", "sk-proj-your-key-here")

# 2. Configure agent to use GPT-4
configure_agent_with_api(
  agent_id="agent_1",
  provider="openai",
  model_name="gpt-4",
  person_name="Eddie Lake"
)

# Returns:
{
  "message": "Agent agent_1 configured to use openai API",
  "agent_id": "agent_1",
  "person_name": "Eddie Lake",
  "updates": {
    "api_provider": "openai",
    "api_model": "gpt-4",
    "model_type": "api"
  }
}

# Now agent_1 uses GPT-4 for responses!
```

### **Option 2: Use Claude for an Agent**

```python
# 1. Add Anthropic API key
add_api_key("anthropic", "sk-ant-your-key-here")

# 2. Configure agent
configure_agent_with_api(
  agent_id="agent_2",
  provider="anthropic",
  model_name="claude-3-sonnet",
  person_name="Jamik Tashpulatov"
)

# Now agent_2 uses Claude!
```

### **Option 3: Mix Local and API Models**

```python
# Eddie uses fine-tuned local model
update_agent_model("agent_1", "models/Eddie_Lake_model")

# Jamik uses GPT-4 API
configure_agent_with_api("agent_2", "openai", "gpt-4")

# Sarah uses Claude API  
configure_agent_with_api("agent_3", "anthropic", "claude-3-haiku")

# Different agents, different models!
```

## 🎯 **Use Cases**

### **Use Case 1: Rapid Prototyping**
```python
# Don't want to train models yet? Use GPT-4
for agent_id in ["agent_1", "agent_2", "agent_3"]:
    configure_agent_with_api(agent_id, "openai", "gpt-4")

# Instant working agents with GPT-4 intelligence
```

### **Use Case 2: Compare Model Quality**
```python
# Test local model
update_agent_model("agent_1", "models/Eddie_Lake_model")
create_task("Test task")  # See response

# Test GPT-4
configure_agent_with_api("agent_1", "openai", "gpt-4")
create_task("Test task")  # Compare response

# Pick the better one!
```

### **Use Case 3: Hybrid Team**
```python
# Critical agents: Fine-tuned personality models
update_agent_model("agent_1", "models/Eddie_Lake_model")
update_agent_model("agent_2", "models/Jamik_model")

# Less critical agents: GPT-4 for quick setup
configure_agent_with_api("agent_3", "openai", "gpt-4")
configure_agent_with_api("agent_4", "openai", "gpt-4")
configure_agent_with_api("agent_5", "openai", "gpt-4")
```

## 📊 **Model Types Comparison**

| Feature | Local Fine-tuned | API (GPT-4/Claude) |
|---------|------------------|---------------------|
| **Setup Time** | Hours (training) | Minutes (add key) |
| **Personality** | ✅ Trained on real messages | ❌ Generic prompting |
| **Cost** | Free (after training) | $$$ Per request |
| **Privacy** | ✅ Fully local | ⚠️ Sent to API |
| **Quality** | Good for persona | Excellent general |
| **Speed** | Fast (local) | Medium (API) |
| **Offline** | ✅ Works offline | ❌ Needs internet |

## 🔐 **Security Notes**

✅ **API keys are masked** when displayed
✅ **Keys stored locally** in `data/api_keys.json`
✅ **Keys loaded as env vars** for immediate use
✅ **Validation before use** - test keys before deploying

⚠️ **Never commit** `data/api_keys.json` to git
⚠️ **Use environment variables** for production

## 📝 **Quick Start Examples**

### **Example 1: Use OpenAI for All Agents**

```bash
# Via MCP or Python
add_api_key("openai", "sk-proj-your-key")

# Configure all agents
for agent_id in ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]:
    configure_agent_with_api(agent_id, "openai", "gpt-4")

# Done! All agents use GPT-4
```

### **Example 2: Environment Variables**

```bash
# Add to .env file
OPENAI_API_KEY=sk-proj-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
HUGGINGFACE_API_KEY=hf_your-key-here

# System automatically detects them
list_api_keys()
# Shows: OpenAI (from env), Anthropic (from env), etc.
```

### **Example 3: Check Current Setup**

```python
# See what models all agents are using
directory = get_agent_directory()

for agent in directory["agents"]:
    if agent["role"] == "worker":
        info = get_agent_model_info(agent["agent_id"])
        print(f"{info['person_name']}:")
        print(f"  Model: {info['model_path']}")
        print(f"  Type: {'API' if 'api://' in info['model_path'] else 'Local'}")
        print(f"  Loaded: {info['model_loaded']}")
```

## 🎊 **Complete Model Options Now:**

### **Option A: Local Fine-tuned (Your Original Plan)**
```python
# Train on social media data
python deploy_agents.py run

# Use trained models
update_agent_model("agent_1", "models/Eddie_Lake_model")
```

### **Option B: Cloud API (Quick Start)**
```python
# Add API key
add_api_key("openai", "your-key")

# Use GPT-4
configure_agent_with_api("agent_1", "openai", "gpt-4")
```

### **Option C: Hybrid (Best of Both)**
```python
# Important agents: Fine-tuned personalities
update_agent_model("agent_1", "models/Eddie_Lake_model")

# Less critical: GPT-4 API
configure_agent_with_api("agent_3", "openai", "gpt-4")
```

## 🚀 **All MCP Functions Updated**

**Total functions now: 25**

- ✅ System management (2)
- ✅ Task management (6)
- ✅ Agent management (4)
- ✅ Model management (6)
- ✅ **API key management (7)** ← NEW!

You have **complete flexibility** in how you power your digital twin agents! 🎯
