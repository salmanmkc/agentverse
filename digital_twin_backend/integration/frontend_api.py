"""
Frontend Integration API
Bridge between the agent system and the Next.js dashboard
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from communication.shared_knowledge import (
    SharedKnowledgeBase, 
    TaskInfo, 
    AgentContext,
    AgentCapabilities,
    TaskStatus,
    AgentStatus
)
from communication.protocol import AgentCommunicationProtocol, MessageType, MessagePriority
from agents.manager_agent import ManagerAgent
from agents.worker_agent import WorkerAgent
from config.settings import settings, AGENT_CONFIGS


# Pydantic models for API requests/responses
class TaskRequest(BaseModel):
    """Request model for creating new tasks"""
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    task_type: str = Field(..., description="Type of task")
    priority: int = Field(..., ge=1, le=10, description="Priority level 1-10")
    estimated_hours: float = Field(..., gt=0, description="Estimated hours to complete")
    deadline: Optional[datetime] = Field(None, description="Task deadline")
    required_skills: List[str] = Field(default_factory=list, description="Required skills")


class TaskResponse(BaseModel):
    """Response model for task operations"""
    task_id: str
    title: str
    status: str
    assigned_agent: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AgentStatusResponse(BaseModel):
    """Response model for agent status"""
    agent_id: str
    person_name: str
    availability_status: str
    current_workload: int
    max_capacity: int
    utilization: float
    stress_level: float
    assigned_tasks: List[str]
    last_active: datetime


class TaskAssignmentUpdate(BaseModel):
    """Model for task assignment updates"""
    task_id: str
    assigned_agent: str
    reasoning: str
    assignment_message: str


class SystemStatusResponse(BaseModel):
    """Response model for system status"""
    total_agents: int
    active_agents: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    system_uptime: str
    last_updated: datetime


class FrontendIntegrationAPI:
    """Main API class for frontend integration"""
    
    def __init__(
        self,
        shared_knowledge: SharedKnowledgeBase,
        communication_protocol: AgentCommunicationProtocol
    ):
        self.shared_knowledge = shared_knowledge
        self.communication_protocol = communication_protocol
        self.app = FastAPI(
            title="Digital Twin Workplace API",
            description="API for managing digital twin agents and task distribution",
            version="1.0.0"
        )
        
        # Agent system
        self.manager_agent: Optional[ManagerAgent] = None
        self.worker_agents: Dict[str, WorkerAgent] = {}
        self.agents_initialized = False
        
        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []
        
        # Initialize API routes
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self) -> None:
        """Setup CORS and other middleware"""
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.FRONTEND_API_URL, "http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self) -> None:
        """Setup API routes"""
        
        # System routes
        self.app.get("/api/status")(self.get_system_status)
        self.app.post("/api/initialize")(self.initialize_system)
        
        # Task routes
        self.app.post("/api/tasks", response_model=TaskResponse)(self.create_task)
        self.app.get("/api/tasks")(self.get_tasks)
        self.app.get("/api/tasks/{task_id}")(self.get_task)
        self.app.put("/api/tasks/{task_id}/assign")(self.assign_task_manually)
        self.app.put("/api/tasks/{task_id}/status")(self.update_task_status)
        
        # Agent routes
        self.app.get("/api/agents")(self.get_agents)
        self.app.get("/api/agents/{agent_id}")(self.get_agent_status)
        self.app.put("/api/agents/{agent_id}/availability")(self.update_agent_availability)
        
        # Frontend data sync routes
        self.app.get("/api/dashboard/data")(self.get_dashboard_data)
        self.app.post("/api/dashboard/sync")(self.sync_frontend_data)
        
        # WebSocket for real-time updates
        self.app.websocket("/ws")(self.websocket_endpoint)
    
    async def initialize_system(self) -> Dict[str, Any]:
        """Initialize the agent system"""
        
        if self.agents_initialized:
            return {"message": "System already initialized", "status": "success"}
        
        try:
            print("🔄 Initializing digital twin agent system...")
            
            # Initialize shared knowledge and communication
            await self.shared_knowledge.initialize()
            await self.communication_protocol.initialize()
            
            # Create manager agent
            self.manager_agent = ManagerAgent(
                shared_knowledge=self.shared_knowledge,
                worker_agent_ids=settings.WORKER_AGENT_IDS
            )
            await self.manager_agent.initialize()
            
            # Register manager with communication protocol
            await self.communication_protocol.register_agent(
                "manager",
                self.manager_agent.receive_message
            )
            
            # Create worker agents
            for agent_id in settings.WORKER_AGENT_IDS:
                agent_config = AGENT_CONFIGS.get(agent_id)
                if agent_config:
                    worker_capabilities = AgentCapabilities(
                        technical_skills=agent_config.capabilities,
                        preferred_task_types=[],
                        work_style={},
                        communication_style={}
                    )
                    worker = WorkerAgent(
                        agent_id=agent_id,
                        person_name=agent_config.person_name,
                        shared_knowledge=self.shared_knowledge,
                        capabilities=worker_capabilities,
                        model_path=agent_config.model_path if agent_config.fine_tuned else None
                    )
                    
                    await worker.initialize()
                    self.worker_agents[agent_id] = worker
                    
                    # Register with communication protocol
                    await self.communication_protocol.register_agent(
                        agent_id,
                        worker.receive_message
                    )
            
            self.agents_initialized = True
            
            print(f"✅ System initialized with {len(self.worker_agents)} worker agents")
            
            return {
                "message": "System initialized successfully",
                "status": "success",
                "agents": {
                    "manager": "manager",
                    "workers": list(self.worker_agents.keys())
                }
            }
            
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")
    
    async def get_system_status(self) -> SystemStatusResponse:
        """Get overall system status"""
        
        if not self.agents_initialized:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Get task counts
        task_values = list(self.shared_knowledge.tasks.values())
        pending_tasks = len([t for t in task_values if t.status == TaskStatus.PENDING])
        in_progress_tasks = len([t for t in task_values if t.status == TaskStatus.IN_PROGRESS])
        completed_tasks = len([t for t in task_values if t.status == TaskStatus.COMPLETED])
        
        # Get agent counts
        agent_contexts = await self.shared_knowledge.get_all_agent_contexts()
        active_agents = len([c for c in agent_contexts.values() if c.availability_status != AgentStatus.OFFLINE])
        
        return SystemStatusResponse(
            total_agents=len(self.worker_agents),
            active_agents=active_agents,
            pending_tasks=pending_tasks,
            in_progress_tasks=in_progress_tasks,
            completed_tasks=completed_tasks,
            system_uptime=datetime.now().isoformat(),
            last_updated=datetime.now()
        )
    
    async def create_task(self, task_request: TaskRequest, background_tasks: BackgroundTasks) -> TaskResponse:
        """Create a new task and distribute it to agents"""
        
        if not self.agents_initialized:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Generate task ID
        task_id = f"task_{int(datetime.now().timestamp() * 1000)}"
        
        # Create task object
        task = TaskInfo(
            task_id=task_id,
            title=task_request.title,
            description=task_request.description,
            task_type=task_request.task_type,
            priority=task_request.priority,
            estimated_hours=task_request.estimated_hours,
            deadline=task_request.deadline,
            required_skills=task_request.required_skills,
            dependencies=[],
            created_at=datetime.now(),
            status=TaskStatus.PENDING
        )
        
        # Add task distribution to background tasks
        background_tasks.add_task(self._distribute_task_background, task)
        
        return TaskResponse(
            task_id=task_id,
            title=task.title,
            status=task.status.value,
            assigned_agent=None,
            created_at=task.created_at,
            updated_at=datetime.now()
        )
    
    async def _distribute_task_background(self, task: TaskInfo) -> None:
        """Background task for distributing tasks to agents"""
        
        try:
            # Use manager agent to distribute task
            distribution_result = await self.manager_agent.distribute_task(task)
            
            if distribution_result.get("success"):
                # Notify frontend via WebSocket
                await self._broadcast_websocket({
                    "type": "task_assigned",
                    "task_id": task.task_id,
                    "assigned_agent": distribution_result["assigned_agent"],
                    "reasoning": distribution_result["reasoning"]
                })
                
                # Update frontend data format
                await self._update_frontend_task_assignment(
                    task.task_id,
                    distribution_result["assigned_agent"]
                )
            else:
                # Notify frontend of assignment failure
                await self._broadcast_websocket({
                    "type": "task_assignment_failed",
                    "task_id": task.task_id,
                    "error": distribution_result.get("error", "Unknown error")
                })
        
        except Exception as e:
            print(f"❌ Task distribution failed in background: {e}")
    
    async def get_tasks(self, status: Optional[str] = None) -> List[TaskResponse]:
        """Get all tasks, optionally filtered by status"""
        
        if not self.agents_initialized:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        tasks = list(self.shared_knowledge.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status.value == status]
        
        return [
            TaskResponse(
                task_id=task.task_id,
                title=task.title,
                status=task.status.value,
                assigned_agent=await self._get_task_assignee(task.task_id),
                created_at=task.created_at,
                updated_at=datetime.now()
            )
            for task in tasks
        ]
    
    async def get_task(self, task_id: str) -> TaskResponse:
        """Get a specific task"""
        
        task = await self.shared_knowledge.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskResponse(
            task_id=task.task_id,
            title=task.title,
            status=task.status.value,
            assigned_agent=await self._get_task_assignee(task_id),
            created_at=task.created_at,
            updated_at=datetime.now()
        )
    
    async def get_agents(self) -> List[AgentStatusResponse]:
        """Get all agent statuses"""
        
        if not self.agents_initialized:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        agent_responses = []
        
        for agent_id, agent in self.worker_agents.items():
            status = await agent.get_current_status()
            agent_responses.append(
                AgentStatusResponse(
                    agent_id=status["agent_id"],
                    person_name=status["person_name"],
                    availability_status=status["availability_status"],
                    current_workload=status["current_workload"],
                    max_capacity=status["max_capacity"],
                    utilization=status["utilization"],
                    stress_level=status["stress_level"],
                    assigned_tasks=status["assigned_tasks"],
                    last_active=datetime.fromisoformat(status["last_active"])
                )
            )
        
        return agent_responses
    
    async def get_agent_status(self, agent_id: str) -> AgentStatusResponse:
        """Get specific agent status"""
        
        if agent_id not in self.worker_agents:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent = self.worker_agents[agent_id]
        status = await agent.get_current_status()
        
        return AgentStatusResponse(
            agent_id=status["agent_id"],
            person_name=status["person_name"],
            availability_status=status["availability_status"],
            current_workload=status["current_workload"],
            max_capacity=status["max_capacity"],
            utilization=status["utilization"],
            stress_level=status["stress_level"],
            assigned_tasks=status["assigned_tasks"],
            last_active=datetime.fromisoformat(status["last_active"])
        )
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data in the format expected by the frontend dashboard"""
        
        if not self.agents_initialized:
            return {"message": "System not initialized", "data": []}
        
        # Get current tasks and convert to frontend format
        all_tasks = self.shared_knowledge.tasks
        dashboard_data = []
        
        for i, (task_id, task) in enumerate(all_tasks.items()):
            # Get assigned agent
            assigned_agent = await self._get_task_assignee(task_id)
            reviewer = assigned_agent if assigned_agent else "Assign reviewer"
            
            # Convert to frontend format (matching existing data.json structure)
            dashboard_item = {
                "id": i + 1,  # Sequential ID for frontend
                "header": task.title,
                "type": task.task_type,
                "status": "Done" if task.status == TaskStatus.COMPLETED else "In Process",
                "target": str(task.priority),
                "limit": str(int(task.estimated_hours)),
                "reviewer": reviewer
            }
            
            dashboard_data.append(dashboard_item)
        
        return {"data": dashboard_data}
    
    async def sync_frontend_data(self, frontend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync data from frontend dashboard"""
        
        try:
            synced_count = 0
            
            for item in frontend_data:
                # Convert frontend item to task if needed
                if item.get("reviewer") != "Assign reviewer":
                    # This item has been assigned in the frontend
                    task_id = f"frontend_task_{item['id']}"
                    
                    # Create or update task
                    task = TaskInfo(
                        task_id=task_id,
                        title=item["header"],
                        description=f"Task from frontend: {item['header']}",
                        task_type=item["type"],
                        priority=int(item.get("target", 5)),
                        estimated_hours=float(item.get("limit", 1)),
                        deadline=None,
                        required_skills=[],
                        status=TaskStatus.COMPLETED if item["status"] == "Done" else TaskStatus.IN_PROGRESS
                    )
                    
                    await self.shared_knowledge.add_task(task)
                    
                    # Assign to agent if specified
                    if item["reviewer"] != "Assign reviewer":
                        await self.shared_knowledge.assign_task(
                            task_id,
                            item["reviewer"],
                            "Assignment synced from frontend"
                        )
                    
                    synced_count += 1
            
            return {
                "message": f"Synced {synced_count} items from frontend",
                "status": "success"
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Sync failed: {str(e)}")
    
    async def websocket_endpoint(self, websocket: WebSocket):
        """WebSocket endpoint for real-time updates"""
        
        await websocket.accept()
        self.websocket_connections.append(websocket)
        
        try:
            while True:
                # Keep connection alive and listen for messages
                data = await websocket.receive_text()
                
                # Echo back or handle specific commands
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "status":
                    status = await self.get_system_status()
                    await websocket.send_text(json.dumps(status.dict()))
                
        except WebSocketDisconnect:
            print("📡 WebSocket client disconnected")
        finally:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)
    
    async def _broadcast_websocket(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all WebSocket connections"""
        
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message_str)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.websocket_connections.remove(websocket)
    
    async def _get_task_assignee(self, task_id: str) -> Optional[str]:
        """Get the agent assigned to a task"""
        
        return self.shared_knowledge.task_assignments.get(task_id)
    
    async def _update_frontend_task_assignment(self, task_id: str, assigned_agent: str) -> None:
        """Update task assignment in frontend-compatible format"""
        
        # This would integrate with the frontend's data structure
        # For now, we'll just broadcast the update
        await self._broadcast_websocket({
            "type": "assignment_update",
            "task_id": task_id,
            "reviewer": assigned_agent,
            "timestamp": datetime.now().isoformat()
        })
    
    # Additional utility methods
    async def assign_task_manually(self, task_id: str, agent_id: str = None) -> Dict[str, Any]:
        """Manually assign task to specific agent"""
        
        task = await self.shared_knowledge.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if agent_id and agent_id not in self.worker_agents:
            raise HTTPException(status_code=400, detail="Invalid agent ID")
        
        if agent_id:
            # Direct assignment
            await self.shared_knowledge.assign_task(task_id, agent_id, "Manual assignment")
        else:
            # Trigger automatic distribution
            await self._distribute_task_background(task)
        
        return {"message": "Task assignment initiated", "status": "success"}
    
    async def update_task_status(self, task_id: str, status: str) -> Dict[str, Any]:
        """Update task status"""
        
        task = await self.shared_knowledge.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        try:
            task.status = TaskStatus(status)
            await self.shared_knowledge.add_task(task)  # Updates existing
            
            return {"message": "Task status updated", "status": "success"}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")
    
    async def update_agent_availability(self, agent_id: str, availability: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent availability"""
        
        if agent_id not in self.worker_agents:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent = self.worker_agents[agent_id]
        
        new_status = availability.get("status")
        max_capacity = availability.get("max_capacity")
        
        await agent.update_availability(new_status, max_capacity)
        
        return {"message": "Agent availability updated", "status": "success"}


# Factory function to create the API instance
async def create_frontend_api(
    shared_knowledge: SharedKnowledgeBase,
    communication_protocol: AgentCommunicationProtocol
) -> FrontendIntegrationAPI:
    """Factory function to create and configure the API"""
    
    api = FrontendIntegrationAPI(shared_knowledge, communication_protocol)
    return api
