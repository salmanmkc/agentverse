#!/usr/bin/env python3
"""
Quick Start Script for Digital Twin Backend
"""
import asyncio
import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

print("🎯 Digital Twin Workplace - Quick Start")
print("=====================================")

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        "fastapi", "uvicorn", "redis", "selenium", 
        "torch", "transformers", "datasets", "peft"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ Missing required packages:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\n📦 Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages found")
    return True

def check_redis():
    """Check if Redis is available"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_timeout=1)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        print("   System will use in-memory storage (no persistence)")
        return False

def setup_directories():
    """Create necessary directories"""
    directories = [
        "models",
        "data/scraped",
        "data/training", 
        "data/consent",
        "data/browser_profiles"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories created")

async def quick_demo():
    """Run a quick demo of the system"""
    print("\n🚀 Starting Quick Demo...")
    
    try:
        # Import main components
        from communication.shared_knowledge import SharedKnowledgeBase
        from communication.protocol import AgentCommunicationProtocol
        from agents.manager_agent import ManagerAgent
        from agents.worker_agent import WorkerAgent
        from communication.shared_knowledge import (
            TaskInfo, AgentCapabilities, TaskStatus
        )
        from config.settings import AGENT_CONFIGS
        
        # Initialize core systems
        print("🔄 Initializing shared knowledge...")
        shared_knowledge = SharedKnowledgeBase()
        await shared_knowledge.initialize()
        
        print("🔄 Initializing communication protocol...")
        communication_protocol = AgentCommunicationProtocol(shared_knowledge)
        await communication_protocol.initialize()
        
        # Create a simple manager agent
        print("🔄 Creating manager agent...")
        manager = ManagerAgent(shared_knowledge)
        await manager.initialize()
        
        # Create a worker agent
        print("🔄 Creating worker agent...")
        agent_config = list(AGENT_CONFIGS.values())[1]  # Skip manager
        
        worker = WorkerAgent(
            agent_id=agent_config.agent_id,
            person_name=agent_config.person_name,
            shared_knowledge=shared_knowledge,
            capabilities=AgentCapabilities(
                technical_skills=agent_config.capabilities
            )
        )
        await worker.initialize()
        
        # Create a demo task
        print("🔄 Creating demo task...")
        demo_task = TaskInfo(
            task_id="demo_task_001",
            title="System Integration Testing", 
            description="Test the digital twin agent system",
            task_type="Technical content",
            priority=5,
            estimated_hours=2.0,
            required_skills=["testing", "integration"]
        )
        
        # Test task distribution
        print("🔄 Testing task distribution...")
        result = await manager.distribute_task(demo_task)
        
        if result.get("success"):
            print(f"✅ Demo task assigned to: {result['assigned_agent']}")
            print(f"   Reasoning: {result['reasoning']}")
        else:
            print(f"⚠️  Demo task assignment failed: {result.get('error')}")
        
        # Get system status
        team_status = await manager.get_team_status()
        print(f"\n📊 System Status:")
        print(f"   Active agents: {team_status['active_agents']}")
        print(f"   Available agents: {team_status['available_agents']}")
        
        # Cleanup
        await communication_protocol.shutdown()
        await shared_knowledge.close()
        
        print("\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

async def start_api_server():
    """Start the full API server"""
    print("\n🌐 Starting API Server...")
    
    try:
        from main import main
        await main()
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed: {e}")

def show_next_steps():
    """Show next steps for development"""
    print("\n📋 Next Steps:")
    print("1. 🔧 Configure your team in config/settings.py")
    print("2. 📱 Set up consent for data scraping:")
    print("   python finetuning.py setup 'Your Name' 'email@company.com'")
    print("3. 🧠 Train agent models:")
    print("   python finetuning.py train 'Your Name' agent_1")
    print("4. 🌐 Start the API server:")
    print("   python main.py")
    print("5. 🔗 Connect your Next.js frontend to:")
    print("   http://localhost:8000")
    print("\n📖 See README.md for full documentation")

def main():
    """Main entry point"""
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check Redis
    redis_available = check_redis()
    
    # Setup directories
    setup_directories()
    
    # Ask user what to do
    print("\n🎯 What would you like to do?")
    print("1. Run quick demo (test core functionality)")
    print("2. Start API server (for frontend integration)")
    print("3. Show next steps")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            asyncio.run(quick_demo())
        elif choice == "2":
            asyncio.run(start_api_server())
        elif choice == "3":
            show_next_steps()
        else:
            print("Invalid choice. Showing next steps...")
            show_next_steps()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        show_next_steps()

if __name__ == "__main__":
    main()
