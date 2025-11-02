# 🤖 Agent Architecture - Complete Structure

## 📊 **Class Hierarchy**

```
DigitalTwinAgent (ABC)
    ↓ inherits
    ├── ManagerAgent
    └── WorkerAgent
```

## 🏗️ **Core Architecture**

### **1. Base Agent Class** (`agents/base_agent.py`)

```python
class DigitalTwinAgent(ABC):
    """Base class for all digital twin agents"""
    
    def __init__(self, agent_id, person_name, shared_knowledge, capabilities, model_path):
        # Identity
        self.agent_id = "agent_1"
        self.person_name = "Eddie Lake"
        
        # Knowledge & Capabilities
        self.shared_knowledge = SharedKnowledgeBase()  # Access to team context
        self.capabilities = AgentCapabilities(...)     # Skills, preferences, style
        
        # AI Model (fine-tuned on person's messages)
        self.model_path = "models/Eddie_Lake_model/"
        self.model = None  # Loaded on initialize
        self.tokenizer = None
        
        # State
        self.context = AgentContext()           # Workload, stress, availability
        self.conversation_history = []          # Past messages
        self.active_negotiations = {}           # Current negotiations
        
        # Communication
        self.message_queue = asyncio.Queue()    # Incoming messages
        self.is_active = False
    
    # Core Methods
    async def initialize():
        """Setup agent and load model"""
        
    async def load_model():
        """Load fine-tuned personality model"""
        
    async def generate_response(prompt, context):
        """Generate personalized response using model"""
        
    async def assess_task(task):
        """Assess if agent can handle a task (Phase 1)"""
        
    async def participate_in_negotiation(task, other_assessments):
        """Participate in peer negotiation (Phase 2)"""
        
    async def send_message(recipient, content):
        """Send message to another agent"""
        
    async def receive_message(message):
        """Receive and queue incoming message"""
    
    # Abstract methods (must be implemented by subclasses)
    @abstractmethod
    async def _handle_task_consultation(message):
        """Handle task consultation from manager"""
        
    @abstractmethod  
    async def _handle_negotiation_message(message):
        """Handle negotiation from peers"""
        
    @abstractmethod
    async def _handle_general_message(message):
        """Handle general messages"""
```

### **2. Manager Agent** (`agents/manager_agent.py`)

```python
class ManagerAgent(DigitalTwinAgent):
    """Manager responsible for task distribution"""
    
    def __init__(self, shared_knowledge, worker_agent_ids):
        super().__init__(
            agent_id="manager",
            person_name="Team Manager",
            shared_knowledge=shared_knowledge,
            capabilities=manager_capabilities,  # Leadership, coordination
            model_path=None
        )
        
        self.worker_agent_ids = ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]
        self.active_distributions = {}  # Track ongoing distributions
    
    # Main Distribution Method
    async def distribute_task(task):
        """Two-phase task distribution"""
        
        # Phase 1: Individual consultation
        phase1_result = await self._phase1_individual_consultation(task)
        
        # Phase 2: Peer negotiation
        phase2_result = await self._phase2_peer_negotiation(task, phase1_result)
        
        # Finalize assignment
        final_assignment = await self._finalize_assignment(task, phase2_result)
        
        return final_assignment
    
    # Phase 1: Manager → Each Agent (1-on-1)
    async def _phase1_individual_consultation(task):
        """Ask each agent individually"""
        
        for agent_id in self.worker_agent_ids:
            assessment = await self._consult_individual_agent(agent_id, task)
            # Gets: can_handle, confidence, estimated_time, concerns
        
        # Identify viable candidates
        viable_candidates = [agent for agent in assessments if agent.can_handle]
        
        return viable_candidates
    
    # Phase 2: Agents ↔ Agents (peer discussion)
    async def _phase2_peer_negotiation(task, viable_candidates):
        """Let agents discuss among themselves"""
        
        for round in range(MAX_NEGOTIATION_ROUNDS):
            # Each agent contributes to discussion
            messages = await self._conduct_negotiation_round(task, viable_candidates)
            
            # Check for consensus
            if consensus_reached(messages):
                break
        
        # Determine who takes the task
        final_agent = self._determine_final_consensus(messages)
        
        return final_agent
```

### **3. Worker Agent** (`agents/worker_agent.py`)

```python
class WorkerAgent(DigitalTwinAgent):
    """Individual team member digital twin"""
    
    def __init__(self, agent_id, person_name, shared_knowledge, capabilities, model_path):
        super().__init__(agent_id, person_name, shared_knowledge, capabilities, model_path)
        
        # Worker-specific state
        self.assigned_tasks = {}        # Tasks currently assigned to me
        self.completed_tasks = []       # Task history
        self.negotiation_style = self._determine_negotiation_style()
    
    # Message Handlers (implements abstract methods)
    
    async def _handle_task_consultation(message):
        """Manager asks: Can you handle this task?"""
        
        task = TaskInfo(**message["task_info"])
        
        # Assess the task
        assessment = await self.assess_task(task)
        
        # Generate response using personality model
        response = await self.generate_response(
            f"Manager asked about task: {task.title}. My assessment: {assessment}"
        )
        
        # Send back to manager
        await self.send_message("manager", response)
    
    async def _handle_negotiation_message(message):
        """Peer says: I think you should take this / I can do it"""
        
        peer_agent = message["from"]
        task = TaskInfo(**message["task"])
        
        # Consider peer's input
        my_assessment = await self.assess_task(task)
        peer_contexts = await self.shared_knowledge.get_all_agent_contexts()
        
        # Generate negotiation response using personality
        response = await self._generate_negotiation_response(task, message)
        
        # Send to other agents
        await self.send_message(peer_agent, response)
    
    # Task Assessment (Phase 1)
    async def assess_task(task):
        """Assess if I can handle this task"""
        
        # Check skills
        skill_match = self._check_skill_match(task.required_skills)
        
        # Check availability
        have_capacity = self.context.utilization < 0.8
        
        # Calculate confidence
        confidence = skill_match * (1.0 - self.context.stress_level)
        
        # Estimate time considering my workload
        estimated_time = task.estimated_hours * (1 + self.context.stress_level)
        
        return TaskAssessment(
            can_handle=skill_match > 0.5 and have_capacity,
            confidence=confidence,
            estimated_time=estimated_time,
            concerns=self._identify_concerns(task)
        )
    
    # Negotiation (Phase 2)
    async def participate_in_negotiation(task, other_assessments):
        """Discuss with peers who should take it"""
        
        # See what others said
        peer_contexts = await self.shared_knowledge.get_all_agent_contexts()
        
        # Decide my position
        if self.confidence > 0.7 and self.utilization < 0.6:
            return "I can confidently take this task"
        elif peer_has_better_fit:
            return f"I think {peer_name} is better suited"
        else:
            return "I have concerns but can do it if needed"
```

## 🔄 **Agent Communication Flow**

```
1. Task arrives
        ↓
2. Manager creates distribution
        ↓
3. PHASE 1: Manager → Each Worker (individually)
   Manager: "Can you handle API docs task?"
   Eddie: "Yes, 71% confidence, 3.5h estimate"
   Jamik: "Not my area, I'm backend focused"
   Sarah: "I'm overloaded right now"
        ↓
4. Manager identifies: Eddie is viable
        ↓
5. PHASE 2: Workers ↔ Workers (peer discussion)
   (If multiple viable candidates)
   Eddie: "I can do it but slightly busy"
   Jamik: "Eddie's better at docs, I agree"
        ↓
6. Consensus: Eddie takes the task
        ↓
7. Manager finalizes assignment
        ↓
8. Eddie's workload updated
```

## 📁 **File Structure**

```
agents/
├── __init__.py
├── base_agent.py          # Abstract base class (532 lines)
│   ├── DigitalTwinAgent
│   ├── AgentResponse
│   └── TaskAssessment
│
├── manager_agent.py       # Manager implementation (603 lines)
│   └── ManagerAgent(DigitalTwinAgent)
│       ├── distribute_task()
│       ├── _phase1_individual_consultation()
│       ├── _phase2_peer_negotiation()
│       └── _finalize_assignment()
│
└── worker_agent.py        # Worker implementation (512 lines)
    └── WorkerAgent(DigitalTwinAgent)
        ├── assess_task()
        ├── participate_in_negotiation()
        ├── _handle_task_consultation()
        └── _handle_negotiation_message()
```

## 🎯 **Key Agent Properties**

Each agent has:
- **Identity:** `agent_id`, `person_name`
- **AI Model:** Fine-tuned on their WhatsApp/LinkedIn messages
- **Capabilities:** Skills, preferences, communication style
- **Context:** Current workload, stress, availability
- **Communication:** Message queue, conversation history
- **Behavior:** Custom negotiation and assessment logic

## 💬 **Agent Interaction Example**

```python
# Creating agents
manager = ManagerAgent(shared_knowledge, worker_ids=["agent_1", "agent_2"])
eddie = WorkerAgent("agent_1", "Eddie Lake", shared_knowledge, eddie_capabilities, "models/Eddie_Lake_model")
jamik = WorkerAgent("agent_2", "Jamik Tashpulatov", shared_knowledge, jamik_capabilities, "models/Jamik_model")

# Task distribution
task = UnifiedTask(title="API Docs", type="Technical", priority=7, hours=3)

# Manager orchestrates
result = await manager.distribute_task(task)
# → Internally: Consults eddie and jamik, they discuss, decision made

# Result
print(result["assigned_agent"])  # "agent_1" (Eddie)
print(result["reasoning"])       # "Best skill match and availability"
```

---

**Main files to understand the agentic structure:**
1. `agents/base_agent.py` - Core agent architecture (lines 62-532)
2. `agents/manager_agent.py` - Manager's two-phase distribution (lines 23-603)
3. `agents/worker_agent.py` - Worker's assessment and negotiation (lines 21-512)

Want me to show you a specific part of the agent structure in more detail? 🤖
