#!/usr/bin/env python3
"""
Watch Agent Chat - See Full Conversation Logs
Shows detailed messages between agents during task negotiation
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from digital_twin_backend.communication.shared_knowledge import (
    SharedKnowledgeBase,
    AgentCapabilities,
    AgentContext,
    TaskInfo,
    TaskStatus,
    AgentStatus
)
from digital_twin_backend.communication.protocol import AgentCommunicationProtocol, Message
from digital_twin_backend.agents.manager_agent import ManagerAgent
from digital_twin_backend.agents.worker_agent import WorkerAgent


class ChatLogger:
    """Logs and displays all agent communications"""
    
    def __init__(self):
        self.messages = []
        self.message_count = 0
    
    def log_message(self, msg: Message):
        """Log a message with formatting"""
        self.message_count += 1
        self.messages.append(msg)
        
        # Format based on message type
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print("\n" + "─" * 70)
        print(f"📨 Message #{self.message_count} [{timestamp}]")
        print("─" * 70)
        
        # Sender and receiver
        from_name = self._get_agent_name(msg.sender_id)
        to_name = self._get_agent_name(msg.receiver_id)
        
        print(f"From: {from_name} ({msg.sender_id})")
        print(f"To:   {to_name} ({msg.receiver_id})")
        print(f"Type: {msg.message_type}")
        
        # Content
        if msg.content:
            print(f"\n💬 Message Content:")
            if isinstance(msg.content, dict):
                for key, value in msg.content.items():
                    if key == "message":
                        print(f"   📝 {value}")
                    elif key == "reasoning":
                        print(f"   🤔 Reasoning: {value}")
                    elif key == "confidence":
                        print(f"   ✅ Confidence: {value:.1%}")
                    elif key == "available":
                        status = "✅ Available" if value else "❌ Not Available"
                        print(f"   {status}")
                    else:
                        print(f"   {key}: {value}")
            else:
                print(f"   {msg.content}")
        
        # Metadata
        if msg.metadata:
            print(f"\n📊 Metadata:")
            for key, value in msg.metadata.items():
                print(f"   • {key}: {value}")
        
        print("─" * 70)
    
    def _get_agent_name(self, agent_id: str) -> str:
        """Get friendly agent name"""
        names = {
            "manager": "🎯 Team Manager",
            "eddie": "📝 Eddie (Technical Doc Specialist)",
            "jamik": "🏗️  Jamik (System Architect)",
            "sarah": "🎨 Sarah (UX Designer)",
            "mike": "⚙️  Mike (Backend Engineer)",
            "lisa": "🧪 Lisa (QA Lead)"
        }
        return names.get(agent_id, agent_id)
    
    def print_summary(self):
        """Print summary of all messages"""
        print("\n" + "=" * 70)
        print("📊 CHAT SUMMARY")
        print("=" * 70)
        print(f"Total messages exchanged: {self.message_count}")
        
        # Count by type
        by_type = {}
        for msg in self.messages:
            by_type[msg.message_type] = by_type.get(msg.message_type, 0) + 1
        
        print("\nMessages by type:")
        for msg_type, count in sorted(by_type.items()):
            print(f"   • {msg_type}: {count}")
        
        # Count by sender
        by_sender = {}
        for msg in self.messages:
            by_sender[msg.sender_id] = by_sender.get(msg.sender_id, 0) + 1
        
        print("\nMessages by sender:")
        for sender, count in sorted(by_sender.items(), key=lambda x: -x[1]):
            name = self._get_agent_name(sender)
            print(f"   • {name}: {count}")


class InterceptedProtocol(AgentCommunicationProtocol):
    """Communication protocol that logs all messages"""
    
    def __init__(self, shared_knowledge, chat_logger):
        super().__init__(shared_knowledge)
        self.chat_logger = chat_logger
    
    async def send_message(self, message: Message) -> bool:
        """Send message and log it"""
        # Log the message
        self.chat_logger.log_message(message)
        
        # Send normally
        return await super().send_message(message)


async def watch_task_distribution():
    """Watch a task being distributed with full chat logs"""
    
    print("🎬 Agent Chat Viewer - Watch Agents Communicate")
    print("=" * 70)
    print("This shows the FULL conversation between agents during task")
    print("distribution, including Phase 1 (individual consultation) and")
    print("Phase 2 (peer negotiation).")
    print("=" * 70)
    
    # Setup chat logger
    chat_logger = ChatLogger()
    
    # Initialize systems
    print("\n🔧 Initializing agent team...")
    
    shared_knowledge = SharedKnowledgeBase()
    await shared_knowledge.initialize()
    
    # Use intercepted protocol
    communication_protocol = InterceptedProtocol(shared_knowledge, chat_logger)
    await communication_protocol.initialize()
    
    # Create manager
    manager = ManagerAgent(
        shared_knowledge=shared_knowledge,
        worker_agent_ids=["eddie", "jamik", "sarah"]
    )
    await manager.initialize()
    await communication_protocol.register_agent("manager", manager.receive_message)
    
    # Create 3 diverse workers (less agents = clearer chat)
    workers_config = {
        "eddie": {
            "name": "Eddie Lake",
            "caps": AgentCapabilities(
                technical_skills={"technical": 0.9, "documentation": 0.95, "api": 0.85},
                preferred_task_types=["Technical content", "API Documentation"],
                work_style={"collaborative": True, "detail_oriented": True},
                communication_style={"formal": 0.6, "technical": 0.9}
            ),
            "workload": 2,
            "capacity": 5
        },
        "jamik": {
            "name": "Jamik Tashpulatov",
            "caps": AgentCapabilities(
                technical_skills={"architecture": 0.95, "backend": 0.9, "leadership": 0.85},
                preferred_task_types=["System Architecture", "Backend Development"],
                work_style={"strategic": True, "independent": True},
                communication_style={"formal": 0.8, "strategic": 0.9}
            ),
            "workload": 4,
            "capacity": 5
        },
        "sarah": {
            "name": "Sarah Johnson",
            "caps": AgentCapabilities(
                technical_skills={"design": 0.95, "creative": 0.9, "ux": 0.95},
                preferred_task_types=["Visual Design", "UI/UX"],
                work_style={"collaborative": True, "creative": True},
                communication_style={"casual": 0.8, "enthusiastic": 0.9}
            ),
            "workload": 1,
            "capacity": 5
        }
    }
    
    workers = {}
    for agent_id, config in workers_config.items():
        worker = WorkerAgent(
            agent_id=agent_id,
            person_name=config["name"],
            shared_knowledge=shared_knowledge,
            capabilities=config["caps"]
        )
        await worker.initialize()
        await communication_protocol.register_agent(agent_id, worker.receive_message)
        
        # Set initial context
        await shared_knowledge.update_agent_context(
            agent_id,
            AgentContext(
                agent_id=agent_id,
                current_workload=config["workload"],
                max_capacity=config["capacity"],
                availability_status=AgentStatus.AVAILABLE if config["workload"] < config["capacity"] else AgentStatus.BUSY
            )
        )
        
        workers[agent_id] = worker
        print(f"   ✅ {config['name']} ready ({config['workload']}/{config['capacity']} tasks)")
    
    print("\n" + "=" * 70)
    print("🚀 Team Ready! Starting task distribution...")
    print("=" * 70)
    
    # Create an interesting task
    task = TaskInfo(
        task_id="demo_task_001",
        title="Write API Integration Guide",
        description="Create comprehensive documentation for our new REST API, including code examples and best practices",
        task_type="Technical content",
        priority=8,
        estimated_hours=4.0,
        required_skills=["technical", "documentation", "api"],
        status=TaskStatus.PENDING
    )
    
    print(f"\n📋 Task to Distribute:")
    print(f"   Title: {task.title}")
    print(f"   Type: {task.task_type}")
    print(f"   Skills: {', '.join(task.required_skills)}")
    print(f"   Priority: {task.priority}/10")
    print(f"   Estimated: {task.estimated_hours} hours")
    
    # Add to shared knowledge
    await shared_knowledge.add_task(task)
    
    print("\n🎬 Watch the agents communicate...")
    print("=" * 70)
    
    # Distribute the task
    result = await manager.distribute_task(task)
    
    # Print chat summary
    chat_logger.print_summary()
    
    # Print final result
    print("\n" + "=" * 70)
    print("🎯 FINAL RESULT")
    print("=" * 70)
    
    if result.get("success"):
        assigned_to = result.get("assigned_agent")
        assigned_name = workers_config.get(assigned_to, {}).get("name", assigned_to)
        print(f"✅ Task assigned to: {assigned_name}")
        print(f"   Reasoning: {result.get('reasoning', 'N/A')}")
    else:
        print(f"❌ Assignment failed: {result.get('error', 'Unknown error')}")
    
    # Cleanup
    await communication_protocol.shutdown()
    await shared_knowledge.close()
    
    print("\n✨ Chat log complete!")


if __name__ == "__main__":
    asyncio.run(watch_task_distribution())

