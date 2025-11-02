#!/usr/bin/env python3
"""
Run Agents with OpenAI Fine-Tuned Model
Uses your custom fine-tuned OpenAI model from .env
"""
import asyncio
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from digital_twin_backend.config.settings import settings
from digital_twin_backend.config.api_keys import api_key_manager
from digital_twin_backend.communication.shared_knowledge import (
    SharedKnowledgeBase,
    AgentCapabilities,
    AgentContext,
    TaskInfo,
    TaskStatus,
    AgentStatus
)
from digital_twin_backend.communication.protocol import AgentCommunicationProtocol
from digital_twin_backend.agents.manager_agent import ManagerAgent
from digital_twin_backend.agents.worker_agent import WorkerAgent


async def setup_openai_agents():
    """Setup agents to use OpenAI fine-tuned model"""
    
    print("🚀 Setting up Digital Twin Agents with OpenAI")
    print("=" * 70)
    
    # Check environment variables
    print("\n🔍 Checking configuration...")
    
    if not settings.OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY not found in .env file")
        print("   Please add: OPENAI_API_KEY=sk-...")
        return False
    
    print(f"✅ OpenAI API Key: {settings.OPENAI_API_KEY[:20]}...")
    
    if not settings.OPENAI_MODEL_NAME:
        print("⚠️  Warning: OPENAI_MODEL_NAME not set, using default")
        model_name = "gpt-3.5-turbo"
    else:
        model_name = settings.OPENAI_MODEL_NAME
    
    print(f"✅ OpenAI Model: {model_name}")
    
    # Add API key to manager
    print(f"\n🔑 Configuring API key...")
    result = api_key_manager.add_key("openai", settings.OPENAI_API_KEY, "Fine-tuned model")
    
    if result["success"]:
        print(f"✅ API key stored: {result['masked_key']}")
    else:
        print(f"⚠️  API key status: {result.get('message', 'Unknown')}")
    
    # Initialize core systems
    print(f"\n🔧 Initializing agent system...")
    
    shared_knowledge = SharedKnowledgeBase()
    await shared_knowledge.initialize()
    
    protocol = AgentCommunicationProtocol(shared_knowledge)
    await protocol.initialize()
    
    # Create manager with OpenAI
    print(f"\n👔 Creating Manager Agent...")
    manager = ManagerAgent(
        shared_knowledge=shared_knowledge,
        worker_agent_ids=["eddie", "jamik", "sarah"],
        use_api_model=True,  # Use API instead of local model
        api_provider="openai",
        api_model=model_name
    )
    await manager.initialize()
    print(f"✅ Manager using OpenAI model: {model_name}")
    
    # Create worker agents
    print(f"\n👥 Creating Worker Agents...")
    
    workers_config = {
        "eddie": {
            "name": "Eddie Lake",
            "caps": AgentCapabilities(
                technical_skills={"technical": 0.9, "documentation": 0.95, "api": 0.85},
                preferred_task_types=["Technical content", "API Documentation"],
                work_style={},
                communication_style={}
            ),
            "workload": 2
        },
        "jamik": {
            "name": "Jamik Tashpulatov",
            "caps": AgentCapabilities(
                technical_skills={"architecture": 0.95, "backend": 0.9, "technical": 0.85},
                preferred_task_types=["System Architecture", "Backend Development"],
                work_style={},
                communication_style={}
            ),
            "workload": 4
        },
        "sarah": {
            "name": "Sarah Johnson",
            "caps": AgentCapabilities(
                technical_skills={"design": 0.95, "creative": 0.9, "ux": 0.95},
                preferred_task_types=["Visual Design", "UI/UX"],
                work_style={},
                communication_style={}
            ),
            "workload": 1
        }
    }
    
    workers = {}
    for agent_id, config in workers_config.items():
        worker = WorkerAgent(
            agent_id=agent_id,
            person_name=config["name"],
            shared_knowledge=shared_knowledge,
            capabilities=config["caps"],
            use_api_model=True,  # Use OpenAI API
            api_provider="openai",
            api_model=model_name
        )
        await worker.initialize()
        
        await shared_knowledge.update_agent_context(
            agent_id,
            AgentContext(
                agent_id=agent_id,
                current_workload=config["workload"],
                max_capacity=5,
                availability_status=AgentStatus.AVAILABLE
            )
        )
        
        workers[agent_id] = worker
        print(f"   ✅ {config['name']}: Using {model_name}")
    
    print("\n" + "=" * 70)
    print("✅ All agents configured with OpenAI fine-tuned model!")
    print("=" * 70)
    
    return manager, workers, shared_knowledge, protocol


async def run_openai_demo():
    """Run a demo with OpenAI agents"""
    
    # Setup
    result = await setup_openai_agents()
    if not result:
        print("\n❌ Setup failed. Please check your .env configuration.")
        return
    
    manager, workers, shared_knowledge, protocol = result
    
    # Create a test task
    print("\n📋 Creating test task...")
    
    task = TaskInfo(
        task_id="openai_demo_001",
        title="Design RESTful API Architecture",
        description="Design a scalable RESTful API for our microservices platform with proper authentication and rate limiting",
        task_type="System Architecture",
        priority=9,
        estimated_hours=6.0,
        required_skills=["architecture", "backend", "technical"],
        status=TaskStatus.PENDING
    )
    
    print(f"\n📝 Task: {task.title}")
    print(f"   Type: {task.task_type}")
    print(f"   Skills: {', '.join(task.required_skills)}")
    print(f"   Priority: {task.priority}/10")
    
    print("\n🎯 Starting distribution with OpenAI-powered agents...")
    print("=" * 70)
    
    # Distribute
    await shared_knowledge.add_task(task)
    result = await manager.distribute_task(task)
    
    # Show result
    print("\n" + "=" * 70)
    print("✅ TASK DISTRIBUTION COMPLETE")
    print("=" * 70)
    
    if result.get("success"):
        assigned = result["assigned_agent"]
        print(f"\n🎯 Task assigned to: {assigned.upper()}")
        print(f"   Reasoning: {result.get('reasoning', 'N/A')}")
        
        context = await shared_knowledge.get_agent_context(assigned)
        if context:
            print(f"   New workload: {context.current_workload}/{context.max_capacity} ({context.utilization:.0%})")
    else:
        print(f"\n❌ Distribution failed: {result.get('error')}")
    
    # Cleanup
    await protocol.shutdown()
    await shared_knowledge.close()
    
    print("\n✨ Demo complete!")
    print("\n💡 Your agents are now using your fine-tuned OpenAI model!")
    print(f"   Model: {settings.OPENAI_MODEL_NAME}")


async def verify_openai_config():
    """Quick verification of OpenAI configuration"""
    
    print("🔍 OpenAI Configuration Check")
    print("=" * 70)
    
    print("\nEnvironment Variables:")
    print(f"   OPENAI_API_KEY: {'✅ Set' if settings.OPENAI_API_KEY else '❌ Not set'}")
    print(f"   OPENAI_MODEL_NAME: {settings.OPENAI_MODEL_NAME or '❌ Not set'}")
    
    if settings.OPENAI_API_KEY:
        print(f"\nAPI Key (masked): {settings.OPENAI_API_KEY[:20]}...{settings.OPENAI_API_KEY[-4:]}")
    
    print(f"\nModel to use: {settings.OPENAI_MODEL_NAME}")
    
    # Check model type
    if settings.OPENAI_MODEL_NAME.startswith('asst_'):
        print("✅ OpenAI Assistant detected!")
        print(f"   Assistant ID: {settings.OPENAI_MODEL_NAME}")
        print("   Using OpenAI Assistants API")
    elif ':ft-' in settings.OPENAI_MODEL_NAME:
        print("✅ Fine-tuned model detected!")
        base_model = settings.OPENAI_MODEL_NAME.split(':')[0]
        print(f"   Base model: {base_model}")
        print(f"   Fine-tune ID: {settings.OPENAI_MODEL_NAME}")
    else:
        print("ℹ️  Using standard OpenAI model")
    
    print("\n" + "=" * 70)
    
    if not settings.OPENAI_API_KEY:
        print("\n❌ Please add to your .env file:")
        print("   OPENAI_API_KEY=sk-your-api-key")
        print("   OPENAI_MODEL_NAME=gpt-3.5-turbo:ft-your-fine-tune-id")
        return False
    
    print("\n✅ Configuration looks good!")
    return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        # Just verify configuration
        asyncio.run(verify_openai_config())
    else:
        # Run full demo
        asyncio.run(run_openai_demo())

