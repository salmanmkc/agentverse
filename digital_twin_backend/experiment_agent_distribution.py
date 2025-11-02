#!/usr/bin/env python3
"""
Interactive Agent Distribution Experiment
Try different task prompts and see how agents negotiate and assign tasks
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


class AgentExperiment:
    """Interactive agent distribution experiments"""
    
    def __init__(self):
        self.shared_knowledge = None
        self.communication_protocol = None
        self.manager = None
        self.workers = {}
        self.task_counter = 0
        self.experiment_results = []
    
    async def setup_agents(self):
        """Setup the agent team"""
        
        print("🔧 Setting up agent team...")
        print("-" * 60)
        
        # Initialize core systems
        self.shared_knowledge = SharedKnowledgeBase()
        await self.shared_knowledge.initialize()
        
        self.communication_protocol = AgentCommunicationProtocol(self.shared_knowledge)
        await self.communication_protocol.initialize()
        
        # Create manager
        self.manager = ManagerAgent(
            shared_knowledge=self.shared_knowledge,
            worker_agent_ids=["eddie", "jamik", "sarah", "mike", "lisa"]
        )
        await self.manager.initialize()
        await self.communication_protocol.register_agent("manager", self.manager.receive_message)
        
        # Create diverse worker agents
        agents_config = {
            "eddie": {
                "name": "Eddie Lake (Technical Doc Specialist)",
                "caps": AgentCapabilities(
                    technical_skills={"technical": 0.9, "documentation": 0.95, "api": 0.85, "code_review": 0.8},
                    preferred_task_types=["Technical content", "API Documentation", "Code Review"],
                    work_style={"collaborative": True, "detail_oriented": True, "methodical": True},
                    communication_style={"formal": 0.6, "technical": 0.9, "helpful": 0.9}
                ),
                "workload": 2,
                "capacity": 5
            },
            "jamik": {
                "name": "Jamik Tashpulatov (System Architect)",
                "caps": AgentCapabilities(
                    technical_skills={"architecture": 0.95, "backend": 0.9, "leadership": 0.85, "technical": 0.9},
                    preferred_task_types=["System Architecture", "Backend Development", "Technical Strategy"],
                    work_style={"strategic": True, "independent": True, "big_picture": True},
                    communication_style={"formal": 0.8, "strategic": 0.9, "direct": 0.8}
                ),
                "workload": 3,
                "capacity": 5
            },
            "sarah": {
                "name": "Sarah Johnson (UX Designer)",
                "caps": AgentCapabilities(
                    technical_skills={"design": 0.95, "creative": 0.9, "frontend": 0.8, "ux": 0.95},
                    preferred_task_types=["Visual Design", "UI/UX", "Creative Content"],
                    work_style={"collaborative": True, "creative": True, "user_focused": True},
                    communication_style={"casual": 0.8, "enthusiastic": 0.9, "empathetic": 0.9}
                ),
                "workload": 4,
                "capacity": 5
            },
            "mike": {
                "name": "Mike Chen (Backend Engineer)",
                "caps": AgentCapabilities(
                    technical_skills={"backend": 0.95, "database": 0.9, "api": 0.85, "performance": 0.9},
                    preferred_task_types=["Backend Development", "Database Design", "API Development"],
                    work_style={"independent": True, "fast_paced": True, "pragmatic": True},
                    communication_style={"casual": 0.7, "concise": 0.9, "practical": 0.9}
                ),
                "workload": 1,
                "capacity": 5
            },
            "lisa": {
                "name": "Lisa Wong (QA Lead)",
                "caps": AgentCapabilities(
                    technical_skills={"qa": 0.95, "testing": 0.9, "automation": 0.85, "quality": 0.95},
                    preferred_task_types=["Quality Assurance", "Testing", "Bug Analysis"],
                    work_style={"methodical": True, "detail_oriented": True, "thorough": True},
                    communication_style={"formal": 0.7, "precise": 0.9, "systematic": 0.9}
                ),
                "workload": 2,
                "capacity": 5
            }
        }
        
        # Create worker agents
        for agent_id, config in agents_config.items():
            worker = WorkerAgent(
                agent_id=agent_id,
                person_name=config["name"],
                shared_knowledge=self.shared_knowledge,
                capabilities=config["caps"],
                model_path=None  # Using fallback responses for now
            )
            
            await worker.initialize()
            
            # Set workload
            worker.context.current_workload = config["workload"]
            worker.context.max_capacity = config["capacity"]
            await self.shared_knowledge.update_agent_context(agent_id, worker.context)
            
            self.workers[agent_id] = worker
            await self.communication_protocol.register_agent(agent_id, worker.receive_message)
        
        print("✅ Team setup complete!")
        print(f"   • Manager: {self.manager.person_name}")
        for agent_id, worker in self.workers.items():
            utilization = worker.context.utilization
            print(f"   • {worker.person_name}: {utilization:.0%} capacity ({worker.context.current_workload}/{worker.context.max_capacity})")
    
    async def run_experiment(self, task_title: str, task_type: str, priority: int, hours: float, skills: list = None):
        """Run a task distribution experiment"""
        
        self.task_counter += 1
        
        print("\n" + "=" * 60)
        print(f"🧪 EXPERIMENT #{self.task_counter}")
        print("=" * 60)
        
        # Create task
        task = TaskInfo(
            task_id=f"exp_{self.task_counter}",
            title=task_title,
            description=f"Experiment task: {task_title}",
            task_type=task_type,
            priority=priority,
            estimated_hours=hours,
            required_skills=skills or [],
            status=TaskStatus.PENDING
        )
        
        print(f"\n📋 Task Created:")
        print(f"   Title: {task.title}")
        print(f"   Type: {task.task_type}")
        print(f"   Priority: {task.priority}/10")
        print(f"   Estimated Hours: {task.estimated_hours}")
        print(f"   Required Skills: {', '.join(task.required_skills) if task.required_skills else 'General'}")
        
        # Distribute task
        print(f"\n🎯 Starting Distribution Process...")
        result = await self.manager.distribute_task(task)
        
        # Show results
        if result.get("success"):
            assigned_to = result["assigned_agent"]
            assigned_worker = self.workers.get(assigned_to)
            
            print(f"\n✅ TASK ASSIGNED TO: {assigned_worker.person_name if assigned_worker else assigned_to}")
            print(f"   Reasoning: {result['reasoning']}")
            
            # Show updated workload
            updated_context = await self.shared_knowledge.get_agent_context(assigned_to)
            print(f"   New workload: {updated_context.current_workload}/{updated_context.max_capacity}")
            print(f"   New utilization: {updated_context.utilization:.0%}")
            
            # Store result
            self.experiment_results.append({
                "task": task.title,
                "type": task.task_type,
                "priority": task.priority,
                "assigned_to": assigned_worker.person_name if assigned_worker else assigned_to,
                "reasoning": result["reasoning"]
            })
        else:
            print(f"\n❌ ASSIGNMENT FAILED")
            print(f"   Error: {result.get('error')}")
    
    async def show_team_status(self):
        """Show current team workload status"""
        
        print("\n📊 Current Team Status:")
        print("-" * 60)
        
        contexts = await self.shared_knowledge.get_all_agent_contexts()
        
        for agent_id, worker in self.workers.items():
            context = contexts.get(agent_id)
            if context:
                bar_length = 20
                filled = int(context.utilization * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                print(f"{worker.person_name:35s} [{bar}] {context.utilization:.0%}")
                print(f"{'':35s} {context.current_workload}/{context.max_capacity} tasks, stress: {context.stress_level:.1f}")
    
    async def show_experiment_summary(self):
        """Show summary of all experiments"""
        
        print("\n" + "=" * 60)
        print("📈 EXPERIMENT SUMMARY")
        print("=" * 60)
        
        if not self.experiment_results:
            print("No experiments run yet")
            return
        
        # Count assignments per agent
        agent_assignments = {}
        for result in self.experiment_results:
            agent = result["assigned_to"]
            agent_assignments[agent] = agent_assignments.get(agent, 0) + 1
        
        print(f"\n✅ Total Tasks Distributed: {len(self.experiment_results)}")
        print("\n👥 Tasks per Agent:")
        for agent, count in sorted(agent_assignments.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {agent}: {count} task(s)")
        
        print("\n📋 Task Distribution Log:")
        for i, result in enumerate(self.experiment_results, 1):
            print(f"\n   {i}. {result['task']} ({result['type']})")
            print(f"      → Assigned to: {result['assigned_to']}")
            print(f"      → Reason: {result['reasoning'][:60]}...")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.communication_protocol:
            await self.communication_protocol.shutdown()
        if self.shared_knowledge:
            await self.shared_knowledge.close()


async def run_predefined_experiments():
    """Run a series of predefined experiments"""
    
    experiment = AgentExperiment()
    
    try:
        await experiment.setup_agents()
        
        # Experiment 1: Technical Documentation
        await experiment.run_experiment(
            task_title="Update REST API Documentation",
            task_type="Technical content",
            priority=8,
            hours=3.0,
            skills=["technical", "documentation", "api"]
        )
        
        await experiment.show_team_status()
        await asyncio.sleep(1)
        
        # Experiment 2: UI Design
        await experiment.run_experiment(
            task_title="Design User Dashboard Mockups",
            task_type="Visual Design",
            priority=7,
            hours=4.0,
            skills=["design", "creative", "ux"]
        )
        
        await experiment.show_team_status()
        await asyncio.sleep(1)
        
        # Experiment 3: Backend Development
        await experiment.run_experiment(
            task_title="Implement GraphQL API Endpoint",
            task_type="Backend Development",
            priority=9,
            hours=6.0,
            skills=["backend", "api", "database"]
        )
        
        await experiment.show_team_status()
        await asyncio.sleep(1)
        
        # Experiment 4: Testing
        await experiment.run_experiment(
            task_title="Create E2E Test Suite",
            task_type="Testing",
            priority=6,
            hours=5.0,
            skills=["qa", "testing", "automation"]
        )
        
        await experiment.show_team_status()
        await asyncio.sleep(1)
        
        # Experiment 5: System Architecture
        await experiment.run_experiment(
            task_title="Design Microservices Architecture",
            task_type="System Architecture",
            priority=10,
            hours=8.0,
            skills=["architecture", "technical", "leadership"]
        )
        
        await experiment.show_team_status()
        await asyncio.sleep(1)
        
        # Experiment 6: Code Review
        await experiment.run_experiment(
            task_title="Review Authentication Module PR",
            task_type="Code Review",
            priority=7,
            hours=2.0,
            skills=["technical", "code_review", "security"]
        )
        
        await experiment.show_team_status()
        await asyncio.sleep(1)
        
        # Experiment 7: Creative Content
        await experiment.run_experiment(
            task_title="Create Marketing Landing Page Design",
            task_type="Creative Content",
            priority=5,
            hours=3.0,
            skills=["creative", "design", "frontend"]
        )
        
        await experiment.show_team_status()
        
        # Show summary
        await experiment.show_experiment_summary()
        
    finally:
        await experiment.cleanup()


async def run_interactive_mode():
    """Interactive mode - create custom tasks"""
    
    experiment = AgentExperiment()
    
    try:
        await experiment.setup_agents()
        
        print("\n" + "=" * 60)
        print("🎮 INTERACTIVE MODE - Create Custom Tasks")
        print("=" * 60)
        print("Type tasks to see how agents distribute them")
        print("Commands: 'status', 'summary', 'quit'")
        print("-" * 60)
        
        while True:
            print("\n📝 Create a new task (or command):")
            
            # Get task title
            title = input("  Title (or command): ").strip()
            
            if title.lower() in ['quit', 'exit', 'q']:
                break
            elif title.lower() == 'status':
                await experiment.show_team_status()
                continue
            elif title.lower() == 'summary':
                await experiment.show_experiment_summary()
                continue
            elif not title:
                continue
            
            # Get task type
            print("\n  Task Types:")
            print("    1. Technical content")
            print("    2. Visual Design")
            print("    3. Backend Development")
            print("    4. Frontend Development")
            print("    5. Testing")
            print("    6. System Architecture")
            print("    7. Code Review")
            print("    8. Creative Content")
            
            type_choice = input("  Choose type (1-8) or custom: ").strip()
            
            task_types = {
                "1": "Technical content",
                "2": "Visual Design",
                "3": "Backend Development",
                "4": "Frontend Development",
                "5": "Testing",
                "6": "System Architecture",
                "7": "Code Review",
                "8": "Creative Content"
            }
            
            task_type = task_types.get(type_choice, type_choice if type_choice else "General")
            
            # Get priority
            priority_input = input("  Priority (1-10, default 5): ").strip()
            priority = int(priority_input) if priority_input.isdigit() else 5
            priority = max(1, min(10, priority))
            
            # Get hours
            hours_input = input("  Estimated hours (default 2.0): ").strip()
            hours = float(hours_input) if hours_input else 2.0
            
            # Get skills
            skills_input = input("  Required skills (comma-separated, optional): ").strip()
            skills = [s.strip() for s in skills_input.split(",")] if skills_input else []
            
            # Run experiment
            await experiment.run_experiment(title, task_type, priority, hours, skills)
            await experiment.show_team_status()
        
        # Final summary
        await experiment.show_experiment_summary()
        
    finally:
        await experiment.cleanup()


async def run_scenario_tests():
    """Run specific scenario tests"""
    
    experiment = AgentExperiment()
    
    try:
        await experiment.setup_agents()
        
        print("\n" + "=" * 60)
        print("🎬 SCENARIO TESTING - Realistic Workplace Situations")
        print("=" * 60)
        
        scenarios = [
            {
                "scenario": "🚨 URGENT: Production Bug Fix",
                "title": "Critical Auth Bug - Users Can't Login",
                "type": "Backend Development",
                "priority": 10,
                "hours": 2.0,
                "skills": ["backend", "debugging", "security"]
            },
            {
                "scenario": "📊 Regular: Update Documentation",
                "title": "Add Examples to API Docs",
                "type": "Technical content",
                "priority": 5,
                "hours": 3.0,
                "skills": ["documentation", "technical", "api"]
            },
            {
                "scenario": "🎨 Creative: Brand Refresh",
                "title": "Redesign Company Logo and Brand Assets",
                "type": "Visual Design",
                "priority": 4,
                "hours": 12.0,
                "skills": ["design", "creative", "branding"]
            },
            {
                "scenario": "🏗️ Strategic: Architecture Planning",
                "title": "Design Event-Driven Microservices Architecture",
                "type": "System Architecture",
                "priority": 9,
                "hours": 10.0,
                "skills": ["architecture", "technical", "leadership"]
            },
            {
                "scenario": "🧪 Quality: Test Automation",
                "title": "Build Automated E2E Test Pipeline",
                "type": "Testing",
                "priority": 7,
                "hours": 6.0,
                "skills": ["testing", "automation", "qa"]
            },
            {
                "scenario": "👁️ Review: Code Quality Check",
                "title": "Review Payment Processing Module",
                "type": "Code Review",
                "priority": 8,
                "hours": 1.5,
                "skills": ["technical", "code_review", "security"]
            }
        ]
        
        for scenario_data in scenarios:
            print(f"\n{scenario_data['scenario']}")
            
            await experiment.run_experiment(
                task_title=scenario_data["title"],
                task_type=scenario_data["type"],
                priority=scenario_data["priority"],
                hours=scenario_data["hours"],
                skills=scenario_data["skills"]
            )
            
            await asyncio.sleep(0.5)
        
        # Final team status
        await experiment.show_team_status()
        await experiment.show_experiment_summary()
        
    finally:
        await experiment.cleanup()


def main():
    """Main entry point"""
    
    print("🎯 Agent Distribution Experiment Tool")
    print("=" * 60)
    print("Choose experiment mode:")
    print("  1. Predefined experiments (7 diverse tasks)")
    print("  2. Interactive mode (create custom tasks)")
    print("  3. Scenario tests (6 realistic scenarios)")
    
    choice = input("\nChoice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(run_predefined_experiments())
    elif choice == "2":
        asyncio.run(run_interactive_mode())
    elif choice == "3":
        asyncio.run(run_scenario_tests())
    else:
        print("Invalid choice. Running predefined experiments...")
        asyncio.run(run_predefined_experiments())


if __name__ == "__main__":
    main()
