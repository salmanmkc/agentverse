# 🚀 MCP Server - Quick Start Guide

## ✅ **MCP Server Successfully Installed & Configured!**

Your MCP server has **25 tools** for managing the digital twin workplace.

### **🎯 What is the MCP Server?**

The Model Context Protocol (MCP) server exposes your digital twin backend as tools that can be called by:
- **Claude Desktop** - Use digital twins directly in Claude
- **Other AI assistants** - Integrate with any MCP client
- **Custom applications** - Call tools programmatically

### **🚀 Start the MCP Server**

```bash
# Navigate to backend
cd digital_twin_backend

# Activate virtual environment
source venv/bin/activate

# Start MCP server
python -m digital_twin_backend.mcp_integration.server
```

### **📋 Available Tools (25 Total)**

**📡 System Management (2 tools):**
- ✅ `initialize_system()` - Start the agent system
- ✅ `get_system_status()` - Get system health and statistics

**📋 Task Management (6 tools):**
- ✅ `create_task()` - Create and auto-distribute tasks
- ✅ `get_tasks()` - List all tasks (filter by status)
- ✅ `get_task()` - Get specific task details
- ✅ `assign_task()` - Manually assign or trigger distribution
- ✅ `update_task_status()` - Update task status

**👥 Agent Management (4 tools):**
- ✅ `get_agents()` - List all agents with status
- ✅ `get_agent_status()` - Get specific agent details
- ✅ `get_agent_directory()` - Agent directory with roles
- ✅ `update_agent_name()` - Change agent name

**🤖 Model Management (6 tools):**
- ✅ `list_available_models()` - See all trained models
- ✅ `get_agent_model_info()` - Check agent's current model
- ✅ `update_agent_model()` - Switch agent's model
- ✅ `configure_agent()` - Update agent name/model/capabilities
- ✅ `reload_agent_model()` - Reload model from disk
- ✅ `set_base_model()` - Change base model for training

**🔑 API Key Management (7 tools):**
- ✅ `add_api_key()` - Add OpenAI/Claude/etc. API key
- ✅ `list_api_keys()` - View all API keys (masked)
- ✅ `remove_api_key()` - Delete an API key
- ✅ `validate_api_key()` - Test if key works
- ✅ `get_api_key_status()` - Check key configuration
- ✅ `configure_agent_with_api()` - Use API model for agent
- ✅ `list_supported_api_providers()` - See supported APIs

### **💡 Example Usage**

```bash
# Start the server
python -m digital_twin_backend.mcp_integration.server

# Server exposes all tools via MCP protocol
# Can be called from Claude Desktop or other MCP clients
```

### **🧪 Test Without MCP Client**

```bash
# Test core functionality
python test_mcp_server.py

# Shows:
# ✅ System initialization working
# ✅ Agent management working  
# ✅ Model management working
# ✅ API key management working
# ✅ Task distribution working
```

### **🎯 Use Cases**

**1. Quick Task Distribution:**
```
Call: create_task("Update API docs", "Write examples", "Technical content", 7, 3)
Result: Task auto-assigned to best agent
```

**2. Check Team Status:**
```
Call: get_agents()
Result: See all agent workloads and availability
```

**3. Switch Agent Models:**
```
Call: update_agent_model("agent_1", "models/Eddie_Lake_model", true)
Result: Agent now uses Eddie's personality
```

**4. Add OpenAI API:**
```
Call: add_api_key("openai", "sk-proj-your-key")
Call: configure_agent_with_api("agent_1", "openai", "gpt-4")
Result: Agent uses GPT-4 instead of local model
```

### **📖 Full Tool Reference**

See `MCP_MODEL_SELECTION.md` and `API_KEY_MANAGEMENT.md` for detailed examples of each tool.

### **🎉 Your MCP Server is Ready!**

The server provides complete control over your digital twin workplace through simple tool calls.

**Perfect for:**
- 🤖 Integrating with Claude Desktop
- 🔧 Programmatic control of agents
- 🧪 Experimenting with different models
- 🚀 Quick task distribution and management

---

**Start the server and your digital twins are accessible via MCP!** 🎯
