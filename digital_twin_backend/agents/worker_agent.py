"""
Worker Agent - Individual team member digital twin
Handles task consultation, peer negotiation, and work execution
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from digital_twin_backend.agents.base_agent import DigitalTwinAgent, TaskAssessment, AgentResponse
from digital_twin_backend.communication.shared_knowledge import (
    SharedKnowledgeBase, 
    TaskInfo, 
    NegotiationMessage,
    AgentCapabilities,
    AgentContext,
    TaskStatus
)


class WorkerAgent(DigitalTwinAgent):
    """Worker agent representing an individual team member"""
    
    def __init__(
        self,
        agent_id: str,
        person_name: str,
        shared_knowledge: SharedKnowledgeBase,
        capabilities: AgentCapabilities,
        model_path: Optional[str] = None
    ):
        super().__init__(
            agent_id=agent_id,
            person_name=person_name,
            shared_knowledge=shared_knowledge,
            capabilities=capabilities,
            model_path=model_path
        )
        
        # Worker-specific attributes
        self.assigned_tasks: Dict[str, TaskInfo] = {}
        self.completed_tasks: List[str] = []
        self.negotiation_style = self._determine_negotiation_style()
        
    def _determine_negotiation_style(self) -> str:
        """Determine agent's negotiation style based on personality"""
        
        if self.capabilities.work_style.get("collaborative", False):
            return "collaborative"
        elif self.capabilities.communication_style.get("direct", 0) > 0.7:
            return "direct"
        elif self.capabilities.communication_style.get("diplomatic", 0) > 0.7:
            return "diplomatic"
        else:
            return "balanced"
    
    # Message handling implementations
    async def _handle_task_consultation(self, message: Dict[str, Any]) -> None:
        """Handle task consultation from manager (Phase 1)"""
        
        print(f"🤔 {self.agent_id} received task consultation")
        
        try:
            # Extract task info from message
            task_data = message.get("task_info", {})
            task = TaskInfo(**task_data)
            
            # Perform task assessment
            assessment = await self.assess_task(task)
            
            # Generate consultation response
            response_message = await self._generate_consultation_response(task, assessment)
            
            # Send response back to manager
            await self.send_message(
                recipient_id=message["from"],
                content=response_message,
                message_type="consultation_response"
            )
            
            print(f"✅ {self.agent_id} completed task consultation for {task.task_id}")
            
        except Exception as e:
            print(f"❌ Error handling task consultation for {self.agent_id}: {e}")
    
    async def _handle_negotiation_message(self, message: Dict[str, Any]) -> None:
        """Handle negotiation message from peer (Phase 2)"""
        
        print(f"🤝 {self.agent_id} received negotiation message")
        
        try:
            # Extract negotiation context
            task_id = message.get("task_id")
            from_agent = message.get("from")
            content = message.get("content", "")
            
            if not task_id:
                print(f"⚠️  No task_id in negotiation message")
                return
            
            # Get task info
            task = await self.shared_knowledge.get_task(task_id)
            if not task:
                print(f"⚠️  Task {task_id} not found")
                return
            
            # Add to active negotiations
            if task_id not in self.active_negotiations:
                self.active_negotiations[task_id] = []
            
            negotiation_msg = NegotiationMessage(
                from_agent=from_agent,
                to_agents=[self.agent_id],
                task_id=task_id,
                message_type=message.get("message_type", "general"),
                content=content,
                reasoning=message.get("reasoning", ""),
                confidence=message.get("confidence", 0.5),
                timestamp=datetime.now()
            )
            
            self.active_negotiations[task_id].append(negotiation_msg)
            
            # Generate negotiation response
            response = await self._generate_negotiation_response(task, negotiation_msg)
            
            # Send response to relevant agents (not just the sender)
            other_agents = message.get("to_agents", [])
            for recipient in other_agents:
                if recipient != self.agent_id:  # Don't send to self
                    await self.send_message(
                        recipient_id=recipient,
                        content=response.content,
                        message_type="negotiation_response"
                    )
            
        except Exception as e:
            print(f"❌ Error handling negotiation message for {self.agent_id}: {e}")
    
    async def _handle_general_message(self, message: Dict[str, Any]) -> None:
        """Handle general message"""
        
        print(f"💬 {self.agent_id} received general message: {message['content'][:50]}...")
        
        # Process different types of general messages
        message_type = message.get("message_type", "general")
        
        if message_type == "task_assignment":
            await self._handle_task_assignment(message)
        elif message_type == "status_request":
            await self._handle_status_request(message)
        elif message_type == "work_update":
            await self._handle_work_update(message)
        else:
            # Generic response for other messages
            response = await self._generate_general_response(message)
            
            await self.send_message(
                recipient_id=message["from"],
                content=response,
                message_type="general_response"
            )
    
    async def _generate_consultation_response(self, task: TaskInfo, assessment: TaskAssessment) -> str:
        """Generate response to manager's task consultation"""
        
        # Build context for response generation
        context = {
            "task_info": task.__dict__,
            "assessment": {
                "can_handle": assessment.can_handle,
                "confidence": assessment.confidence,
                "estimated_time": assessment.estimated_time,
                "concerns": assessment.concerns
            },
            "current_workload": self.context.current_workload,
            "utilization": self.context.utilization
        }
        
        consultation_prompt = f"""
The manager asked me about taking on this task: {task.title}

My assessment:
- Can handle: {'Yes' if assessment.can_handle else 'No'}
- Confidence level: {assessment.confidence:.1%}
- Time estimate: {assessment.estimated_time:.1f} hours
- Current workload: {self.context.current_workload}/{self.context.max_capacity} tasks
- Concerns: {', '.join(assessment.concerns) if assessment.concerns else 'None'}

I need to respond honestly and professionally about my capability and availability.
Consider my communication style and work preferences in the response.
"""
        
        response = await self.generate_response(consultation_prompt, context)
        
        return response
    
    async def _generate_negotiation_response(self, task: TaskInfo, negotiation_msg: NegotiationMessage) -> AgentResponse:
        """Generate response to peer negotiation"""
        
        # Get my own assessment of the task
        my_assessment = await self.assess_task(task)
        
        # Get context about other agents
        peer_contexts = await self.shared_knowledge.get_all_agent_contexts()
        peer_capabilities = await self.shared_knowledge.get_agent_capabilities()
        
        # Build negotiation context
        negotiation_context = {
            "peer_message": {
                "from": negotiation_msg.from_agent,
                "content": negotiation_msg.content,
                "type": negotiation_msg.message_type
            },
            "my_assessment": {
                "can_handle": my_assessment.can_handle,
                "confidence": my_assessment.confidence,
                "concerns": my_assessment.concerns
            },
            "team_situation": self._analyze_team_situation(peer_contexts, task)
        }
        
        negotiation_prompt = f"""
We're discussing who should take the task: {task.title}

{negotiation_msg.from_agent} said: "{negotiation_msg.content}"

My situation:
- Can handle: {'Yes' if my_assessment.can_handle else 'No'}  
- Confidence: {my_assessment.confidence:.1%}
- Current utilization: {self.context.utilization:.1%}
- Concerns: {', '.join(my_assessment.concerns) if my_assessment.concerns else 'None'}

Based on my negotiation style ({self.negotiation_style}) and the team discussion,
how should I respond? Should I volunteer, support someone else's offer, or raise concerns?

Respond naturally as I would in a team discussion.
"""
        
        response_content = await self.generate_response(negotiation_prompt, negotiation_context)
        
        # Determine confidence in negotiation position
        negotiation_confidence = self._calculate_negotiation_confidence(
            my_assessment, negotiation_msg, peer_contexts
        )
        
        return AgentResponse(
            content=response_content,
            reasoning=f"Negotiation response based on {my_assessment.confidence:.1%} task confidence",
            confidence=negotiation_confidence,
            metadata={
                "negotiation_style": self.negotiation_style,
                "task_id": task.task_id,
                "in_response_to": negotiation_msg.from_agent
            }
        )
    
    def _analyze_team_situation(self, peer_contexts: Dict[str, AgentContext], task: TaskInfo) -> Dict[str, Any]:
        """Analyze current team situation for negotiation context"""
        
        team_analysis = {
            "total_agents": len(peer_contexts),
            "average_utilization": sum(c.utilization for c in peer_contexts.values()) / len(peer_contexts),
            "overloaded_agents": [aid for aid, c in peer_contexts.items() if c.utilization >= 1.0],
            "available_agents": [aid for aid, c in peer_contexts.items() if c.utilization < 0.7],
            "high_stress_agents": [aid for aid, c in peer_contexts.items() if c.stress_level > 0.7]
        }
        
        return team_analysis
    
    def _calculate_negotiation_confidence(
        self,
        my_assessment: TaskAssessment,
        peer_message: NegotiationMessage,
        peer_contexts: Dict[str, AgentContext]
    ) -> float:
        """Calculate confidence in negotiation position"""
        
        base_confidence = my_assessment.confidence
        
        # Adjust based on peer message type
        if peer_message.message_type == "offer" and peer_message.confidence > my_assessment.confidence:
            # Peer made a strong offer
            base_confidence *= 0.8
        elif peer_message.message_type == "suggestion" and self.agent_id in peer_message.content:
            # Peer suggested me
            base_confidence *= 1.2
        
        # Adjust based on relative workload
        my_utilization = self.context.utilization
        peer_utilizations = [c.utilization for c in peer_contexts.values() if c.agent_id != self.agent_id]
        avg_peer_utilization = sum(peer_utilizations) / len(peer_utilizations) if peer_utilizations else 0.5
        
        if my_utilization < avg_peer_utilization:
            # I'm less busy than average
            base_confidence *= 1.1
        elif my_utilization > avg_peer_utilization:
            # I'm busier than average
            base_confidence *= 0.9
        
        return min(base_confidence, 1.0)
    
    async def _handle_task_assignment(self, message: Dict[str, Any]) -> None:
        """Handle official task assignment"""
        
        task_id = message.get("task_id")
        if not task_id:
            print(f"⚠️  No task_id in assignment message")
            return
        
        task = await self.shared_knowledge.get_task(task_id)
        if not task:
            print(f"⚠️  Task {task_id} not found")
            return
        
        # Add to assigned tasks
        self.assigned_tasks[task_id] = task
        
        # Update context
        self.context.current_workload += 1
        self.context.current_tasks.append(task_id)
        await self.shared_knowledge.update_agent_context(self.agent_id, self.context)
        
        # Generate acknowledgment
        ack_prompt = f"""
I've been officially assigned the task: {task.title}

Generate a professional acknowledgment that:
1. Confirms I understand the assignment
2. Shows enthusiasm and commitment  
3. Mentions next steps I'll take
4. Asks any clarifying questions if needed

Keep it natural and aligned with my communication style.
"""
        
        acknowledgment = await self.generate_response(
            ack_prompt,
            context={"task": task.__dict__}
        )
        
        # Send acknowledgment back
        await self.send_message(
            recipient_id=message["from"],
            content=acknowledgment,
            message_type="assignment_acknowledgment"
        )
        
        print(f"✅ {self.agent_id} accepted assignment for task {task_id}")
    
    async def _handle_status_request(self, message: Dict[str, Any]) -> None:
        """Handle status request"""
        
        status = await self.get_current_status()
        
        status_response = f"""
Current status for {self.person_name}:
- Workload: {self.context.current_workload}/{self.context.max_capacity} tasks
- Utilization: {self.context.utilization:.1%}
- Stress level: {self.context.stress_level:.1f}/1.0
- Active tasks: {len(self.assigned_tasks)}
- Available capacity: {self.context.max_capacity - self.context.current_workload} tasks
"""
        
        await self.send_message(
            recipient_id=message["from"],
            content=status_response,
            message_type="status_response"
        )
    
    async def _handle_work_update(self, message: Dict[str, Any]) -> None:
        """Handle work progress update"""
        
        task_id = message.get("task_id")
        update_type = message.get("update_type", "progress")
        
        if task_id and task_id in self.assigned_tasks:
            
            if update_type == "completed":
                await self._complete_task(task_id)
            elif update_type == "progress":
                progress = message.get("progress", 0)
                await self._update_task_progress(task_id, progress)
    
    async def _complete_task(self, task_id: str) -> None:
        """Mark task as completed"""
        
        if task_id not in self.assigned_tasks:
            return
        
        task = self.assigned_tasks[task_id]
        
        # Update task status in shared knowledge
        task.status = TaskStatus.COMPLETED
        await self.shared_knowledge.add_task(task)  # This updates existing task
        
        # Update agent context
        self.context.current_workload = max(0, self.context.current_workload - 1)
        if task_id in self.context.current_tasks:
            self.context.current_tasks.remove(task_id)
        
        await self.shared_knowledge.update_agent_context(self.agent_id, self.context)
        
        # Move to completed tasks
        self.completed_tasks.append(task_id)
        del self.assigned_tasks[task_id]
        
        # Update performance metrics
        self._update_performance_metrics(task)
        
        print(f"✅ {self.agent_id} completed task {task_id}")
    
    async def _update_task_progress(self, task_id: str, progress: float) -> None:
        """Update task progress"""
        
        if task_id not in self.assigned_tasks:
            return
        
        # In a real implementation, this would update detailed progress tracking
        print(f"📈 {self.agent_id} updated progress on {task_id}: {progress:.1%}")
    
    def _update_performance_metrics(self, completed_task: TaskInfo) -> None:
        """Update agent's performance metrics"""
        
        # Calculate performance score based on task completion
        # This is simplified - real implementation would be more sophisticated
        
        if "recent_performance" not in self.context.recent_performance:
            self.context.recent_performance["recent_performance"] = {"completed_tasks": 0, "average_score": 0.7}
        
        perf = self.context.recent_performance["recent_performance"]
        perf["completed_tasks"] += 1
        
        # Simple scoring based on task complexity and completion
        task_score = 0.8  # Base score
        if completed_task.priority >= 8:
            task_score += 0.1  # Bonus for high priority
        if completed_task.task_type in self.capabilities.preferred_task_types:
            task_score += 0.1  # Bonus for preferred work
        
        # Update running average
        total_tasks = perf["completed_tasks"]
        current_avg = perf["average_score"]
        perf["average_score"] = ((current_avg * (total_tasks - 1)) + task_score) / total_tasks
    
    async def _generate_general_response(self, message: Dict[str, Any]) -> str:
        """Generate response to general message"""
        
        content = message.get("content", "")
        from_agent = message.get("from", "unknown")
        
        response_prompt = f"""
{from_agent} sent me this message: "{content}"

Generate a natural, helpful response that fits my personality and communication style.
Keep it professional but friendly.
"""
        
        response = await self.generate_response(
            response_prompt,
            context={"message": message}
        )
        
        return response
    
    # Utility methods
    async def get_current_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        
        return {
            "agent_id": self.agent_id,
            "person_name": self.person_name,
            "current_workload": self.context.current_workload,
            "max_capacity": self.context.max_capacity,
            "utilization": self.context.utilization,
            "stress_level": self.context.stress_level,
            "availability_status": self.context.availability_status.value,
            "assigned_tasks": list(self.assigned_tasks.keys()),
            "completed_tasks_count": len(self.completed_tasks),
            "negotiation_style": self.negotiation_style,
            "last_active": self.context.last_active.isoformat(),
            "model_loaded": self.is_model_loaded
        }
    
    async def update_availability(self, new_status: str, max_capacity: Optional[int] = None) -> None:
        """Update agent availability"""
        
        if max_capacity:
            self.context.max_capacity = max_capacity
        
        # Update availability status
        from digital_twin_backend.communication.shared_knowledge import AgentStatus
        
        if new_status in [status.value for status in AgentStatus]:
            self.context.availability_status = AgentStatus(new_status)
            await self.shared_knowledge.update_agent_context(self.agent_id, self.context)
            print(f"📅 {self.agent_id} availability updated to {new_status}")
    
    async def get_workload_forecast(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Get workload forecast"""
        
        # This is a placeholder for more sophisticated forecasting
        # Would analyze task deadlines, estimated completion times, etc.
        
        return {
            "current_utilization": self.context.utilization,
            "projected_utilization": min(self.context.utilization * 1.1, 1.0),  # Simplified
            "capacity_available": self.context.max_capacity - self.context.current_workload,
            "stress_trend": "stable",  # Would be calculated from historical data
            "recommended_new_tasks": max(0, int((self.context.max_capacity - self.context.current_workload) * 0.8))
        }
