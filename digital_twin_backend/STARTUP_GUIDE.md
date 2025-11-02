# 🚀 Digital Twin Agents - Complete Startup Guide

This guide walks you through setting up your complete digital twin workplace system from scratch.

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Python 3.8+** installed
- [ ] **Chrome browser** (for social media scraping)
- [ ] **Redis server** (optional, for persistence)
- [ ] **Social media account access** for each team member
- [ ] **Consent from team members** for data scraping
- [ ] **At least 4GB RAM** (8GB+ recommended for training)

## 🛠️ Step 1: Installation & Setup

### 1.1 Clone and Install Dependencies

```bash
cd digital_twin_backend
pip install -r requirements.txt
```

### 1.2 Create Environment Configuration

Create `.env` file:

```env
DEBUG=True
API_HOST=localhost
API_PORT=8000
DATABASE_URL=sqlite:///./digital_twins.db
REDIS_URL=redis://localhost:6379
BASE_MODEL_NAME=microsoft/DialoGPT-medium
SCRAPING_ENABLED=True
SELENIUM_HEADLESS=False
LOG_LEVEL=INFO
```

### 1.3 Test Basic Setup

```bash
python test_pipeline.py
```

**Expected Output:**
```
✅ Configuration Loading
✅ Fine-tuning Setup  
✅ Shared Knowledge System
✅ Communication Protocol
✅ Agent Initialization
✅ Task Distribution
🎉 All tests passed!
```

## ⚙️ Step 2: Configure Your Team

### 2.1 Update Agent Configuration

Edit `agent_training_config.json` with your real team information:

```json
{
  "training_pipeline": {
    "base_model": "microsoft/DialoGPT-medium",
    "auto_deploy_after_training": true
  },
  "agents": {
    "agent_1": {
      "person_name": "Your Teammate Name",
      "email": "teammate@company.com",
      "social_accounts": {
        "whatsapp_phone": "+1-XXX-XXX-XXXX",
        "linkedin_profile_url": "https://linkedin.com/in/teammate",
        "twitter_profile_url": "https://twitter.com/teammate"
      },
      "scraping_config": {
        "platforms": ["whatsapp", "linkedin"],
        "max_messages_per_platform": 500
      },
      "agent_role": {
        "primary_skills": ["technical", "documentation"],
        "task_preferences": ["Technical content", "API Documentation"]
      }
    }
  }
}
```

### 2.2 Verify Configuration

```bash
python -c "
import json
with open('agent_training_config.json') as f:
    config = json.load(f)
print(f'✅ Config loaded: {len(config[\"agents\"])} agents configured')
for aid, agent in config['agents'].items():
    print(f'   👤 {agent[\"person_name\"]} - {agent[\"scraping_config\"][\"platforms\"]}')
"
```

## 📱 Step 3: Data Collection & Training

### 3.1 Complete Pipeline (Recommended)

```bash
# Run everything in one go
python deploy_agents.py run
```

This will:
1. ✅ Create consent records
2. 🕸️ Launch browsers for social media scraping (manual login required)
3. 🧠 Train personalized models using scraped data
4. 🚀 Deploy agents ready for use

### 3.2 Step-by-Step Pipeline (Alternative)

If you prefer more control:

```bash
# Step 1: Create consent records
python train_pipeline.py create-consents

# Step 2: Scrape social media data
python train_pipeline.py scrape-all
# (Manual login required for WhatsApp/LinkedIn/Twitter)

# Step 3: Train models
python train_pipeline.py train-all

# Step 4: Check status
python train_pipeline.py status
```

## 🔐 Step 4: Social Media Login Process

When scraping starts, you'll see browser windows opening:

### WhatsApp Web Login
1. Browser opens to `web.whatsapp.com`
2. **Scan QR code** with your phone
3. Wait for chat list to load
4. Scraper automatically extracts messages

### LinkedIn Login  
1. Browser opens to LinkedIn login page
2. **Enter credentials manually**
3. Navigate to messaging if needed
4. Scraper extracts direct messages

### Twitter/X Login
1. Browser opens to Twitter login
2. **Enter credentials manually** 
3. May require 2FA verification
4. Scraper extracts DMs

**🔒 Privacy Note:** All scraped data stays local on your machine.

## 🧠 Step 5: Training Process

### What Happens During Training

For each team member:

1. **Data Processing**
   - Filters messages (min 10 characters, text only)
   - Extracts only messages **sent by** the person
   - Creates training pairs: `"Respond as [Person]:" → "Their actual message"`

2. **Communication Analysis**
   - **Technical skills:** Detects keywords like "API", "database", "bug"
   - **Creative skills:** Finds "design", "creative", "visual" 
   - **Leadership:** Identifies "team", "strategy", "coordinate"
   - **Communication style:** Formal vs casual language patterns

3. **Model Fine-tuning**
   - Uses LoRA (efficient fine-tuning) on base model
   - Trains for 3 epochs (~5-15 minutes per agent)
   - Saves personalized model for each agent

### Training Progress Output

```
🧠 Training model for Eddie Lake...
   Training data: 847 messages
   Epochs: 3
   Learning rate: 5e-4
   
🔄 Loading base model...
✅ Model trained for Eddie Lake
   Training time: 312.5s
   Training samples: 678
   Model saved to: models/Eddie_Lake_model/
```

## 🚀 Step 6: Deployment & Testing

### 6.1 Check Deployment Status

```bash
python deploy_agents.py status
```

**Expected Output:**
```
✅ Eddie Lake - READY TO USE
✅ Jamik Tashpulatov - READY TO USE  
✅ Sarah Johnson - READY TO USE
🎉 3 digital twin agents are live!
```

### 6.2 Start the API Server

```bash
python main.py
```

**Expected Output:**
```
🚀 Starting Digital Twin Backend...
✅ Core systems initialized successfully
🌐 Starting server on localhost:8000
```

### 6.3 Test Agent System

```bash
# Test system initialization
curl -X POST http://localhost:8000/api/initialize

# Create a test task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API Documentation Review",
    "description": "Review and update API documentation",
    "task_type": "Technical content", 
    "priority": 7,
    "estimated_hours": 3
  }'

# Check task assignment
curl http://localhost:8000/api/tasks

# View agent directory (count + names)
curl http://localhost:8000/api/agents/directory

# Rename an agent and persist to disk (data/agent_profiles.json)
curl -X PUT http://localhost:8000/api/agents/agent_1/name \
  -H "Content-Type: application/json" \
  -d '{"person_name": "Alex Doe"}'
```

### 6.4 Connect Your Frontend

Your Next.js dashboard can now connect to:
- **API:** `http://localhost:8000`
- **WebSocket:** `ws://localhost:8000/ws`
- **Dashboard data:** `GET /api/dashboard/data`

## 🎯 Step 7: See It In Action

### Task Distribution Example

1. **New Task Arrives:** "Update API documentation" 
2. **Phase 1 - Manager Consultation:**
   - Manager: "Eddie, can you handle API docs? 3 hours, high priority."
   - Eddie: "Yes, I'm good with API docs but pretty busy this week."
   - Manager: "Jamik, can you handle API docs?"
   - Jamik: "Absolutely, just finished similar work."

3. **Phase 2 - Peer Negotiation:**
   - Eddie: "I could do it but Jamik's better suited and less busy."
   - Jamik: "Thanks Eddie, I'll take it. Want me to run the draft by you?"

4. **Result:** Task assigned to Jamik with collaborative approach

## 🔧 Troubleshooting

## 🔌 (Optional) MCP Server

Run a stdio MCP server to control agents programmatically via MCP tools (no FastAPI needed).

```bash
pip install mcp
python -m digital_twin_backend.mcp.server
```

Tools available:

- initialize_system
- get_system_status
- create_task
- get_tasks / get_task
- assign_task / update_task_status
- get_agents / get_agent_status
- get_agent_directory / update_agent_name

Use any MCP-compatible client to connect over stdio.


### Common Issues & Solutions

**❌ "Import error" when running scripts**
```bash
# Make sure you're in the right directory
cd digital_twin_backend
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

**❌ "No valid consent" during scraping**
```bash
# Re-create consent records
python train_pipeline.py create-consents
```

**❌ "Chrome/ChromeDriver" not found**
```bash
# Install Chrome and ChromeDriver
# On macOS: brew install chromedriver
# On Ubuntu: apt-get install chromium-chromedriver
```

**❌ "Insufficient training data"**
- Need at least 50 messages per person
- Check privacy settings on social media accounts
- Try different platforms or longer message history

**❌ Redis connection failed**
```bash
# Install and start Redis (optional)
# On macOS: brew install redis && brew services start redis
# On Ubuntu: apt-get install redis-server
# Or just run without Redis (uses in-memory storage)
```

**❌ Model training out of memory**
```bash
# Reduce batch size in agent_training_config.json
"training_config": {
  "batch_size": 2,
  "gradient_accumulation_steps": 4
}
```

## 📊 Monitoring & Status

### Check Overall Status
```bash
python deploy_agents.py status
```

### View Training Details
```bash
cat data/pipeline_status.json
```

### Monitor Agent Performance
```bash
# API endpoints
curl http://localhost:8000/api/agents        # All agent status
curl http://localhost:8000/api/system/stats  # System statistics
```

## 🎉 Success Indicators

Your system is working correctly when you see:

✅ **All tests pass:** `python test_pipeline.py`
✅ **Agents trained:** Multiple `.../model/` directories created
✅ **API responds:** `curl http://localhost:8000/api/status` returns system info
✅ **Task assignment works:** Tasks get assigned to appropriate agents
✅ **Agents negotiate:** Check logs for agent-to-agent communication
✅ **Frontend connects:** Your Next.js dashboard shows live data

## 🚀 Next Steps

Once your system is running:

1. **Integrate with your frontend** using the API endpoints
2. **Create realistic tasks** through the API to test agent behavior
3. **Monitor agent decisions** and communication patterns
4. **Refine training data** by adjusting scraping parameters
5. **Scale up** by adding more team members to the configuration

## 🎯 For Your Hackathon

You now have a **working digital twin workplace** that:
- **Scrapes real communication data** from your team
- **Creates personalized AI agents** that talk like real team members
- **Distributes tasks intelligently** using two-phase negotiation
- **Integrates with your dashboard** via REST API + WebSocket
- **Demonstrates advanced AI coordination** for workplace automation

**This is a complete, functional system ready for demo! 🎊**

---

**Need help?** Check the logs in `logs/` directory or run components individually to debug issues.
