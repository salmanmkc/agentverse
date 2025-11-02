# 🔑 OpenAI Key Setup & Ryan Lin Configuration

## 📍 Where OpenAI Keys Are Called

### 1. **Primary Location: `agents/base_agent.py` (Line 260)**

When an agent uses the OpenAI API, the key is retrieved and used here:

```python:260:260:digital_twin_backend/agents/base_agent.py
client = openai.OpenAI(api_key=api_key)
```

**Key Retrieval Flow:**
1. `_generate_api_response()` method (line 241) gets called
2. API key is retrieved from `api_key_manager.get_key(self.api_provider)` (line 248)
3. OpenAI client is created with the key (line 260)

### 2. **API Key Storage: `config/api_keys.py`**

API keys are managed by the `APIKeyManager` class:
- Keys are stored in `data/api_keys.json`
- Keys can be loaded from `.env` file (`OPENAI_API_KEY`)
- Keys can be added programmatically via `add_key()`

### 3. **Key Loading in Frontend API: `integration/frontend_api.py` (Line 185-186)**

When the system initializes, it automatically loads the OpenAI key from `.env`:

```python:185:186:digital_twin_backend/integration/frontend_api.py
if settings.OPENAI_API_KEY:
    api_key_manager.add_key("openai", settings.OPENAI_API_KEY, "From .env")
```

## 🤖 Ryan Lin Configuration

### ✅ **What Was Configured**

1. **Added Ryan Lin to Agent Config** (`config/settings.py`)
   - Agent ID: `ryan_lin`
   - Person Name: `Ryan Lin`
   - Capabilities: Technical (0.9), Research (0.95), Communication (0.85)

2. **Added Ryan Lin to Worker Agent List** (`config/settings.py`)
   - Added `"ryan_lin"` to `WORKER_AGENT_IDS`

3. **Configured OpenAI Assistant** (`integration/frontend_api.py`)
   - Ryan Lin uses OpenAI Assistant API
   - Assistant ID: `asst_Z0iNwOpGtqooVPFMutWfz15G`
   - Uses `use_api_model=True`
   - Provider: `openai`

### 📝 **Configuration Details**

**In `config/settings.py`:**
```python
"ryan_lin": AgentConfig("ryan_lin", "Ryan Lin", {
    "technical": 0.9, 
    "research": 0.95, 
    "communication": 0.85
}),
```

**In `integration/frontend_api.py`:**
```python
# Ryan Lin uses custom finetuned OpenAI assistant
if agent_id == "ryan_lin":
    use_api_model = True
    api_provider = "openai"
    api_model = "asst_Z0iNwOpGtqooVPFMutWfz15G"
```

## 🔄 How It Works

### OpenAI Assistant API Flow

When Ryan Lin generates a response:

1. **Prompt Building** (`base_agent.py:254`)
   - Contextual prompt is built with Ryan Lin's personality, skills, and current situation

2. **Assistant API Detection** (`base_agent.py:263`)
   - Checks if `api_model.startswith('asst_')`
   - Since Ryan Lin uses `asst_Z0iNwOpGtqooVPFMutWfz15G`, it uses Assistants API

3. **Assistant API Call** (`base_agent.py:265-300`)
   - Creates a new thread
   - Adds the prompt as a user message
   - Runs the assistant with the configured assistant ID
   - Waits for completion and returns the response

### Complete Flow:

```
generate_response()
  ↓
_build_contextual_prompt() → Adds personality/context
  ↓
_generate_api_response()
  ↓
api_key_manager.get_key("openai") → Gets API key
  ↓
openai.OpenAI(api_key=...) → Creates client
  ↓
client.beta.threads.create() → Creates thread
  ↓
client.beta.threads.runs.create(assistant_id="asst_Z0iNwOpGtqooVPFMutWfz15G")
  ↓
Returns response from finetuned assistant
```

## ✅ Requirements

### 1. **Environment Variable**
Make sure your `.env` file has:
```env
OPENAI_API_KEY=sk-your-actual-key-here
```

### 2. **API Key Location**
The key is:
- Loaded from `.env` → `settings.OPENAI_API_KEY`
- Stored in `data/api_keys.json` via `api_key_manager`
- Retrieved when making API calls via `api_key_manager.get_key("openai")`

## 🧪 Testing

To verify Ryan Lin is using your assistant:

1. **Check Agent Status:**
   ```bash
   curl http://localhost:8000/api/agents/ryan_lin
   ```

2. **Create a Task:**
   ```bash
   curl -X POST http://localhost:8000/api/tasks \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Test Task",
       "description": "Test if Ryan Lin uses the assistant",
       "task_type": "Research",
       "priority": 7,
       "estimated_hours": 2
     }'
   ```

3. **Check Logs:**
   When Ryan Lin responds, you should see:
   - `🔄 Loading model for ryan_lin...`
   - API calls going to OpenAI with assistant ID `asst_Z0iNwOpGtqooVPFMutWfz15G`

## 📋 Summary

✅ **OpenAI keys are called in:**
- `agents/base_agent.py:260` - Main API call location
- `agents/base_agent.py:248` - Key retrieval location

✅ **Ryan Lin is configured to use:**
- OpenAI Assistant ID: `asst_Z0iNwOpGtqooVPFMutWfz15G`
- Automatic API key loading from `.env`
- Full assistant API integration

✅ **Files Modified:**
- `config/settings.py` - Added Ryan Lin agent config
- `integration/frontend_api.py` - Added OpenAI Assistant setup for Ryan Lin

The system will now automatically use your custom finetuned OpenAI assistant when Ryan Lin generates responses!

