# 🤖 MCP Model Selection Functions - Usage Guide

## ✅ **NEW Functions Added to MCP Server**

You can now manage agent models through the MCP server!

### **Available Model Functions:**

## 1️⃣ **List Available Models**

See all trained models in your `models/` directory:

```python
# MCP Tool Call
list_available_models()

# Returns:
{
  "models": [
    {
      "name": "Eddie_Lake_model",
      "path": "models/Eddie_Lake_model",
      "has_config": true,
      "has_adapter": true,
      "has_tokenizer": true,
      "size_mb": 245.3
    },
    {
      "name": "Jamik_Tashpulatov_model",
      "path": "models/Jamik_Tashpulatov_model",
      "has_config": true,
      "has_adapter": true,
      "has_tokenizer": true,
      "size_mb": 312.7
    }
  ],
  "total": 2,
  "models_dir": "./models"
}
```

## 2️⃣ **Get Agent's Current Model**

Check what model an agent is using:

```python
# MCP Tool Call
get_agent_model_info("agent_1")

# Returns:
{
  "agent_id": "agent_1",
  "person_name": "Eddie Lake",
  "model_path": "models/Eddie_Lake_model",
  "model_loaded": true,
  "has_fine_tuned_model": true,
  "using_fallback": false,
  "capabilities": {
    "technical": 0.8,
    "documentation": 0.9
  }
}
```

## 3️⃣ **Update Agent's Model**

Switch which model an agent uses:

```python
# MCP Tool Call
update_agent_model(
  agent_id="agent_1",
  model_path="models/Eddie_Lake_model",
  reload=true
)

# Returns:
{
  "message": "Model updated for Eddie Lake",
  "agent_id": "agent_1",
  "old_model_path": null,
  "new_model_path": "models/Eddie_Lake_model",
  "model_loaded": true,
  "reload_attempted": true
}
```

## 4️⃣ **Configure Agent Completely**

Update name, model, and capabilities in one call:

```python
# MCP Tool Call
configure_agent(
  agent_id="agent_1",
  person_name="Eddie Lake",
  model_path="models/Eddie_Lake_model",
  capabilities={"technical": 0.9, "documentation": 0.85, "api": 0.8}
)

# Returns:
{
  "message": "Agent agent_1 configured successfully",
  "agent_id": "agent_1",
  "updates": {
    "person_name": "Eddie Lake",
    "model_path": "models/Eddie_Lake_model",
    "model_loaded": true,
    "capabilities": {
      "technical": 0.9,
      "documentation": 0.85,
      "api": 0.8
    }
  }
}
```

## 5️⃣ **Reload Agent Model**

Reload model from disk (useful after retraining):

```python
# MCP Tool Call
reload_agent_model("agent_1")

# Returns:
{
  "message": "Model reloaded for Eddie Lake",
  "agent_id": "agent_1",
  "model_path": "models/Eddie_Lake_model",
  "model_loaded": true
}
```

## 6️⃣ **Set Base Model**

Change the base model for future training:

```python
# MCP Tool Call
set_base_model("meta-llama/Llama-2-7b-chat-hf")

# Returns:
{
  "message": "Base model updated",
  "base_model": "meta-llama/Llama-2-7b-chat-hf",
  "note": "This affects new training operations. Existing models unchanged."
}
```

## 🎯 **Real-World Usage Scenarios**

### **Scenario 1: After Training a New Model**

```python
# 1. Check available models
models = list_available_models()
# See: "Eddie_Lake_model" is now available

# 2. Update agent to use new model
update_agent_model(
  agent_id="agent_1",
  model_path="models/Eddie_Lake_model",
  reload=true
)

# 3. Verify it loaded
info = get_agent_model_info("agent_1")
# model_loaded: true ✅

# 4. Create a task to test the personality
create_task(
  title="Test Eddie's Personality",
  description="See how Eddie responds",
  task_type="Technical content",
  priority=5,
  estimated_hours=1
)
```

### **Scenario 2: Hot-Swap Models for Testing**

```python
# Try different models for same agent
update_agent_model("agent_1", "models/Eddie_Lake_model")
# Test response

update_agent_model("agent_1", "models/Alternative_Model") 
# Test response

# Compare which works better!
```

### **Scenario 3: Setup New Team Member**

```python
# 1. Configure new agent completely
configure_agent(
  agent_id="agent_3",
  person_name="Sarah Johnson",
  model_path="models/Sarah_Johnson_model",
  capabilities={
    "creative": 0.9,
    "design": 0.95,
    "frontend": 0.8
  }
)

# 2. Verify setup
get_agent_model_info("agent_3")

# 3. Agent is ready to receive tasks!
```

### **Scenario 4: Check All Agent Models**

```python
# Get directory of all agents
directory = get_agent_directory()

# For each agent, check their model
for agent in directory["agents"]:
    if agent["role"] == "worker":
        info = get_agent_model_info(agent["agent_id"])
        print(f"{info['person_name']}: {info['model_path']}")
```

## 📡 **How to Use MCP Server**

### **Start MCP Server:**
```bash
# Install MCP
source venv/bin/activate
pip install mcp

# Run MCP server
python -m digital_twin_backend.mcp.server
```

### **Call Functions:**

The MCP server exposes all these functions as tools that can be called by:
- Claude Desktop
- Other MCP clients
- Your custom integrations

### **Direct Python Usage:**
```python
import asyncio
from digital_twin_backend.mcp.server import create_app

async def test_model_functions():
    app = create_app()
    
    # Initialize
    await app.call_tool("initialize_system", {})
    
    # List models
    models = await app.call_tool("list_available_models", {})
    print(f"Available models: {len(models['models'])}")
    
    # Update agent model
    result = await app.call_tool("update_agent_model", {
        "agent_id": "agent_1",
        "model_path": "models/Eddie_Lake_model",
        "reload": True
    })
    print(f"Model update: {result['message']}")

asyncio.run(test_model_functions())
```

## 🎊 **What You Can Do Now:**

✅ **List all trained models** in your system
✅ **Check which model each agent is using**
✅ **Switch agent models** on the fly
✅ **Reload models** after retraining
✅ **Configure agents** completely (name + model + capabilities)
✅ **Change base model** for future training

## 🎯 **Summary**

**MCP Server Now Provides:**
- ✅ Task management (create, assign, status)
- ✅ Agent management (list, status, directory)
- ✅ **Model management (list, update, reload, configure)** ← NEW!

You have **complete control** over which models your agents use through simple MCP function calls! 🚀
