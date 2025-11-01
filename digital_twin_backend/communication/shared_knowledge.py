"""
Shared Knowledge Base System for Digital Twin Agents
Manages agent context, capabilities, workloads, and task states
"""
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import redis.asyncio as redis
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AgentStatus(Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"


@dataclass
class AgentCapabilities:
    """Agent skill set and preferences"""
    technical_skills: Dict[str, float] = field(default_factory=dict)  # skill -> proficiency (0-1)
    preferred_task_types: List[str] = field(default_factory=list)
    work_style: Dict[str, Any] = field(default_factory=dict)  # collaborative, independent, etc.
    communication_style: Dict[str, Any] = field(default_factory=dict)  # formal, casual, etc.


@dataclass
class AgentContext:
    """Real-time agent state and context"""
    agent_id: str
    current_workload: int = 0
    max_capacity: int = 5
    availability_status: AgentStatus = AgentStatus.AVAILABLE
    current_tasks: List[str] = field(default_factory=list)
    recent_performance: Dict[str, Any] = field(default_factory=dict)
    last_active: datetime = field(default_factory=datetime.now)
    stress_level: float = 0.0  # 0-1, calculated from workload and deadlines
    
    @property
    def utilization(self) -> float:
        """Current capacity utilization (0-1)"""
        return self.current_workload / self.max_capacity if self.max_capacity > 0 else 0.0


@dataclass
class TaskInfo:
    """Task information for agent decision making"""
    task_id: str
    title: str
    description: str
    task_type: str
    priority: int  # 1-10
    estimated_hours: float
    deadline: Optional[datetime] = None
    required_skills: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class NegotiationMessage:
    """Agent negotiation message"""
    from_agent: str
    to_agents: List[str]
    task_id: str
    message_type: str  # offer, counter_offer, accept, decline, question
    content: str
    reasoning: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


class SharedKnowledgeBase:
    """Central knowledge repository for all agents"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = redis_url
        self.agent_capabilities: Dict[str, AgentCapabilities] = {}
        self.agent_contexts: Dict[str, AgentContext] = {}
        self.tasks: Dict[str, TaskInfo] = {}
        self.negotiation_history: Dict[str, List[NegotiationMessage]] = {}
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id
        
    async def initialize(self):
        """Initialize the knowledge base and Redis connection"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            print("✅ Connected to Redis for shared knowledge base")
        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            print("📝 Using in-memory storage (data will not persist)")
            self.redis_client = None
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    # Agent Management
    async def register_agent(self, agent_id: str, capabilities: AgentCapabilities) -> None:
        """Register an agent with their capabilities"""
        self.agent_capabilities[agent_id] = capabilities
        if agent_id not in self.agent_contexts:
            self.agent_contexts[agent_id] = AgentContext(agent_id=agent_id)
        
        # Store in Redis if available
        if self.redis_client:
            await self.redis_client.hset(
                f"agent:{agent_id}:capabilities",
                mapping={
                    "technical_skills": json.dumps(capabilities.technical_skills),
                    "preferred_task_types": json.dumps(capabilities.preferred_task_types),
                    "work_style": json.dumps(capabilities.work_style),
                    "communication_style": json.dumps(capabilities.communication_style)
                }
            )
    
    async def update_agent_context(self, agent_id: str, context: AgentContext) -> None:
        """Update agent's real-time context"""
        self.agent_contexts[agent_id] = context
        
        # Update stress level based on workload and deadlines
        context.stress_level = self._calculate_stress_level(agent_id)
        
        # Store in Redis
        if self.redis_client:
            await self.redis_client.hset(
                f"agent:{agent_id}:context",
                mapping={
                    "current_workload": context.current_workload,
                    "max_capacity": context.max_capacity,
                    "availability_status": context.availability_status.value,
                    "current_tasks": json.dumps(context.current_tasks),
                    "stress_level": context.stress_level,
                    "last_active": context.last_active.isoformat()
                }
            )
    
    async def get_agent_capabilities(self, agent_id: Optional[str] = None) -> Dict[str, AgentCapabilities]:
        """Get capabilities for specific agent or all agents"""
        if agent_id:
            return {agent_id: self.agent_capabilities.get(agent_id)}
        return self.agent_capabilities.copy()
    
    async def get_agent_context(self, agent_id: str) -> Optional[AgentContext]:
        """Get current context for an agent"""
        return self.agent_contexts.get(agent_id)
    
    async def get_all_agent_contexts(self) -> Dict[str, AgentContext]:
        """Get current contexts for all agents"""
        return self.agent_contexts.copy()
    
    # Task Management
    async def add_task(self, task: TaskInfo) -> None:
        """Add a new task to the knowledge base"""
        self.tasks[task.task_id] = task
        
        if self.redis_client:
            task_data = {
                "title": task.title,
                "description": task.description,
                "task_type": task.task_type,
                "priority": task.priority,
                "estimated_hours": task.estimated_hours,
                "required_skills": json.dumps(task.required_skills),
                "status": task.status.value,
                "created_at": task.created_at.isoformat()
            }
            if task.deadline:
                task_data["deadline"] = task.deadline.isoformat()
            
            await self.redis_client.hset(f"task:{task.task_id}", mapping=task_data)
    
    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task information"""
        return self.tasks.get(task_id)
    
    async def get_pending_tasks(self) -> List[TaskInfo]:
        """Get all pending tasks"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.PENDING]
    
    async def assign_task(self, task_id: str, agent_id: str, reasoning: str) -> None:
        """Assign a task to an agent"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.ASSIGNED
            self.task_assignments[task_id] = agent_id
            
            # Update agent workload
            if agent_id in self.agent_contexts:
                context = self.agent_contexts[agent_id]
                context.current_workload += 1
                context.current_tasks.append(task_id)
                await self.update_agent_context(agent_id, context)
            
            # Store in Redis
            if self.redis_client:
                await self.redis_client.hset(
                    f"assignment:{task_id}",
                    mapping={
                        "agent_id": agent_id,
                        "reasoning": reasoning,
                        "assigned_at": datetime.now().isoformat()
                    }
                )
    
    # Negotiation Management
    async def log_negotiation_message(self, message: NegotiationMessage) -> None:
        """Log a negotiation message"""
        task_id = message.task_id
        if task_id not in self.negotiation_history:
            self.negotiation_history[task_id] = []
        
        self.negotiation_history[task_id].append(message)
        
        # Store in Redis
        if self.redis_client:
            await self.redis_client.lpush(
                f"negotiation:{task_id}",
                json.dumps({
                    "from_agent": message.from_agent,
                    "to_agents": message.to_agents,
                    "message_type": message.message_type,
                    "content": message.content,
                    "reasoning": message.reasoning,
                    "confidence": message.confidence,
                    "timestamp": message.timestamp.isoformat()
                })
            )
    
    async def get_negotiation_history(self, task_id: str) -> List[NegotiationMessage]:
        """Get negotiation history for a task"""
        return self.negotiation_history.get(task_id, [])
    
    # Decision Support
    async def get_best_candidates(self, task: TaskInfo, top_k: int = 3) -> List[Tuple[str, float]]:
        """Get best agent candidates for a task based on capabilities and availability"""
        candidates = []
        
        for agent_id, capabilities in self.agent_capabilities.items():
            if agent_id == "manager":  # Manager doesn't take tasks
                continue
                
            context = self.agent_contexts.get(agent_id)
            if not context or context.availability_status == AgentStatus.OFFLINE:
                continue
            
            # Calculate match score
            score = self._calculate_task_match_score(task, capabilities, context)
            candidates.append((agent_id, score))
        
        # Sort by score and return top candidates
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]
    
    def _calculate_task_match_score(self, task: TaskInfo, capabilities: AgentCapabilities, context: AgentContext) -> float:
        """Calculate how well an agent matches a task"""
        score = 0.0
        
        # Skill match (40% weight)
        skill_scores = []
        for required_skill in task.required_skills:
            skill_level = capabilities.technical_skills.get(required_skill, 0.0)
            skill_scores.append(skill_level)
        
        if skill_scores:
            skill_match = sum(skill_scores) / len(skill_scores)
        else:
            skill_match = 0.5  # Neutral if no specific skills required
        
        score += skill_match * 0.4
        
        # Availability (30% weight)
        availability_score = 1.0 - context.utilization
        score += availability_score * 0.3
        
        # Task type preference (20% weight)
        if task.task_type in capabilities.preferred_task_types:
            type_preference = 1.0
        else:
            type_preference = 0.3  # Reduced score but still possible
        
        score += type_preference * 0.2
        
        # Recent performance (10% weight)
        performance_score = context.recent_performance.get('average_score', 0.7)
        score += performance_score * 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_stress_level(self, agent_id: str) -> float:
        """Calculate agent stress level based on workload and deadlines"""
        context = self.agent_contexts.get(agent_id)
        if not context:
            return 0.0
        
        # Base stress from utilization
        utilization_stress = context.utilization
        
        # Additional stress from approaching deadlines
        deadline_stress = 0.0
        now = datetime.now()
        
        for task_id in context.current_tasks:
            task = self.tasks.get(task_id)
            if task and task.deadline:
                time_left = (task.deadline - now).total_seconds() / 3600  # Hours
                if time_left < 24:  # Less than 24 hours
                    deadline_stress += 0.3
                elif time_left < 72:  # Less than 3 days
                    deadline_stress += 0.1
        
        return min(utilization_stress + deadline_stress, 1.0)


# Global instance
shared_knowledge = SharedKnowledgeBase()
