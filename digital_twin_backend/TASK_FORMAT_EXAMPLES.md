# 📋 Task Format Examples - Complete Reference

## 🎯 **The Solution: UnifiedTask**

**ONE format that works everywhere:**
- ✅ Backend agent processing
- ✅ Frontend dashboard display
- ✅ API requests/responses
- ✅ Agent-to-agent communication
- ✅ Database storage

## 🔧 **How to Use in Different Scenarios**

### **Scenario 1: Frontend Creates New Task**

**Your Next.js Dashboard:**
```typescript
// Frontend sends this
const newTask = {
  header: "Update API Documentation",
  type: "Technical content",
  target: "7",  // Priority
  limit: "3"    // Estimated hours
}

// POST to backend
fetch('http://localhost:8000/api/tasks/from-frontend', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(newTask)
})
```

**Backend Receives (frontend_api.py):**
```python
from digital_twin_backend.communication.task_format import UnifiedTask

@app.post("/api/tasks/from-frontend")
async def create_task_from_frontend(frontend_data: Dict):
    # Convert frontend format to UnifiedTask
    task = UnifiedTask.from_frontend_format(frontend_data)
    
    # Distribute to agents (same format throughout!)
    result = await manager.distribute_task(task)
    
    # Return in API format
    return task.to_api_response()
```

**Agents Process:**
```python
# Manager and workers all use the SAME UnifiedTask object
async def distribute_task(self, task: UnifiedTask):
    # Phase 1: Consultation
    for agent in workers:
        assessment = await agent.assess_task(task)  # Same format!
    
    # Phase 2: Negotiation
    final_assignment = await self.negotiate(task)  # Same format!
    
    # Assignment
    task.assign_to(final_assignment["agent_id"])
    
    return task.to_api_response()
```

**Backend Sends Back to Frontend:**
```python
@app.get("/api/dashboard/data")
async def get_dashboard_data():
    # Get all UnifiedTasks
    tasks = list(shared_knowledge.tasks.values())
    
    # Convert to frontend format
    from digital_twin_backend.communication.task_format import batch_convert_to_frontend
    
    frontend_data = batch_convert_to_frontend(tasks)
    return {"data": frontend_data}
```

### **Scenario 2: Agent Receives Task for Assessment**

**Manager sends to Agent:**
```python
# Manager has UnifiedTask
task = UnifiedTask(title="API Docs", task_type="Technical content", priority=7, estimated_hours=3)

# Sends to agent in unified format
message = {
    "from": "manager",
    "to": "agent_1",
    "message_type": "task_consultation",
    "task": task.to_agent_format()  # Full details
}
```

**Agent Processes:**
```python
# Agent receives message
async def _handle_task_consultation(self, message: Dict):
    # Parse task from message
    task = UnifiedTask.from_dict(message["task"])
    
    # Assess using UnifiedTask properties
    can_handle = self._check_skills(task.required_skills)
    confidence = self._calculate_confidence(task)
    
    # Create assessment
    assessment = TaskAssessment(
        can_handle=can_handle,
        confidence=confidence,
        estimated_time=task.estimated_hours * (1 + self.stress_level)
    )
    
    return assessment
```

### **Scenario 3: Complete E2E Flow**

```python
# 1. Frontend creates task
frontend_task = {
    "header": "Implement User Authentication",
    "type": "Backend Development",
    "target": "9",
    "limit": "8"
}

# 2. Backend converts
task = UnifiedTask.from_frontend_format(frontend_task)
# Now it's a UnifiedTask with:
# - title: "Implement User Authentication"
# - task_type: "Backend Development"  
# - priority: 9
# - estimated_hours: 8.0
# - required_skills: ["backend", "technical", "database"] (auto-inferred!)
# - status: TaskStatus.PENDING

# 3. Distribute to agents
result = await manager.distribute_task(task)

# 4. Agent 1 (Eddie) assesses
eddie_assessment = await eddie.assess_task(task)
# - Uses task.required_skills to check match
# - Uses task.estimated_hours for time estimate
# - Uses task.priority for urgency assessment

# 5. Agent 2 (Jamik) assesses  
jamik_assessment = await jamik.assess_task(task)

# 6. Agents negotiate
# Both agents reference the SAME UnifiedTask
jamik_says: "I have 0.95 in backend (task.required_skills), I can take this"
eddie_says: "Jamik's better suited for this task.task_type"

# 7. Task assigned
task.assign_to("agent_2")  # Jamik
# - task.status becomes TaskStatus.ASSIGNED
# - task.assigned_to = "agent_2"
# - task.updated_at = now

# 8. Store in shared knowledge
await shared_knowledge.add_task(task.to_dict())

# 9. Send to frontend
frontend_update = task.to_frontend_format()
# {
#   "id": 1,
#   "header": "Implement User Authentication",
#   "type": "Backend Development",
#   "status": "In Process",
#   "target": "9",
#   "limit": "8",
#   "reviewer": "agent_2"  // or Jamik's name
# }
```

## 📊 **Format Comparison Table**

| Component | Before (Multiple Formats) | After (UnifiedTask) |
|-----------|---------------------------|---------------------|
| **Frontend** | Custom JSON format | `task.to_frontend_format()` |
| **API Request** | Pydantic TaskRequest | `UnifiedTask.from_api_request()` |
| **API Response** | Pydantic TaskResponse | `task.to_api_response()` |
| **Backend** | TaskInfo dataclass | `UnifiedTask` directly |
| **Agents** | Custom dict | `task.to_agent_format()` |
| **Storage** | Multiple schemas | `task.to_dict()` |

## 🎯 **Key Benefits**

✅ **One Format Everywhere** - No conversion errors
✅ **Auto-Inference** - Skills determined from task type
✅ **Type Safety** - Consistent field types
✅ **Easy Conversion** - One-line transforms to any format
✅ **Backward Compatible** - Works with your existing frontend
✅ **Future Proof** - Easy to extend with new fields

## 📝 **Quick Start Code**

```python
from digital_twin_backend.communication.task_format import UnifiedTask, TaskStatus

# Create task (any component can do this)
task = UnifiedTask(
    title="Your Task",
    task_type="Technical content",
    priority=7,
    estimated_hours=3
)

# Use in frontend API
frontend_json = task.to_frontend_format()

# Use in agent processing
agent_data = task.to_agent_format()

# Store in database
db_dict = task.to_dict()

# Parse from anywhere
task = UnifiedTask.from_frontend_format(frontend_data)
task = UnifiedTask.from_api_request(api_data)
task = UnifiedTask.from_dict(any_dict)
```

## 🚀 **Integration Example**

Here's how the unified format simplifies your entire system:

**Before (Multiple Formats):**
```python
# Frontend format
frontend_task = {"header": "...", "type": "...", "target": "7", "limit": "3"}

# Convert to backend
backend_task = TaskInfo(title=frontend_task["header"], ...)

# Convert to agent format
agent_dict = {"title": backend_task.title, "type": backend_task.task_type, ...}

# Convert back to frontend
frontend_response = {"id": 1, "header": backend_task.title, ...}

# Too many conversions! 😵
```

**After (UnifiedTask):**
```python
# ONE format
task = UnifiedTask.from_frontend_format(frontend_data)

# Use everywhere
await manager.distribute_task(task)  # Agents get same object
await shared_knowledge.add_task(task.to_dict())  # Storage
frontend_response = task.to_frontend_format()  # Frontend

# Simple! 🎉
```

---

**Now your entire system uses ONE consistent task format!** 

No more confusion about fields, types, or conversions. Everything just works! 🚀
