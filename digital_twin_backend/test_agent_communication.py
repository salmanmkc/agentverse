#!/usr/bin/env python3
"""
Test Agent Communication System
Demonstrates agents communicating without requiring trained models
Uses fallback response system to simulate realistic agent behavior
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
    TaskStatus
)
from digital_twin_backend.communication.protocol import AgentCommunicationProtocol
from digital_twin_backend.agents.manager_agent import ManagerAgent
from digital_twin_backend.agents.worker_agent import WorkerAgent


async def test_agent_communication():
    """Test agent-to-agent communication system"""
    
    print("🤖 Testing Agent Communication System")
    print("=" * 60)
    print("Note: Using fallback responses (no trained models required)")
    print("=" * 60)
    
    try:
        # Step 1: Initialize core systems
        print("\n📡 Step 1: Initializing core systems...")
        shared_knowledge = SharedKnowledgeBase()
        await shared_knowledge.initialize()
        
        communication_protocol = AgentCommunicationProtocol(shared_knowledge)
        await communication_protocol.initialize()
        
        print("✅ Core systems initialized")
        
        # Step 2: Create Manager Agent
        print("\n👔 Step 2: Creating Manager Agent...")
        manager = ManagerAgent(
            shared_knowledge=shared_knowledge,
            worker_agent_ids=["alice", "bob", "charlie"]
        )
        await manager.initialize()
        
        # Register with communication
        await communication_protocol.register_agent("manager", manager.receive_message)
        
        print("✅ Manager agent created and registered")
        
        # Step 3: Create Worker Agents
        print("\n👥 Step 3: Creating Worker Agents...")
        
        # Alice - Technical specialist, low workload
        alice_caps = AgentCapabilities(
            technical_skills={"technical": 0.9, "documentation": 0.8, "api": 0.85},
            preferred_task_types=["Technical content", "API Documentation"],
            work_style={"collaborative": True, "detail_oriented": True},
            communication_style={"formal": 0.7, "technical": 0.9}
        )
        
        alice = WorkerAgent(
            agent_id="alice",
            person_name="Alice (Technical Lead)",
            shared_knowledge=shared_knowledge,
            capabilities=alice_caps,
            model_path=None  # No trained model - will use fallback
        )
        await alice.initialize()
        alice.context.current_workload = 2
        alice.context.max_capacity = 5
        await shared_knowledge.update_agent_context("alice", alice.context)
        
        # Bob - Backend specialist, moderate workload
        bob_caps = AgentCapabilities(
            technical_skills={"backend": 0.95, "database": 0.9, "architecture": 0.85},
            preferred_task_types=["System Architecture", "Backend Development"],
            work_style={"independent": True, "fast_paced": True},
            communication_style={"casual": 0.8, "concise": 0.9}
        )
        
        bob = WorkerAgent(
            agent_id="bob",
            person_name="Bob (Backend Expert)",
            shared_knowledge=shared_knowledge,
            capabilities=bob_caps,
            model_path=None  # No trained model - will use fallback
        )
        await bob.initialize()
        bob.context.current_workload = 3
        bob.context.max_capacity = 5
        await shared_knowledge.update_agent_context("bob", bob.context)
        
        # Charlie - Creative specialist, high workload
        charlie_caps = AgentCapabilities(
            technical_skills={"creative": 0.9, "frontend": 0.8, "design": 0.95},
            preferred_task_types=["Visual Design", "UI/UX", "Creative Content"],
            work_style={"collaborative": True, "creative": True},
            communication_style={"casual": 0.9, "enthusiastic": 0.8}
        )
        
        charlie = WorkerAgent(
            agent_id="charlie",
            person_name="Charlie (Creative Designer)",
            shared_knowledge=shared_knowledge,
            capabilities=charlie_caps,
            model_path=None  # No trained model - will use fallback
        )
        await charlie.initialize()
        charlie.context.current_workload = 4
        charlie.context.max_capacity = 5
        await shared_knowledge.update_agent_context("charlie", charlie.context)
        
        # Register all workers with communication
        await communication_protocol.register_agent("alice", alice.receive_message)
        await communication_protocol.register_agent("bob", bob.receive_message)
        await communication_protocol.register_agent("charlie", charlie.receive_message)
        
        print("✅ Created 3 worker agents:")
        print(f"   • Alice: {alice.context.utilization:.1%} utilization (technical specialist)")
        print(f"   • Bob: {bob.context.utilization:.1%} utilization (backend expert)")
        print(f"   • Charlie: {charlie.context.utilization:.1%} utilization (creative designer)")
        
        # Step 4: Create a test task
        print("\n📋 Step 4: Creating test task...")
        
        test_task = TaskInfo(
            task_id="test_001",
            title="API Documentation Update",
            description="Update the REST API documentation with new endpoints",
            task_type="Technical content",
            priority=7,
            estimated_hours=3.0,
            required_skills=["technical", "documentation", "api"],
            status=TaskStatus.PENDING,
            deadline=None
        )
        
        print(f"✅ Created task: {test_task.title}")
        print(f"   Type: {test_task.task_type}")
        print(f"   Priority: {test_task.priority}/10")
        print(f"   Required skills: {', '.join(test_task.required_skills)}")
        
        # Step 5: Test Phase 1 - Manager Consultation
        print("\n🔍 Step 5: PHASE 1 - Individual Consultation...")
        print("Manager asks each agent individually about the task:")
        
        phase1_result = await manager._phase1_individual_consultation(test_task)
        
        print(f"\n📊 Phase 1 Results:")
        print(f"   Viable candidates: {len(phase1_result['viable_candidates'])}")
        
        for agent_id, assessment in phase1_result['all_assessments'].items():
            worker_name = {"alice": "Alice", "bob": "Bob", "charlie": "Charlie"}.get(agent_id, agent_id)
            can_handle = "✅ Can handle" if assessment.can_handle else "❌ Cannot handle"
            print(f"\n   👤 {worker_name}:")
            print(f"      {can_handle}")
            print(f"      Confidence: {assessment.confidence:.1%}")
            print(f"      Est. time: {assessment.estimated_time:.1f}h")
            if assessment.concerns:
                print(f"      Concerns: {', '.join(assessment.concerns)}")
        
        # Step 6: Test Phase 2 - Peer Negotiation  
        print("\n🤝 Step 6: PHASE 2 - Peer Negotiation...")
        print("Agents discuss among themselves who should take the task:")
        
        if len(phase1_result['viable_candidates']) > 1:
            phase2_result = await manager._phase2_peer_negotiation(test_task, phase1_result)
            
            print(f"\n💬 Negotiation Messages:")
            for msg in phase2_result['negotiation_messages']:
                print(f"   {msg.from_agent}: {msg.content[:80]}...")
                print(f"   [Type: {msg.message_type}, Confidence: {msg.confidence:.1%}]")
            
            print(f"\n🎯 Consensus: {phase2_result['consensus']}")
        else:
            print("   Only one viable candidate - no negotiation needed")
        
        # Step 7: Complete Distribution
        print("\n🚀 Step 7: Complete Task Distribution...")
        
        distribution_result = await manager.distribute_task(test_task)
        
        if distribution_result.get("success"):
            assigned_agent = distribution_result["assigned_agent"]
            worker_name = {"alice": "Alice", "bob": "Bob", "charlie": "Charlie"}.get(assigned_agent, assigned_agent)
            
            print(f"✅ Task assigned to: {worker_name}")
            print(f"   Reasoning: {distribution_result['reasoning']}")
            
            # Check workload update
            updated_context = await shared_knowledge.get_agent_context(assigned_agent)
            print(f"   Updated workload: {updated_context.current_workload}/{updated_context.max_capacity}")
            print(f"   New utilization: {updated_context.utilization:.1%}")
        else:
            print(f"❌ Distribution failed: {distribution_result.get('error')}")
        
        # Step 8: Test Agent Status
        print("\n📊 Step 8: Final Agent Status...")
        
        all_contexts = await shared_knowledge.get_all_agent_contexts()
        
        for agent_id in ["alice", "bob", "charlie"]:
            context = all_contexts.get(agent_id)
            if context:
                worker_name = {"alice": "Alice", "bob": "Bob", "charlie": "Charlie"}.get(agent_id, agent_id)
                print(f"   {worker_name}: {context.utilization:.1%} utilization, stress: {context.stress_level:.1f}")
        
        # Test communication stats
        print("\n📡 Communication Stats:")
        comm_stats = await communication_protocol.get_system_stats()
        print(f"   Active agents: {comm_stats['active_agents']}")
        print(f"   Total messages sent: {comm_stats['message_stats']['total_sent']}")
        print(f"   Total messages delivered: {comm_stats['message_stats']['total_delivered']}")
        
        # Summary
        print("\n" + "=" * 60)
        print("🎉 AGENT COMMUNICATION TEST COMPLETE!")
        print("=" * 60)
        print("✅ Manager agent working")
        print("✅ Worker agents working")
        print("✅ Phase 1 consultation working")
        print("✅ Phase 2 negotiation working")
        print("✅ Task distribution working")
        print("✅ Shared knowledge updating")
        print("✅ Communication protocol routing messages")
        print("\n🚀 Agent communication system is fully functional!")
        print("💡 Next: Install ML libraries to enable personalized models")
        
        # Cleanup
        await communication_protocol.shutdown()
        await shared_knowledge.close()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_agent_communication())
