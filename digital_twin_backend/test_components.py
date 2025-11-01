#!/usr/bin/env python3
"""
Individual Component Testing Suite
Test each major component of the digital twin system independently
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

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
from digital_twin_backend.communication.protocol import (
    AgentCommunicationProtocol,
    MessageType,
    MessagePriority
)


class ComponentTester:
    """Test individual components"""
    
    def __init__(self):
        self.test_results = {}
    
    async def test_shared_knowledge_alone(self):
        """Test 1: Shared Knowledge System"""
        print("\n🧠 TEST 1: Shared Knowledge System")
        print("-" * 50)
        
        try:
            # Initialize
            shared_knowledge = SharedKnowledgeBase()
            await shared_knowledge.initialize()
            print("✅ Initialized successfully")
            
            # Test agent registration
            test_caps = AgentCapabilities(
                technical_skills={"python": 0.9, "testing": 0.8},
                preferred_task_types=["Testing", "Development"],
                work_style={"collaborative": True},
                communication_style={"formal": 0.5}
            )
            
            await shared_knowledge.register_agent("test_agent", test_caps)
            print("✅ Registered agent successfully")
            
            # Test agent capabilities retrieval
            caps = await shared_knowledge.get_agent_capabilities("test_agent")
            assert "test_agent" in caps
            print("✅ Retrieved agent capabilities")
            
            # Test task creation
            task = TaskInfo(
                task_id="task_001",
                title="Test Task",
                description="Testing the system",
                task_type="Testing",
                priority=5,
                estimated_hours=2.0,
                required_skills=["testing"]
            )
            
            await shared_knowledge.add_task(task)
            print("✅ Created task successfully")
            
            # Test task retrieval
            retrieved = await shared_knowledge.get_task("task_001")
            assert retrieved.title == "Test Task"
            print("✅ Retrieved task successfully")
            
            # Test task assignment
            await shared_knowledge.assign_task("task_001", "test_agent", "Test assignment")
            print("✅ Assigned task successfully")
            
            # Test agent context
            context = await shared_knowledge.get_agent_context("test_agent")
            assert context.current_workload == 1
            print(f"✅ Agent workload updated: {context.current_workload} tasks")
            
            # Cleanup
            await shared_knowledge.close()
            
            self.test_results["shared_knowledge"] = "✅ PASSED"
            print("🎉 Shared Knowledge System: WORKING")
            
        except Exception as e:
            self.test_results["shared_knowledge"] = f"❌ FAILED: {e}"
            print(f"❌ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_communication_protocol_alone(self):
        """Test 2: Communication Protocol"""
        print("\n📡 TEST 2: Communication Protocol")
        print("-" * 50)
        
        try:
            # Initialize
            shared_knowledge = SharedKnowledgeBase()
            await shared_knowledge.initialize()
            
            protocol = AgentCommunicationProtocol(shared_knowledge)
            await protocol.initialize()
            print("✅ Protocol initialized successfully")
            
            # Test agent registration
            received_messages = []
            
            async def test_handler(message):
                received_messages.append(message)
                print(f"   📨 Received: {message.get('content', '')[:50]}")
            
            await protocol.register_agent("agent_1", test_handler)
            await protocol.register_agent("agent_2", test_handler)
            print("✅ Registered 2 agents")
            
            # Test message sending
            success = await protocol.send_message(
                from_agent="agent_1",
                to_agent="agent_2",
                message_type=MessageType.GENERAL,
                content="Hello from agent_1!",
                metadata={"test": True}
            )
            
            assert success
            print("✅ Message sent successfully")
            
            # Wait for message processing
            await asyncio.sleep(0.5)
            
            # Test broadcast
            results = await protocol.broadcast_message(
                from_agent="manager",
                recipient_agents=["agent_1", "agent_2"],
                message_type=MessageType.SYSTEM,
                content="Broadcast message to all agents"
            )
            
            print(f"✅ Broadcast sent to {len(results)} agents")
            
            # Test communication stats
            stats = await protocol.get_system_stats()
            print(f"✅ Active agents: {stats['active_agents']}")
            print(f"✅ Messages sent: {stats['message_stats']['total_sent']}")
            
            # Cleanup
            await protocol.shutdown()
            await shared_knowledge.close()
            
            self.test_results["communication"] = "✅ PASSED"
            print("🎉 Communication Protocol: WORKING")
            
        except Exception as e:
            self.test_results["communication"] = f"❌ FAILED: {e}"
            print(f"❌ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_agent_capabilities_matching(self):
        """Test 3: Agent Capability Matching"""
        print("\n🎯 TEST 3: Agent Capability Matching")
        print("-" * 50)
        
        try:
            # Initialize
            shared_knowledge = SharedKnowledgeBase()
            await shared_knowledge.initialize()
            
            # Create agents with different capabilities
            agents_config = {
                "technical_alice": AgentCapabilities(
                    technical_skills={"technical": 0.9, "api": 0.8, "documentation": 0.85},
                    preferred_task_types=["Technical content", "API Documentation"],
                    work_style={"detail_oriented": True},
                    communication_style={"formal": 0.7}
                ),
                "creative_bob": AgentCapabilities(
                    technical_skills={"creative": 0.9, "design": 0.95, "visual": 0.8},
                    preferred_task_types=["Visual Design", "Creative Content"],
                    work_style={"creative": True},
                    communication_style={"casual": 0.8}
                ),
                "backend_charlie": AgentCapabilities(
                    technical_skills={"backend": 0.95, "database": 0.9, "infrastructure": 0.85},
                    preferred_task_types=["Backend Development", "System Architecture"],
                    work_style={"independent": True},
                    communication_style={"technical": 0.9}
                )
            }
            
            # Register all agents
            for agent_id, caps in agents_config.items():
                await shared_knowledge.register_agent(agent_id, caps)
                context = AgentContext(agent_id=agent_id, current_workload=2, max_capacity=5)
                await shared_knowledge.update_agent_context(agent_id, context)
            
            print(f"✅ Registered {len(agents_config)} agents with different capabilities")
            
            # Test technical task matching
            tech_task = TaskInfo(
                task_id="tech_001",
                title="API Documentation",
                description="Write API docs",
                task_type="Technical content",
                priority=7,
                estimated_hours=3.0,
                required_skills=["technical", "api", "documentation"]
            )
            
            await shared_knowledge.add_task(tech_task)
            
            # Get best candidates
            candidates = await shared_knowledge.get_best_candidates(tech_task, top_k=3)
            
            print(f"\n📋 Task: {tech_task.title} (requires: {', '.join(tech_task.required_skills)})")
            print("   Best matches:")
            for agent_id, score in candidates:
                print(f"      {agent_id}: {score:.1%} match")
            
            # Verify technical_alice scored highest
            assert candidates[0][0] == "technical_alice", f"Expected technical_alice, got {candidates[0][0]}"
            print(f"✅ Correct agent matched: {candidates[0][0]} ({candidates[0][1]:.1%})")
            
            # Test creative task matching
            creative_task = TaskInfo(
                task_id="creative_001",
                title="UI Design Mockup",
                description="Create UI designs",
                task_type="Visual Design",
                priority=6,
                estimated_hours=4.0,
                required_skills=["creative", "design", "visual"]
            )
            
            await shared_knowledge.add_task(creative_task)
            candidates = await shared_knowledge.get_best_candidates(creative_task, top_k=3)
            
            print(f"\n📋 Task: {creative_task.title} (requires: {', '.join(creative_task.required_skills)})")
            print("   Best matches:")
            for agent_id, score in candidates:
                print(f"      {agent_id}: {score:.1%} match")
            
            # Verify creative_bob scored highest
            assert candidates[0][0] == "creative_bob", f"Expected creative_bob, got {candidates[0][0]}"
            print(f"✅ Correct agent matched: {candidates[0][0]} ({candidates[0][1]:.1%})")
            
            # Cleanup
            await shared_knowledge.close()
            
            self.test_results["capability_matching"] = "✅ PASSED"
            print("\n🎉 Agent Capability Matching: WORKING")
            
        except Exception as e:
            self.test_results["capability_matching"] = f"❌ FAILED: {e}"
            print(f"❌ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_workload_tracking(self):
        """Test 4: Workload and Stress Tracking"""
        print("\n📊 TEST 4: Workload and Stress Tracking")
        print("-" * 50)
        
        try:
            # Initialize
            shared_knowledge = SharedKnowledgeBase()
            await shared_knowledge.initialize()
            
            # Create test agent
            caps = AgentCapabilities(
                technical_skills={"technical": 0.8},
                preferred_task_types=["General"],
                work_style={},
                communication_style={}
            )
            
            await shared_knowledge.register_agent("test_agent", caps)
            
            # Create context with specific workload
            context = AgentContext(
                agent_id="test_agent",
                current_workload=4,
                max_capacity=5,
                availability_status=AgentStatus.BUSY
            )
            
            await shared_knowledge.update_agent_context("test_agent", context)
            
            # Retrieve and check
            retrieved_context = await shared_knowledge.get_agent_context("test_agent")
            
            print(f"✅ Agent workload: {retrieved_context.current_workload}/{retrieved_context.max_capacity}")
            print(f"✅ Utilization: {retrieved_context.utilization:.1%}")
            print(f"✅ Stress level: {retrieved_context.stress_level:.1f}")
            print(f"✅ Status: {retrieved_context.availability_status.value}")
            
            assert retrieved_context.utilization == 0.8  # 4/5
            assert retrieved_context.availability_status == AgentStatus.BUSY
            
            # Add a task
            task = TaskInfo(
                task_id="workload_test",
                title="Test Task",
                description="Test",
                task_type="General",
                priority=5,
                estimated_hours=2.0
            )
            
            await shared_knowledge.add_task(task)
            await shared_knowledge.assign_task("workload_test", "test_agent", "Testing")
            
            # Check updated workload
            updated_context = await shared_knowledge.get_agent_context("test_agent")
            print(f"✅ After task assignment: {updated_context.current_workload}/{updated_context.max_capacity}")
            assert updated_context.current_workload == 5  # Increased by 1
            
            # Cleanup
            await shared_knowledge.close()
            
            self.test_results["workload_tracking"] = "✅ PASSED"
            print("🎉 Workload Tracking: WORKING")
            
        except Exception as e:
            self.test_results["workload_tracking"] = f"❌ FAILED: {e}"
            print(f"❌ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def run_all_component_tests(self):
        """Run all component tests"""
        print("🧪 Digital Twin Backend - Component Testing Suite")
        print("=" * 60)
        
        # Run tests
        await self.test_shared_knowledge_alone()
        await self.test_communication_protocol_alone()
        await self.test_agent_capabilities_matching()
        await self.test_workload_tracking()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 COMPONENT TEST SUMMARY")
        print("=" * 60)
        
        passed = len([r for r in self.test_results.values() if "✅" in r])
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            print(f"{result} {test_name.replace('_', ' ').title()}")
        
        print(f"\n🎯 RESULT: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL COMPONENTS WORKING CORRECTLY!")
            print("\n🚀 Ready for next steps:")
            print("   1. Test full agent communication: python test_agent_communication.py")
            print("   2. Install ML dependencies: source venv/bin/activate && pip install torch transformers")
            print("   3. Test training pipeline: python train_pipeline.py status")
        else:
            print("⚠️  Some components need attention")


async def main():
    """Main test runner"""
    tester = ComponentTester()
    await tester.run_all_component_tests()


if __name__ == "__main__":
    asyncio.run(main())
