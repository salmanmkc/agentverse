"""
Unified Task Format for Digital Twin System
Single source of truth for task representation across all components
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import json


class TaskStatus(Enum):
    """Standardized task status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    
    @classmethod
    def from_frontend(cls, frontend_status: str) -> 'TaskStatus':
        """Convert frontend status to TaskStatus"""
        mapping = {
            "Pending": cls.PENDING,
            "In Process": cls.IN_PROGRESS,
            "Done": cls.COMPLETED,
            "Cancelled": cls.CANCELLED
        }
        return mapping.get(frontend_status, cls.PENDING)
    
    def to_frontend(self) -> str:
        """Convert to frontend format"""
        mapping = {
            self.PENDING: "Pending",
            self.ASSIGNED: "In Process",
            self.IN_PROGRESS: "In Process",
            self.COMPLETED: "Done",
            self.CANCELLED: "Cancelled"
        }
        return mapping.get(self, "Pending")


class UnifiedTask:
    """
    Unified task format used throughout the entire system
    Works for: Backend, Frontend, API, Agent Communication
    """
    
    def __init__(
        self,
        title: str,
        task_type: str,
        priority: int,
        estimated_hours: float,
        task_id: Optional[str] = None,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.PENDING,
        assigned_to: Optional[str] = None,
        required_skills: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        deadline: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        # Core fields (required)
        self.title = title
        self.task_type = task_type
        self.priority = max(1, min(10, priority))  # Clamp to 1-10
        self.estimated_hours = max(0.1, estimated_hours)
        
        # Auto-generated fields
        self.task_id = task_id or self._generate_task_id()
        self.description = description or f"Task: {title}"
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        
        # Status fields
        self.status = status if isinstance(status, TaskStatus) else TaskStatus.PENDING
        self.assigned_to = assigned_to
        
        # Optional fields
        self.required_skills = required_skills or self._infer_skills_from_type(task_type)
        self.dependencies = dependencies or []
        self.deadline = deadline
        self.metadata = metadata or {}
    
    @staticmethod
    def _generate_task_id() -> str:
        """Generate unique task ID"""
        timestamp = int(datetime.now().timestamp() * 1000)
        return f"task_{timestamp}"
    
    @staticmethod
    def _infer_skills_from_type(task_type: str) -> List[str]:
        """Infer required skills from task type"""
        skill_mapping = {
            "Technical content": ["technical", "documentation"],
            "API Documentation": ["technical", "api", "documentation"],
            "System Architecture": ["technical", "architecture", "design"],
            "Backend Development": ["backend", "technical", "database"],
            "Frontend Development": ["frontend", "technical", "ui"],
            "Visual Design": ["creative", "design", "visual"],
            "UI/UX": ["creative", "design", "frontend"],
            "Testing": ["qa", "testing", "technical"],
            "Research": ["research", "analysis"],
            "Planning": ["planning", "coordination"],
            "Narrative": ["communication", "writing"],
        }
        
        return skill_mapping.get(task_type, ["general"])
    
    # ============= Serialization Methods =============
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (universal format)"""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type,
            "priority": self.priority,
            "estimated_hours": self.estimated_hours,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "required_skills": self.required_skills,
            "dependencies": self.dependencies,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_frontend_format(self, sequence_id: Optional[int] = None) -> Dict[str, Any]:
        """Convert to frontend dashboard format"""
        return {
            "id": sequence_id or int(self.task_id.split('_')[1]) % 1000,
            "header": self.title,
            "type": self.task_type,
            "status": self.status.to_frontend(),
            "target": str(self.priority),
            "limit": str(int(self.estimated_hours)),
            "reviewer": self.assigned_to or "Assign reviewer"
        }
    
    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status.value,
            "assigned_agent": self.assigned_to,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def to_agent_format(self) -> Dict[str, Any]:
        """Convert to agent communication format (full details)"""
        return self.to_dict()
    
    # ============= Deserialization Methods =============
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedTask':
        """Create from dictionary"""
        
        # Parse datetime fields
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        deadline = datetime.fromisoformat(data['deadline']) if data.get('deadline') else None
        
        # Parse status
        status = TaskStatus(data['status']) if isinstance(data.get('status'), str) else data.get('status', TaskStatus.PENDING)
        
        return cls(
            task_id=data.get('task_id'),
            title=data['title'],
            description=data.get('description'),
            task_type=data['task_type'],
            priority=data['priority'],
            estimated_hours=data['estimated_hours'],
            status=status,
            assigned_to=data.get('assigned_to'),
            required_skills=data.get('required_skills'),
            dependencies=data.get('dependencies'),
            deadline=deadline,
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get('metadata', {})
        )
    
    @classmethod
    def from_json(cls, json_string: str) -> 'UnifiedTask':
        """Create from JSON string"""
        data = json.loads(json_string)
        return cls.from_dict(data)
    
    @classmethod
    def from_frontend_format(cls, frontend_data: Dict[str, Any]) -> 'UnifiedTask':
        """Create from frontend dashboard format"""
        
        # Map frontend fields to unified format
        return cls(
            task_id=f"frontend_task_{frontend_data.get('id', 0)}",
            title=frontend_data['header'],
            task_type=frontend_data['type'],
            priority=int(frontend_data.get('target', 5)),
            estimated_hours=float(frontend_data.get('limit', 1)),
            status=TaskStatus.from_frontend(frontend_data.get('status', 'Pending')),
            assigned_to=frontend_data.get('reviewer') if frontend_data.get('reviewer') != "Assign reviewer" else None,
            description=f"Task from frontend: {frontend_data['header']}"
        )
    
    @classmethod  
    def from_api_request(cls, request_data: Dict[str, Any]) -> 'UnifiedTask':
        """Create from API request"""
        
        deadline = None
        if request_data.get('deadline'):
            if isinstance(request_data['deadline'], str):
                deadline = datetime.fromisoformat(request_data['deadline'])
            else:
                deadline = request_data['deadline']
        
        return cls(
            title=request_data['title'],
            description=request_data.get('description'),
            task_type=request_data['task_type'],
            priority=request_data['priority'],
            estimated_hours=request_data['estimated_hours'],
            deadline=deadline,
            required_skills=request_data.get('required_skills')
        )
    
    # ============= Utility Methods =============
    
    def update_status(self, new_status: TaskStatus) -> None:
        """Update task status with timestamp"""
        self.status = new_status
        self.updated_at = datetime.now()
    
    def assign_to(self, agent_id: str) -> None:
        """Assign task to an agent"""
        self.assigned_to = agent_id
        self.status = TaskStatus.ASSIGNED
        self.updated_at = datetime.now()
    
    def complete(self) -> None:
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.updated_at = datetime.now()
    
    def add_dependency(self, task_id: str) -> None:
        """Add a task dependency"""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)
            self.updated_at = datetime.now()
    
    def __repr__(self) -> str:
        return f"UnifiedTask(id={self.task_id}, title='{self.title}', status={self.status.value}, assigned_to={self.assigned_to})"
    
    def __str__(self) -> str:
        return f"{self.title} [{self.status.value}] - Priority: {self.priority}/10"


# ============= Convenience Functions =============

def create_task_from_any_format(data: Dict[str, Any], source: str = "auto") -> UnifiedTask:
    """
    Create UnifiedTask from any format - auto-detects source
    
    Args:
        data: Task data dictionary
        source: "auto", "frontend", "api", "backend", or "dict"
    
    Returns:
        UnifiedTask instance
    """
    
    if source == "auto":
        # Auto-detect format
        if "header" in data and "reviewer" in data:
            source = "frontend"
        elif "task_id" in data and "required_skills" in data:
            source = "backend"
        elif all(k in data for k in ["title", "task_type", "priority", "estimated_hours"]):
            source = "api"
        else:
            source = "dict"
    
    if source == "frontend":
        return UnifiedTask.from_frontend_format(data)
    elif source == "api":
        return UnifiedTask.from_api_request(data)
    else:
        return UnifiedTask.from_dict(data)


def batch_convert_to_frontend(tasks: List[UnifiedTask]) -> List[Dict[str, Any]]:
    """Convert list of tasks to frontend format"""
    return [task.to_frontend_format(i + 1) for i, task in enumerate(tasks)]


def batch_convert_from_frontend(frontend_data: List[Dict[str, Any]]) -> List[UnifiedTask]:
    """Convert frontend data to UnifiedTasks"""
    return [UnifiedTask.from_frontend_format(item) for item in frontend_data]
