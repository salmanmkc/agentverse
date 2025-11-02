"""
Manager Agent - Orchestrates task distribution using two-phase process
Phase 1: Individual consultation with each agent
Phase 2: Facilitate peer negotiation among agents
"""
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from digital_twin_backend.agents.base_agent import DigitalTwinAgent, TaskAssessment, AgentResponse
from digital_twin_backend.communication.shared_knowledge import (
    SharedKnowledgeBase, 
    TaskInfo, 
    NegotiationMessage,
    AgentCapabilities,
    TaskStatus
)
from digital_twin_backend.config.settings import settings


class ManagerAgent(DigitalTwinAgent):
    """Manager agent responsible for task distribution and team coordination"""
    
    def __init__(
        self, 
        shared_knowledge: SharedKnowledgeBase,
        worker_agent_ids: List[str] = None,
        use_api_model: bool = False,
        api_provider: str = "openai",
        api_model: str = "gpt-3.5-turbo"
    ):
        # Manager capabilities - focused on leadership and coordination
        manager_capabilities = AgentCapabilities(
            technical_skills={
                "leadership": 0.95,
                "coordination": 0.9,
                "decision_making": 0.85,
                "communication": 0.9
            },
            preferred_task_types=["coordination", "planning", "delegation"],
            work_style={
                "collaborative": True,
                "diplomatic": True,
                "results_oriented": True
            },
            communication_style={
                "formal": 0.7,
                "direct": 0.8,
                "supportive": 0.9
            }
        )
        
        super().__init__(
            agent_id="manager",
            person_name="Team Manager",  # This would be customized
            shared_knowledge=shared_knowledge,
            capabilities=manager_capabilities,
            model_path=None,  # Will be set when fine-tuned model is available
            use_api_model=use_api_model,
            api_provider=api_provider,
            api_model=api_model
        )
        
        self.worker_agent_ids = worker_agent_ids or settings.WORKER_AGENT_IDS
        self.active_distributions: Dict[str, Dict[str, Any]] = {}  # task_id -> distribution state
        self.distribution_timeout = timedelta(minutes=settings.TASK_TIMEOUT_MINUTES)
    
    async def distribute_task(self, task: TaskInfo) -> Dict[str, Any]:
        """
        Main task distribution method using two-phase process
        
        Returns:
            Dict with assignment details and reasoning
        """
        print(f"🎯 Manager starting distribution for task: {task.title}")
        
        try:
            # Initialize distribution tracking
            distribution_id = f"dist_{task.task_id}_{int(time.time())}"
            self.active_distributions[task.task_id] = {
                "distribution_id": distribution_id,
                "task": task,
                "phase": "consultation",
                "started_at": datetime.now(),
                "phase1_responses": {},
                "phase2_negotiations": [],
                "final_assignment": None
            }
            
            # Add task to shared knowledge
            await self.shared_knowledge.add_task(task)
            
            # Phase 1: Individual consultation
            phase1_result = await self._phase1_individual_consultation(task)
            
            if not phase1_result["viable_candidates"]:
                return self._handle_no_viable_candidates(task)
            
            # Phase 2: Peer negotiation
            phase2_result = await self._phase2_peer_negotiation(task, phase1_result)
            
            # Finalize assignment
            final_assignment = await self._finalize_assignment(task, phase2_result)
            
            # Update tracking
            self.active_distributions[task.task_id]["final_assignment"] = final_assignment
            self.active_distributions[task.task_id]["phase"] = "completed"
            
            print(f"✅ Task {task.title} assigned to {final_assignment['assigned_agent']}")
            
            return final_assignment
            
        except Exception as e:
            print(f"❌ Task distribution failed for {task.task_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _phase1_individual_consultation(self, task: TaskInfo) -> Dict[str, Any]:
        """
        Phase 1: Consult with each worker agent individually
        """
        print(f"🔍 Phase 1: Individual consultation for task {task.task_id}")
        
        consultation_tasks = []
        
        # Create consultation tasks for each worker agent
        for agent_id in self.worker_agent_ids:
            consultation_tasks.append(
                self._consult_individual_agent(agent_id, task)
            )
        
        # Run consultations in parallel
        consultation_results = await asyncio.gather(*consultation_tasks, return_exceptions=True)
        
        # Process results
        viable_candidates = []
        all_assessments = {}
        
        for i, result in enumerate(consultation_results):
            agent_id = self.worker_agent_ids[i]
            
            if isinstance(result, Exception):
                print(f"⚠️  Consultation failed for {agent_id}: {result}")
                continue
            
            all_assessments[agent_id] = result
            
            if result.can_handle and result.confidence > 0.3:  # Minimum confidence threshold
                viable_candidates.append((agent_id, result))
        
        # Sort candidates by suitability score
        viable_candidates.sort(
            key=lambda x: self._calculate_suitability_score(x[1], task),
            reverse=True
        )
        
        # Store Phase 1 results (initialize if needed)
        if task.task_id in self.active_distributions:
            self.active_distributions[task.task_id]["phase1_responses"] = all_assessments
        
        # Generate manager's analysis
        analysis = await self._generate_phase1_analysis(task, all_assessments, viable_candidates)
        
        return {
            "viable_candidates": viable_candidates,
            "all_assessments": all_assessments,
            "manager_analysis": analysis
        }
    
    async def _consult_individual_agent(self, agent_id: str, task: TaskInfo) -> TaskAssessment:
        """
        Consult with individual agent about task capability
        """
        print(f"👥 Consulting {agent_id} about task {task.task_id}")
        
        # Get agent context
        agent_context = await self.shared_knowledge.get_agent_context(agent_id)
        if not agent_context:
            raise Exception(f"Agent {agent_id} not found in system")
        
        # Send consultation message to the agent
        consultation_message = {
            "from": self.agent_id,
            "to": agent_id,
            "message_type": "task_consultation",
            "task_info": task.__dict__,
            "consultation_prompt": self._build_consultation_prompt(task),
            "timestamp": datetime.now().isoformat()
        }
        
        # TODO: In full implementation, send message via communication protocol
        # For now, simulate the assessment based on agent capabilities
        assessment = await self._simulate_agent_assessment(agent_id, task)
        
        return assessment
    
    def _build_consultation_prompt(self, task: TaskInfo) -> str:
        """Build consultation prompt for agent"""
        return f"""
Hi, I have a new task that needs to be assigned and I'd like your honest assessment:

**Task: {task.title}**
- Description: {task.description}
- Type: {task.task_type}
- Priority: {task.priority}/10
- Estimated time: {task.estimated_hours} hours
- Required skills: {', '.join(task.required_skills) if task.required_skills else 'General'}
- Deadline: {task.deadline.strftime('%Y-%m-%d %H:%M') if task.deadline else 'Flexible'}

Can you handle this task given your current workload and expertise? 
Please be honest about:
1. Your capability/confidence level
2. Time you'd need (considering your current load)
3. Any concerns or potential issues
4. Alternative suggestions if you can't take it

I'm asking everyone individually first, then we'll discuss as a team.
"""
    
    async def _simulate_agent_assessment(self, agent_id: str, task: TaskInfo) -> TaskAssessment:
        """
        Simulate agent assessment (replace with actual agent communication)
        """
        # Get agent capabilities and context
        capabilities = await self.shared_knowledge.get_agent_capabilities(agent_id)
        context = await self.shared_knowledge.get_agent_context(agent_id)
        
        if not capabilities or agent_id not in capabilities:
            raise Exception(f"No capabilities found for {agent_id}")
        
        agent_caps = capabilities[agent_id]
        
        # Calculate basic assessment
        can_handle = True
        confidence = 0.7
        concerns = []
        
        # Check skill match
        if task.required_skills:
            skill_matches = []
            for skill in task.required_skills:
                skill_level = agent_caps.technical_skills.get(skill, 0.0)
                skill_matches.append(skill_level)
                if skill_level < 0.4:
                    concerns.append(f"Limited {skill} experience")
                    if skill_level < 0.2:
                        can_handle = False
            
            confidence *= (sum(skill_matches) / len(skill_matches)) if skill_matches else 0.5
        
        # Check workload
        if context and context.utilization > 0.8:
            concerns.append("High current workload")
            confidence *= 0.7
            if context.utilization >= 1.0:
                can_handle = False
        
        # Check task type preference
        if task.task_type in agent_caps.preferred_task_types:
            confidence *= 1.2
        elif task.task_type not in agent_caps.preferred_task_types:
            confidence *= 0.8
        
        # Estimate time (add buffer for stress)
        stress_multiplier = 1 + (context.stress_level if context else 0) * 0.5
        estimated_time = task.estimated_hours * stress_multiplier
        
        # Cap confidence
        confidence = min(confidence, 1.0)
        
        return TaskAssessment(
            can_handle=can_handle,
            confidence=confidence,
            estimated_time=estimated_time,
            concerns=concerns,
            reasoning=f"Assessment based on {skill_level:.1%} skill match and {context.utilization:.1%} utilization" if context else "Basic capability assessment"
        )
    
    async def _phase2_peer_negotiation(self, task: TaskInfo, phase1_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2: Facilitate negotiation among viable candidates
        """
        print(f"🤝 Phase 2: Peer negotiation for task {task.task_id}")
        
        viable_candidates = phase1_result["viable_candidates"]
        all_assessments = phase1_result["all_assessments"]
        
        if len(viable_candidates) <= 1:
            # No negotiation needed
            return {
                "negotiation_messages": [],
                "consensus": viable_candidates[0][0] if viable_candidates else None,
                "reasoning": "Only one viable candidate" if viable_candidates else "No viable candidates"
            }
        
        # Start negotiation
        negotiation_messages = []
        
        # Manager facilitates discussion
        facilitation_message = await self._generate_facilitation_message(task, viable_candidates)
        
        print(f"💬 Manager: {facilitation_message[:100]}...")
        
        # Simulate negotiation rounds (in reality, this would be real-time agent communication)
        for round_num in range(settings.MAX_NEGOTIATION_ROUNDS):
            round_messages = await self._conduct_negotiation_round(
                task, viable_candidates, all_assessments, round_num
            )
            
            negotiation_messages.extend(round_messages)
            
            # Check for consensus
            consensus = self._check_for_consensus(round_messages, viable_candidates)
            if consensus:
                break
        
        # Determine final consensus
        final_consensus = self._determine_final_consensus(negotiation_messages, viable_candidates)
        
        # Store negotiation history
        for msg in negotiation_messages:
            await self.shared_knowledge.log_negotiation_message(msg)
        
        return {
            "negotiation_messages": negotiation_messages,
            "consensus": final_consensus,
            "reasoning": "Peer negotiation consensus"
        }
    
    async def _generate_facilitation_message(self, task: TaskInfo, viable_candidates: List[Tuple[str, TaskAssessment]]) -> str:
        """Generate manager's facilitation message"""
        
        candidate_summary = []
        for agent_id, assessment in viable_candidates:
            candidate_summary.append(
                f"- {agent_id}: {assessment.confidence:.1%} confidence, {assessment.estimated_time:.1f}h estimate"
            )
        
        facilitation_prompt = f"""
As the team manager, I need to facilitate a discussion about task assignment.

Task: {task.title}
Priority: {task.priority}/10
Deadline: {task.deadline.strftime('%Y-%m-%d') if task.deadline else 'Flexible'}

After individual consultations, here are the viable candidates:
{chr(10).join(candidate_summary)}

I need to start a team discussion to decide who should take this task.
Please provide a natural facilitation message that encourages honest discussion
and helps the team reach the best decision for everyone.
"""
        
        # Generate using manager's personality (if model is loaded)
        facilitation_message = await self.generate_response(
            facilitation_prompt,
            context={"task_info": task.__dict__, "candidates": viable_candidates}
        )
        
        return facilitation_message
    
    async def _conduct_negotiation_round(
        self, 
        task: TaskInfo, 
        viable_candidates: List[Tuple[str, TaskAssessment]],
        all_assessments: Dict[str, TaskAssessment],
        round_num: int
    ) -> List[NegotiationMessage]:
        """Conduct one round of negotiation"""
        
        round_messages = []
        
        # Each viable candidate provides input
        for agent_id, assessment in viable_candidates:
            # Simulate agent negotiation message
            negotiation_msg = await self._simulate_agent_negotiation(
                agent_id, task, assessment, all_assessments, round_num
            )
            
            round_messages.append(negotiation_msg)
            print(f"💬 {agent_id}: {negotiation_msg.content[:80]}...")
        
        return round_messages
    
    async def _simulate_agent_negotiation(
        self,
        agent_id: str,
        task: TaskInfo,
        own_assessment: TaskAssessment,
        all_assessments: Dict[str, TaskAssessment],
        round_num: int
    ) -> NegotiationMessage:
        """Simulate agent negotiation message"""
        
        context = await self.shared_knowledge.get_agent_context(agent_id)
        
        # Generate different negotiation strategies based on agent and situation
        if own_assessment.confidence > 0.7 and context.utilization < 0.6:
            message_type = "offer"
            content = f"I'm confident I can handle this {task.task_type} task. I have good availability and relevant experience."
        elif own_assessment.confidence > 0.5 and context.utilization > 0.8:
            message_type = "conditional_offer"
            content = f"I could take this on, but I'm pretty busy. If others are also swamped, I can make it work."
        else:
            # Look for better candidate
            best_alternative = max(
                [(aid, assess) for aid, assess in all_assessments.items() if aid != agent_id],
                key=lambda x: x[1].confidence,
                default=(None, None)
            )
            
            if best_alternative[0]:
                message_type = "suggestion"
                content = f"I think {best_alternative[0]} might be better suited for this. They have stronger relevant skills and better availability."
            else:
                message_type = "concern"
                content = f"I have some concerns about the timeline and my current workload, but I can take it if needed."
        
        return NegotiationMessage(
            from_agent=agent_id,
            to_agents=[aid for aid, _ in all_assessments.items() if aid != agent_id],
            task_id=task.task_id,
            message_type=message_type,
            content=content,
            reasoning=f"Round {round_num} negotiation based on {own_assessment.confidence:.1%} confidence",
            confidence=own_assessment.confidence,
            timestamp=datetime.now()
        )
    
    def _check_for_consensus(self, messages: List[NegotiationMessage], candidates: List[Tuple[str, TaskAssessment]]) -> Optional[str]:
        """Check if negotiation has reached consensus"""
        
        offers = [msg for msg in messages if msg.message_type == "offer"]
        suggestions = [msg for msg in messages if msg.message_type == "suggestion"]
        
        # Clear consensus if someone makes a strong offer and others suggest them
        if offers:
            top_offer = max(offers, key=lambda x: x.confidence)
            supporting_suggestions = [
                msg for msg in suggestions 
                if top_offer.from_agent in msg.content
            ]
            
            if len(supporting_suggestions) >= len(candidates) // 2:
                return top_offer.from_agent
        
        return None
    
    def _determine_final_consensus(self, messages: List[NegotiationMessage], candidates: List[Tuple[str, TaskAssessment]]) -> str:
        """Determine final consensus from negotiation"""
        
        # Score each candidate based on negotiation
        scores = {}
        
        for agent_id, assessment in candidates:
            score = assessment.confidence
            
            # Boost score for offers
            offers = [msg for msg in messages if msg.from_agent == agent_id and msg.message_type == "offer"]
            if offers:
                score *= 1.2
            
            # Boost score for suggestions from others
            suggestions = [msg for msg in messages if agent_id in msg.content and msg.message_type == "suggestion"]
            score += len(suggestions) * 0.1
            
            scores[agent_id] = score
        
        # Return agent with highest score
        return max(scores.items(), key=lambda x: x[1])[0] if scores else candidates[0][0]
    
    async def _finalize_assignment(self, task: TaskInfo, phase2_result: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize task assignment"""
        
        assigned_agent = phase2_result["consensus"]
        
        if not assigned_agent:
            return {
                "success": False,
                "error": "No consensus reached",
                "task_id": task.task_id
            }
        
        # Update shared knowledge
        reasoning = f"Assigned through two-phase process: {phase2_result['reasoning']}"
        await self.shared_knowledge.assign_task(task.task_id, assigned_agent, reasoning)
        
        # Generate assignment message
        assignment_message = await self._generate_assignment_message(task, assigned_agent, phase2_result)
        
        return {
            "success": True,
            "task_id": task.task_id,
            "assigned_agent": assigned_agent,
            "reasoning": reasoning,
            "assignment_message": assignment_message,
            "phase1_summary": self.active_distributions[task.task_id]["phase1_responses"],
            "phase2_summary": phase2_result["negotiation_messages"]
        }
    
    async def _generate_assignment_message(self, task: TaskInfo, assigned_agent: str, phase2_result: Dict[str, Any]) -> str:
        """Generate assignment message"""
        
        assignment_prompt = f"""
After our team discussion, I'm assigning the task "{task.title}" to {assigned_agent}.

Generate a professional but friendly assignment message that:
1. Confirms the assignment
2. Acknowledges the team discussion
3. Sets clear expectations
4. Offers support

Keep it natural and encouraging.
"""
        
        assignment_message = await self.generate_response(
            assignment_prompt,
            context={"task": task.__dict__, "assigned_agent": assigned_agent}
        )
        
        return assignment_message
    
    def _handle_no_viable_candidates(self, task: TaskInfo) -> Dict[str, Any]:
        """Handle case where no agents can take the task"""
        
        return {
            "success": False,
            "error": "No viable candidates for task",
            "task_id": task.task_id,
            "recommendation": "Consider extending deadline, reducing scope, or hiring additional resources"
        }
    
    def _calculate_suitability_score(self, assessment: TaskAssessment, task: TaskInfo) -> float:
        """Calculate suitability score for ranking candidates"""
        
        base_score = assessment.confidence
        
        # Adjust for availability (prefer agents with more capacity)
        # This would use actual agent context in real implementation
        
        # Adjust for timeline efficiency
        if task.estimated_hours > 0:
            efficiency = task.estimated_hours / assessment.estimated_time
            base_score *= efficiency
        
        return base_score
    
    async def _generate_phase1_analysis(
        self, 
        task: TaskInfo, 
        assessments: Dict[str, TaskAssessment],
        viable_candidates: List[Tuple[str, TaskAssessment]]
    ) -> str:
        """Generate manager's analysis of Phase 1 results"""
        
        analysis_prompt = f"""
As the team manager, I've completed individual consultations for task: {task.title}

Results summary:
- Viable candidates: {len(viable_candidates)}/{len(assessments)}
- Top candidate: {viable_candidates[0][0] if viable_candidates else 'None'} ({viable_candidates[0][1].confidence:.1%} confidence)

Provide a brief analysis of the consultation results and next steps.
"""
        
        analysis = await self.generate_response(
            analysis_prompt,
            context={"assessments": assessments, "viable_candidates": viable_candidates}
        )
        
        return analysis
    
    # Message handlers (inherited from base class)
    async def _handle_task_consultation(self, message: Dict[str, Any]) -> None:
        """Handle incoming task consultation"""
        # Manager doesn't typically receive task consultations
        pass
    
    async def _handle_negotiation_message(self, message: Dict[str, Any]) -> None:
        """Handle negotiation message"""
        # Manager can monitor negotiation progress
        print(f"📝 Manager monitoring negotiation: {message['content'][:50]}...")
    
    async def _handle_general_message(self, message: Dict[str, Any]) -> None:
        """Handle general message"""
        print(f"💬 Manager received: {message['content'][:50]}...")
    
    # Utility methods
    async def get_team_status(self) -> Dict[str, Any]:
        """Get current team status summary"""
        
        team_contexts = await self.shared_knowledge.get_all_agent_contexts()
        
        status = {
            "total_agents": len(self.worker_agent_ids),
            "active_agents": len([c for c in team_contexts.values() if c.availability_status.value != "offline"]),
            "team_utilization": sum(c.utilization for c in team_contexts.values()) / len(team_contexts) if team_contexts else 0,
            "overloaded_agents": [aid for aid, c in team_contexts.items() if c.utilization >= 1.0],
            "available_agents": [aid for aid, c in team_contexts.items() if c.utilization < 0.8],
            "active_distributions": len(self.active_distributions)
        }
        
        return status
