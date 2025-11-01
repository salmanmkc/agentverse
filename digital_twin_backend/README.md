# Digital Twin Workplace Backend

A comprehensive backend system for creating and managing digital twin agents that simulate workplace team dynamics and task distribution.

## 🎯 Overview

This system creates **personalized digital twin agents** fine-tuned on real team members' communication patterns. The agents use a **two-phase task distribution process**:

1. **Phase 1**: Manager consults each agent individually about task capability
2. **Phase 2**: Agents negotiate among themselves to determine optimal assignment

## 🏗️ System Architecture

```
Frontend (Next.js) → FastAPI → Manager Agent → [Worker Agents]
                                     ↓
         Redis ← Shared Knowledge ← → Communication Protocol
                        ↓
              Fine-tuning Pipeline ← Social Media Scrapers
```

### Core Components

- **Agents**: Manager and Worker agents with personalized models
- **Shared Knowledge**: Central state management for tasks, agent contexts, and capabilities  
- **Communication Protocol**: Message routing and agent-to-agent communication
- **Fine-tuning System**: Scrapes social media data and trains personalized models
- **Frontend Integration**: REST API and WebSocket support for dashboard

## 🚀 Quick Start

### 1. Installation

```bash
cd digital_twin_backend
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file:

```env
DEBUG=True
API_HOST=localhost
API_PORT=8000
DATABASE_URL=sqlite:///./digital_twins.db
REDIS_URL=redis://localhost:6379
BASE_MODEL_NAME=microsoft/DialoGPT-medium
SCRAPING_ENABLED=False
```

### 3. Start the System

```bash
# Start the API server
python main.py

# Or initialize manually in Python
python -c "
from main import create_app
import asyncio

async def run():
    app = await create_app()
    # System is ready for API calls
    print('System initialized!')

asyncio.run(run())
"
```

### 4. Initialize Agents

```bash
# Make API call to initialize the agent system
curl -X POST http://localhost:8000/api/initialize
```

## 🧠 Fine-tuning Process

### Step 1: Setup Data Collection

```bash
# Create consent and scrape social media data
python finetuning.py setup "John Smith" "john@company.com" whatsapp linkedin

# This will:
# - Create consent record with token
# - Scrape WhatsApp Web and LinkedIn messages (with user consent)
# - Process data for training
# - Analyze communication patterns
```

### Step 2: Train Individual Agent

```bash
# Train a specific person's digital twin
python finetuning.py train "John Smith" agent_1

# This will:
# - Load training data
# - Fine-tune base LLM with LoRA
# - Save personalized model
# - Update agent configuration
```

### Step 3: Train All Agents

```bash
# Batch train all configured agents
python finetuning.py train_all
```

## 📡 API Endpoints

### System Management
- `POST /api/initialize` - Initialize agent system
- `GET /api/status` - Get system status

### Task Management
- `POST /api/tasks` - Create new task (triggers automatic distribution)
- `GET /api/tasks` - List all tasks
- `GET /api/tasks/{task_id}` - Get specific task
- `PUT /api/tasks/{task_id}/assign` - Manually assign task

### Agent Management
- `GET /api/agents` - List all agents and their status
- `GET /api/agents/{agent_id}` - Get specific agent status
- `PUT /api/agents/{agent_id}/availability` - Update agent availability

### Frontend Integration
- `GET /api/dashboard/data` - Get data in frontend format
- `POST /api/dashboard/sync` - Sync data from frontend
- `WebSocket /ws` - Real-time updates

## 🎭 Agent Personalities

Each agent is fine-tuned on:

### Data Sources
- **WhatsApp Messages**: Casual communication style
- **LinkedIn Messages**: Professional interactions
- **Twitter/X DMs**: Quick, informal exchanges

### Personality Extraction
- **Technical Skills**: Keyword analysis for capabilities
- **Communication Style**: Formal vs. casual, verbose vs. concise
- **Work Preferences**: Collaborative vs. independent
- **Decision Patterns**: Risk tolerance, detail orientation

## 🔄 Task Distribution Flow

### Example Scenario

```python
# New task arrives
task = TaskInfo(
    title="API Documentation Update",
    task_type="Technical content", 
    priority=7,
    estimated_hours=4,
    required_skills=["documentation", "api"]
)

# Phase 1: Manager consults each agent
manager_to_alice: "Can you handle API documentation? 4 hours, high priority."
alice_response: "Yes, I'm confident with API docs but I'm pretty busy this week..."

manager_to_bob: "Can you handle API documentation? 4 hours, high priority."  
bob_response: "Absolutely! I just finished similar work and have capacity."

# Phase 2: Agents negotiate
alice_to_bob: "I could do it but you're better suited and less busy right now."
bob_to_alice: "Thanks Alice, I'll take it. Want me to run the final draft by you?"

# Result: Task assigned to Bob with collaborative approach
```

## 🛠️ Customization

### Adding New Agents

```python
# In config/settings.py
AGENT_CONFIGS = {
    "new_agent": AgentConfig(
        "new_agent", 
        "Jane Doe", 
        {"technical": 0.9, "creative": 0.6}
    )
}
```

### Custom Communication Patterns

Modify the `_analyze_communication_patterns()` method in `finetuning.py` to detect specific patterns:

```python
# Add custom keyword detection
leadership_keywords = ['delegate', 'prioritize', 'strategy']
technical_keywords = ['bug', 'deploy', 'optimization']
```

### Task Type Mapping

Update frontend task types in `integration/frontend_api.py`:

```python
# Map your frontend task types to agent capabilities
task_type_mapping = {
    "Technical content": ["technical", "documentation"],
    "Design": ["creative", "visual"],
    "Planning": ["leadership", "coordination"]
}
```

## 🏃‍♂️ Development Workflow

### For Your Hackathon

1. **Setup the basic system** (this is done ✅)
2. **Configure your team members** in `config/settings.py`
3. **Create consent records** for data scraping
4. **Scrape real data** (WhatsApp Web, LinkedIn) with consent
5. **Fine-tune models** for each person  
6. **Test task distribution** via API
7. **Connect to your Next.js dashboard**

### Key Files to Modify

- `config/settings.py` - Agent configurations
- `finetuning.py` - Training pipeline
- `integration/frontend_api.py` - Frontend connection

## 🔒 Privacy & Consent

The system includes comprehensive consent management:

- **Explicit consent tokens** for each person/platform combination
- **Data expiration** and cleanup
- **Local storage** of all personal data
- **Scraping controls** via environment variables

## 🧪 Testing

```bash
# Test individual components
python -m pytest tests/

# Test task distribution
python -c "
import asyncio
from main import create_app

async def test_task():
    app = await create_app()
    # Create test task through API
"

# Test fine-tuning pipeline
python finetuning.py setup "Test User" "test@example.com"
```

## 🚨 Important Notes

- **Redis** is required for agent communication
- **Chrome/Selenium** needed for social media scraping
- **GPU recommended** for fine-tuning (but works on CPU)
- **Consent required** before scraping any personal data
- **Models are saved locally** - no cloud dependencies

## 📋 TODO for Production

- [ ] Authentication & authorization
- [ ] Database migrations with Alembic
- [ ] Model versioning and rollback
- [ ] Advanced conversation context
- [ ] Performance monitoring
- [ ] Distributed training support

---

**Built for UCL Hackathon** 🎯

This system demonstrates advanced AI agent coordination with personalized digital twins. Perfect for showcasing realistic workplace automation and human-AI collaboration patterns.
