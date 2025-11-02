#!/usr/bin/env python3
"""
Show Agent Thinking - Verbose Agent Negotiation Viewer
Shows what agents are "thinking" during task distribution
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
from digital_twin_backend.communication.protocol import AgentCommunicationProtocol
from digital_twin_backend.agents.manager_agent import ManagerAgent
from digital_twin_backend.agents.worker_agent import WorkerAgent


# Monkey-patch to show verbose output
original_consult = ManagerAgent._consult_individual_agent

async def verbose_consult(self, agent_id: str, task: TaskInfo):
    """Verbose version showing the conversation"""
    
    print(f"\n{'='*70}")
    print(f"📞 MANAGER → {agent_id.upper()}: CONSULTATION REQUEST")
    print(f"{'='*70}")
    
    context = await self.shared_knowledge.get_agent_context(agent_id)
    capabilities = await self.shared_knowledge.get_agent_capabilities(agent_id)
    
    agent_caps = capabilities.get(agent_id) if capabilities else None
    
    print(f"\n💬 Manager says:")
    print(f"   \"Hi {agent_id}, I need your assessment on this task:\"")
    print(f"   ")
    print(f"   📋 Task: {task.title}")
    print(f"   📝 Description: {task.description}")
    print(f"   🏷️  Type: {task.task_type}")
    print(f"   ⚡ Priority: {task.priority}/10")
    print(f"   ⏱️  Estimated: {task.estimated_hours} hours")
    print(f"   🎯 Required skills: {', '.join(task.required_skills)}")
    print(f"   ")
    print(f"   \"Can you handle this? What's your confidence level?\"")
    
    # Get the actual assessment
    assessment = await self._simulate_agent_assessment(agent_id, task)
    
    print(f"\n💭 {agent_id.upper()} is thinking...")
    if agent_caps:
        print(f"   My skills: {agent_caps.technical_skills}")
        print(f"   My preferred types: {agent_caps.preferred_task_types}")
    if context:
        print(f"   My workload: {context.current_workload}/{context.max_capacity} tasks ({context.utilization:.0%})")
        print(f"   My stress level: {context.stress_level:.0%}")
    
    print(f"\n💬 {agent_id.upper()} responds:")
    
    if assessment.can_handle:
        enthusiasm = "!" if assessment.confidence > 0.8 else "." if assessment.confidence > 0.5 else "..."
        print(f"   \"I can handle this{enthusiasm}\"")
        print(f"   ")
        print(f"   ✅ Confidence: {assessment.confidence:.0%}")
        print(f"   ⏱️  My estimate: {assessment.estimated_time:.1f} hours")
        
        if assessment.confidence > 0.8:
            print(f"   🌟 \"This is exactly my specialty!\"")
        elif assessment.confidence > 0.6:
            print(f"   👍 \"This fits my skillset well.\"")
        else:
            print(f"   🤔 \"I could do it, but it's not my strongest area.\"")
        
        if assessment.concerns:
            print(f"   ")
            print(f"   ⚠️  Concerns:")
            for concern in assessment.concerns:
                print(f"      • {concern}")
    else:
        print(f"   \"I'm afraid I can't take this on right now.\"")
        print(f"   ")
        print(f"   ❌ Cannot handle")
        if assessment.concerns:
            print(f"   Reasons:")
            for concern in assessment.concerns:
                print(f"      • {concern}")
    
    print(f"\n{'─'*70}\n")
    
    return assessment

ManagerAgent._consult_individual_agent = verbose_consult


# Monkey-patch phase 2 to show negotiation
original_phase2 = ManagerAgent._phase2_peer_negotiation

async def verbose_phase2(self, task: TaskInfo, phase1_result: dict):
    """Verbose version showing peer negotiation"""
    
    viable = phase1_result["viable_candidates"]
    
    if len(viable) == 0:
        print(f"\n{'='*70}")
        print("😟 PHASE 2: PEER NEGOTIATION")
        print(f"{'='*70}")
        print("\n❌ No viable candidates from Phase 1")
        print("   Manager: \"Nobody is available or qualified for this task.\"")
        return {
            "consensus": None,
            "reasoning": "No viable candidates",
            "negotiation_messages": []
        }
    
    if len(viable) == 1:
        agent_id, assessment = viable[0]
        print(f"\n{'='*70}")
        print("🎯 PHASE 2: PEER NEGOTIATION")
        print(f"{'='*70}")
        print(f"\n✅ Only one viable candidate: {agent_id}")
        print(f"   Manager: \"{agent_id.capitalize()} is the clear choice here.\"")
        print(f"   Confidence: {assessment.confidence:.0%}")
        return {
            "consensus": agent_id,
            "reasoning": f"Only one viable candidate with {assessment.confidence:.0%} confidence",
            "negotiation_messages": [f"Clear choice: {agent_id}"]
        }
    
    print(f"\n{'='*70}")
    print(f"🤝 PHASE 2: PEER NEGOTIATION ({len(viable)} candidates)")
    print(f"{'='*70}")
    
    print(f"\n💬 Manager says:")
    print(f"   \"We have {len(viable)} agents who can handle this task.\"")
    print(f"   \"Let's discuss who's the best fit...\"")
    print()
    
    for i, (agent_id, assessment) in enumerate(viable, 1):
        context = await self.shared_knowledge.get_agent_context(agent_id)
        print(f"   {i}. {agent_id.capitalize()}:")
        print(f"      • Confidence: {assessment.confidence:.0%}")
        print(f"      • Workload: {context.current_workload if context else '?'}/{context.max_capacity if context else '?'}")
        print(f"      • Utilization: {context.utilization:.0%}" if context else "")
    
    print(f"\n💭 Agents discuss among themselves...")
    print()
    
    # Show the top 2-3 discussing
    for i in range(min(3, len(viable))):
        agent_id, assessment = viable[i]
        context = await self.shared_knowledge.get_agent_context(agent_id)
        
        if i == 0:  # Highest confidence
            if assessment.confidence > 0.8:
                print(f"   💬 {agent_id.upper()}: \"I'd love to take this! It's right in my wheelhouse.\"")
            else:
                print(f"   💬 {agent_id.upper()}: \"I think I'm a good fit for this.\"")
        elif i == 1:  # Second place
            if viable[0][1].confidence - assessment.confidence > 0.2:
                print(f"   💬 {agent_id.upper()}: \"{viable[0][0].capitalize()} is more specialized in this area.\"")
            else:
                print(f"   💬 {agent_id.upper()}: \"I could also handle it if needed.\"")
        elif i == 2:  # Third
            if context and context.utilization > 0.7:
                print(f"   💬 {agent_id.upper()}: \"I'm pretty loaded right now, let others take it.\"")
            else:
                print(f"   💬 {agent_id.upper()}: \"I'm available if you need me.\"")
    
    # Winner
    winner_id, winner_assessment = viable[0]
    
    print()
    print(f"{'─'*70}")
    print(f"🏆 CONSENSUS REACHED")
    print(f"{'─'*70}")
    print(f"\n   💬 Team agrees: \"{winner_id.capitalize()} should take this task.\"")
    print(f"   ")
    print(f"   ✅ {winner_id.upper()} accepts")
    print(f"   💬 {winner_id.upper()}: \"Got it! I'll handle this.\"")
    print()
    
    return {
        "consensus": winner_id,
        "reasoning": f"Best match with {winner_assessment.confidence:.0%} confidence",
        "negotiation_messages": [f"Team consensus: {winner_id}"]
    }

ManagerAgent._phase2_peer_negotiation = verbose_phase2


async def show_agent_distribution():
    """Run task distribution with full agent conversation"""
    
    print("🎬 Agent Communication Viewer")
    print("="*70)
    print("Watch agents communicate and negotiate task assignments")
    print("="*70)
    
    # Setup
    print("\n🔧 Initializing team...")
    
    shared_knowledge = SharedKnowledgeBase()
    await shared_knowledge.initialize()
    
    protocol = AgentCommunicationProtocol(shared_knowledge)
    await protocol.initialize()
    
    # Create manager
    manager = ManagerAgent(
        shared_knowledge=shared_knowledge,
        worker_agent_ids=["eddie", "jamik", "sarah"]
    )
    await manager.initialize()
    
    # Create workers
    workers_config = {
        "eddie": {
            "name": "Eddie Lake",
            "caps": AgentCapabilities(
                technical_skills={"technical": 0.9, "documentation": 0.95, "api": 0.85, "code_review": 0.7},
                preferred_task_types=["Technical content", "API Documentation"],
                work_style={},
                communication_style={}
            ),
            "workload": 2,
            "stress": 0.4
        },
        "jamik": {
            "name": "Jamik Tashpulatov",
            "caps": AgentCapabilities(
                technical_skills={"architecture": 0.95, "backend": 0.9, "technical": 0.85, "documentation": 0.6},
                preferred_task_types=["System Architecture", "Backend Development"],
                work_style={},
                communication_style={}
            ),
            "workload": 4,
            "stress": 0.8
        },
        "sarah": {
            "name": "Sarah Johnson",
            "caps": AgentCapabilities(
                technical_skills={"design": 0.95, "creative": 0.9, "ux": 0.95, "technical": 0.4},
                preferred_task_types=["Visual Design", "UI/UX"],
                work_style={},
                communication_style={}
            ),
            "workload": 1,
            "stress": 0.2
        }
    }
    
    for agent_id, config in workers_config.items():
        worker = WorkerAgent(
            agent_id=agent_id,
            person_name=config["name"],
            shared_knowledge=shared_knowledge,
            capabilities=config["caps"]
        )
        await worker.initialize()
        
        await shared_knowledge.update_agent_context(
            agent_id,
            AgentContext(
                agent_id=agent_id,
                current_workload=config["workload"],
                max_capacity=5,
                stress_level=config["stress"],
                availability_status=AgentStatus.AVAILABLE
            )
        )
    
    print("✅ Team ready!\n")
    
    # Create task
    task = TaskInfo(
        task_id="demo_001",
        title="Write API Integration Guide",
        description="Create comprehensive documentation for our new REST API with code examples, authentication flow, and best practices",
        task_type="Technical content",
        priority=8,
        estimated_hours=4.0,
        required_skills=["technical", "documentation", "api"],
        status=TaskStatus.PENDING
    )
    
    print("="*70)
    print("📋 NEW TASK ARRIVES")
    print("="*70)
    print(f"\n   Title: {task.title}")
    print(f"   Type: {task.task_type}")
    print(f"   Priority: {task.priority}/10")
    print(f"   Estimated: {task.estimated_hours} hours")
    print(f"   Skills needed: {', '.join(task.required_skills)}")
    
    print(f"\n\n{'='*70}")
    print("🎯 MANAGER STARTS DISTRIBUTION PROCESS")
    print(f"{'='*70}")
    print(f"\n💭 Manager thinks:")
    print(f"   \"I need to find the best person for this API documentation task.\"")
    print(f"   \"Let me consult with the team individually first...\"")
    
    print(f"\n\n{'='*70}")
    print("📞 PHASE 1: INDIVIDUAL CONSULTATIONS")
    print(f"{'='*70}")
    
    # Distribute
    await shared_knowledge.add_task(task)
    result = await manager.distribute_task(task)
    
    # Final result
    print("\n" + "="*70)
    print("✅ FINAL ASSIGNMENT")
    print("="*70)
    
    if result.get("success"):
        assigned = result["assigned_agent"]
        context = await shared_knowledge.get_agent_context(assigned)
        print(f"\n   📌 Task assigned to: {assigned.upper()}")
        print(f"   ")
        print(f"   💬 Manager announces:")
        print(f"      \"{assigned.capitalize()} will handle '{task.title}'\"")
        if context:
            print(f"   ")
            print(f"   📊 {assigned.capitalize()}'s new workload: {context.current_workload}/{context.max_capacity} ({context.utilization:.0%})")
    else:
        print(f"\n   ❌ Failed to assign task")
        print(f"   Error: {result.get('error')}")
    
    await protocol.shutdown()
    await shared_knowledge.close()
    
    print("\n✨ Distribution complete!\n")


if __name__ == "__main__":
    asyncio.run(show_agent_distribution())

