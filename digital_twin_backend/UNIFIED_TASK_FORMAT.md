# 📋 Unified Task Format - Complete Guide

## 🎯 **ONE Format for Everything**

We've created `UnifiedTask` - a single task format that works **everywhere** in your system.

## 🏗️ **Core Task Structure**

```python
from digital_twin_backend.communication.task_format import UnifiedTask, TaskStatus

task = UnifiedTask(
    title="Update API Documentation",
    task_type="Technical content",
    priority=7,
    estimated_hours=3.5,
    description="Add new endpoints to REST API docs",
    required_skills=["technical", "api", "documentation"],
    deadline=datetime(2024, 11, 5, 17, 0)
)
```

### **Required Fields:**
- `title` - Task name (str)
- `task_type` - Category (str)
- `priority` - 1-10 (int)
- `estimated_hours` - Time estimate (float)

### **Auto-Generated Fields:**
- `task_id` - Unique ID (auto-generated if not provided)
- `created_at` - Creation timestamp
- `updated_at` - Last modified timestamp
- `description` - Defaults to "Task: {title}"
- `required_skills` - Auto-inferred from task_type

### **Optional Fields:**
- `status` - TaskStatus enum (default: PENDING)
- `assigned_to` - Agent ID (str)
- `dependencies` - List of task IDs
- `deadline` - Completion deadline
- `metadata` - Any additional data

## 🔄 **Universal Conversion**

### **To Frontend Dashboard:**
```python
# Backend task
task = UnifiedTask(
    title="API Docs",
    task_type="Technical content",
    priority=7,
    estimated_hours=3
)

# Convert to your Next.js format
frontend_format = task.to_frontend_format(sequence_id=1)

# Result:
{
    "id": 1,
    "header": "API Docs",
    "type": "Technical content",
    "status": "Pending",
    "target": "7",
    "limit": "3",
    "reviewer": "Assign reviewer"
}
```

### **From Frontend Dashboard:**
```python
# Frontend sends:
frontend_data = {
    "id": 1,
    "header": "API Docs",
    "type": "Technical content",
    "status": "In Process",
    "target": "7",
    "limit": "3",
    "reviewer": "Eddie Lake"
}

# Convert to UnifiedTask
task = UnifiedTask.from_frontend_format(frontend_data)

# Now usable in backend
print(task.title)  # "API Docs"
print(task.assigned_to)  # "Eddie Lake"
print(task.priority)  # 7
```

### **To/From API:**
```python
# API Request
api_request = {
    "title": "Database Migration",
    "description": "Migrate to MongoDB",
    "task_type": "Backend Development",
    "priority": 9,
    "estimated_hours": 8.0,
    "required_skills": ["backend", "database"]
}

task = UnifiedTask.from_api_request(api_request)

# API Response
api_response = task.to_api_response()
# {
#   "task_id": "task_1234567890",
#   "title": "Database Migration",
#   "status": "pending",
#   "assigned_agent": null,
#   "created_at": "2024-11-01T18:30:00",
#   "updated_at": "2024-11-01T18:30:00"
# }
```

### **To/From Agent Communication:**
```python
# For agent-to-agent communication
agent_format = task.to_agent_format()

# Full task details as dict
{
    "task_id": "task_001",
    "title": "API Documentation",
    "description": "Update REST API docs",
    "task_type": "Technical content",
    "priority": 7,
    "estimated_hours": 3.5,
    "required_skills": ["technical", "api", "documentation"],
    "status": "pending",
    "assigned_to": null,
    ...
}
```

## 📨 **Usage Examples**

### **Example 1: Create Task in Backend**
```python
from digital_twin_backend.communication.task_format import UnifiedTask

# Create task
task = UnifiedTask(
    title="Code Review: Auth Module",
    task_type="Technical content",
    priority=8,
    estimated_hours=2.5,
    required_skills=["technical", "security", "review"]
)

# Send to agents
await shared_knowledge.add_task(task)
result = await manager.distribute_task(task)

# Task gets assigned
task.assign_to(result["assigned_agent"])

# Update frontend
frontend_data = task.to_frontend_format()
await update_frontend_dashboard(frontend_data)
```

### **Example 2: Task from Frontend**
```python
from digital_twin_backend.communication.task_format import UnifiedTask

# Frontend sends new task
frontend_input = {
    "header": "Design Dashboard Widget",
    "type": "Visual Design",
    "target": "6",
    "limit": "4"
}

# Convert to UnifiedTask
task = UnifiedTask.from_frontend_format(frontend_input)

# Distribute to agents (same code as above)
result = await manager.distribute_task(task)

# Auto-assigns and sends back to frontend
```

### **Example 3: Batch Sync with Frontend**
```python
from digital_twin_backend.communication.task_format import (
    batch_convert_to_frontend,
    batch_convert_from_frontend
)

# Get all tasks from backend
all_tasks = shared_knowledge.tasks.values()  # List of UnifiedTask

# Convert all to frontend format at once
frontend_data = batch_convert_to_frontend(all_tasks)

# Send to dashboard
return {"data": frontend_data}

# Receive updates from frontend
updated_frontend_data = [...]  # From Next.js
updated_tasks = batch_convert_from_frontend(updated_frontend_data)

# Process updates
for task in updated_tasks:
    await shared_knowledge.update_task(task)
```

### **Example 4: Task in Agent Communication**
```python
# Manager sends task to agent
message = {
    "from": "manager",
    "to": "agent_1",
    "message_type": "task_consultation",
    "task": task.to_agent_format()  # Full task details
}

# Agent receives and processes
received_task = UnifiedTask.from_dict(message["task"])
assessment = await agent.assess_task(received_task)
```

## 🎨 **Format Reference**

### **Universal Dictionary Format:**
```json
{
  "task_id": "task_1730486400123",
  "title": "API Documentation Update",
  "description": "Update REST API documentation with new endpoints",
  "task_type": "Technical content",
  "priority": 7,
  "estimated_hours": 3.5,
  "status": "pending",
  "assigned_to": null,
  "required_skills": ["technical", "api", "documentation"],
  "dependencies": [],
  "deadline": "2024-11-05T17:00:00",
  "created_at": "2024-11-01T18:30:00",
  "updated_at": "2024-11-01T18:30:00",
  "metadata": {}
}
```

### **Frontend Dashboard Format:**
```json
{
  "id": 1,
  "header": "API Documentation Update",
  "type": "Technical content",
  "status": "In Process",
  "target": "7",
  "limit": "3",
  "reviewer": "Eddie Lake"
}
```

### **API Request Format:**
```json
{
  "title": "API Documentation Update",
  "description": "Update REST API docs",
  "task_type": "Technical content",
  "priority": 7,
  "estimated_hours": 3.5,
  "required_skills": ["technical", "api", "documentation"]
}
```

### **API Response Format:**
```json
{
  "task_id": "task_1730486400123",
  "title": "API Documentation Update",
  "status": "assigned",
  "assigned_agent": "agent_1",
  "created_at": "2024-11-01T18:30:00",
  "updated_at": "2024-11-01T18:32:15"
}
```

## 🔧 **Integration Points**

### **1. Shared Knowledge System**
```python
# Store task
await shared_knowledge.add_task(task.to_dict())

# Retrieve task
task_dict = await shared_knowledge.get_task(task_id)
task = UnifiedTask.from_dict(task_dict)
```

### **2. Agent Assessment**
```python
# Agent receives task in unified format
async def assess_task(self, task: UnifiedTask) -> TaskAssessment:
    # Use task.required_skills, task.priority, task.estimated_hours
    # Same task object everywhere!
```

### **3. Frontend API**
```python
# Receive from frontend
@app.post("/api/tasks")
async def create_task(frontend_data: Dict):
    task = UnifiedTask.from_frontend_format(frontend_data)
    await distribute_task(task)
    return task.to_api_response()

# Send to frontend
@app.get("/api/dashboard/data")
async def get_dashboard():
    tasks = get_all_tasks()  # List[UnifiedTask]
    return {"data": batch_convert_to_frontend(tasks)}
```

### **4. Agent Communication**
```python
# Manager to worker
message = {
    "type": "task_consultation",
    "task": task.to_agent_format()
}

# Worker processes
task = UnifiedTask.from_dict(message["task"])
```

## 🎯 **Key Advantages**

✅ **Single source of truth** - No format confusion
✅ **Type safety** - Consistent field names and types
✅ **Auto-conversion** - Easy transformation between formats
✅ **Backward compatible** - Works with existing frontend
✅ **Validation** - Priority clamped to 1-10, hours must be positive
✅ **Skill inference** - Auto-determines skills from task type
✅ **Timestamps** - Automatic creation and update tracking

## 📝 **Quick Reference**

```python
from digital_twin_backend.communication.task_format import UnifiedTask, TaskStatus

# Create
task = UnifiedTask(title="Task", task_type="Type", priority=5, estimated_hours=2)

# Convert
dict_format = task.to_dict()
json_format = task.to_json()
frontend_format = task.to_frontend_format()
api_response = task.to_api_response()

# Parse
task = UnifiedTask.from_dict(data)
task = UnifiedTask.from_json(json_string)
task = UnifiedTask.from_frontend_format(frontend_data)
task = UnifiedTask.from_api_request(api_request)

# Update
task.assign_to("agent_1")
task.update_status(TaskStatus.IN_PROGRESS)
task.complete()

# Status
print(task.status.value)  # "completed"
print(task.status.to_frontend())  # "Done"
```

---

**Now you have ONE consistent format that works everywhere in your system!** 🎉

No more confusion about which format to use where - `UnifiedTask` handles all conversions automatically while maintaining a single source of truth throughout your digital twin workplace system.
