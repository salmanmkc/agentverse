"""
Base Digital Twin Agent Class
Handles core agent functionality including communication, reasoning, and task management
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Optional AI/ML imports
try:
    import torch
    from transformers import (
        AutoTokenizer, 
        AutoModelForCausalLM, 
        pipeline,
        GenerationConfig
    )
    ML_AVAILABLE = True
except ImportError:
    torch = None
    AutoTokenizer = None
    AutoModelForCausalLM = None
    pipeline = None
    GenerationConfig = None
    ML_AVAILABLE = False

from digital_twin_backend.communication.shared_knowledge import (
    SharedKnowledgeBase, 
    AgentCapabilities, 
    AgentContext, 
    TaskInfo, 
    NegotiationMessage,
    AgentStatus
)
from digital_twin_backend.config.settings import settings


@dataclass
class AgentResponse:
    """Standard agent response format"""
    content: str
    reasoning: str
    confidence: float  # 0-1
    metadata: Dict[str, Any] = None
    

@dataclass
class TaskAssessment:
    """Agent's assessment of a task"""
    can_handle: bool
    confidence: float
    estimated_time: float  # hours
    concerns: List[str]
    reasoning: str
    alternative_suggestions: List[str] = None


class DigitalTwinAgent(ABC):
    """Base class for all digital twin agents"""
    
    def __init__(
        self, 
        agent_id: str, 
        person_name: str, 
        shared_knowledge: SharedKnowledgeBase,
        capabilities: AgentCapabilities,
        model_path: Optional[str] = None,
        use_api_model: bool = False,
        api_provider: str = "openai",
        api_model: str = "gpt-3.5-turbo"
    ):
        self.agent_id = agent_id
        self.person_name = person_name
        self.shared_knowledge = shared_knowledge
        self.capabilities = capabilities
        self.model_path = model_path
        
        # API Model settings
        self.use_api_model = use_api_model
        self.api_provider = api_provider
        self.api_model = api_model
        
        # Model components
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[AutoModelForCausalLM] = None
        self.generation_config: Optional[GenerationConfig] = None
        self.is_model_loaded = False
        
        # Agent state
        self.context = AgentContext(agent_id=agent_id)
        self.conversation_history: List[Dict[str, Any]] = []
        self.active_negotiations: Dict[str, List[NegotiationMessage]] = {}
        
        # Communication
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.is_active = False
        
    async def initialize(self) -> None:
        """Initialize the agent"""
        # Register with shared knowledge base
        await self.shared_knowledge.register_agent(self.agent_id, self.capabilities)
        
        # Load model if path is provided
        if self.model_path:
            await self.load_model()
        else:
            print(f"⚠️  Agent {self.agent_id} initialized without fine-tuned model")
        
        # Start message processing
        self.is_active = True
        asyncio.create_task(self._process_messages())
        
        print(f"✅ Agent {self.agent_id} ({self.person_name}) initialized")
    
    async def load_model(self) -> None:
        """Load the agent's fine-tuned model"""
        if not ML_AVAILABLE:
            print(f"⚠️  ML libraries not available for {self.agent_id}")
            print("💡 Install with: pip install torch transformers datasets peft")
            self.is_model_loaded = False
            return
            
        try:
            print(f"🔄 Loading model for {self.agent_id}...")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path if self.model_path else settings.BASE_MODEL_NAME
            )
            
            # Add padding token if missing
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path if self.model_path else settings.BASE_MODEL_NAME,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            # Generation configuration
            self.generation_config = GenerationConfig(
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=1.1
            )
            
            self.is_model_loaded = True
            print(f"✅ Model loaded for {self.agent_id}")
            
        except Exception as e:
            print(f"❌ Failed to load model for {self.agent_id}: {e}")
            print(f"⚠️  Agent {self.agent_id} will use fallback text generation")
            self.is_model_loaded = False
            
            # Set fallback model info
            self.model = None
            self.tokenizer = None
            self.generation_config = None
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate a response using the agent's personality model"""
        
        # Use API model if configured
        if self.use_api_model:
            return await self._generate_api_response(prompt, context or {})
        
        if not self.is_model_loaded:
            # Fallback response based on agent capabilities and context
            return await self._generate_fallback_response(prompt, context or {})
        
        try:
            # Build full prompt with context
            full_prompt = self._build_contextual_prompt(prompt, context or {})
            
            # Tokenize
            inputs = self.tokenizer(
                full_prompt, 
                return_tensors="pt",
                truncation=True,
                max_length=settings.MAX_CONTEXT_LENGTH
            )
            
            # Move to device if CUDA available
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    generation_config=self.generation_config,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response = self.tokenizer.decode(
                outputs[0][len(inputs['input_ids'][0]):], 
                skip_special_tokens=True
            ).strip()
            
            return response
            
        except Exception as e:
            print(f"❌ Generation error for {self.agent_id}: {e}")
            return f"[Generation error] I'm having trouble processing that request."
    
    def _build_contextual_prompt(self, prompt: str, context: Dict[str, Any]) -> str:
        """Build a prompt with agent personality and context"""
        
        # Load agent background context if available
        from digital_twin_backend.config.settings import AGENT_CONTEXTS
        agent_background = AGENT_CONTEXTS.get(self.agent_id, "")
        
        # Base personality context
        personality_context = f"""
You are {self.person_name}.
"""
        
        # Add detailed background if available
        if agent_background:
            personality_context += f"""
{agent_background}

Remember to respond authentically as {self.person_name} would based on your background and experience.
"""
        else:
            # Fallback to basic capabilities
            personality_context += f"""
Your characteristics:
- Technical skills: {json.dumps(self.capabilities.technical_skills)}
- Preferred tasks: {', '.join(self.capabilities.preferred_task_types)}
- Work style: {json.dumps(self.capabilities.work_style)}
- Communication style: {json.dumps(self.capabilities.communication_style)}
"""
        
        # Add current situation
        personality_context += f"""

Current situation:
- Current workload: {self.context.current_workload}/{self.context.max_capacity}
- Stress level: {self.context.stress_level:.1f}/1.0
- Available capacity: {1 - self.context.utilization:.1%}
"""
        
        # Add dynamic context
        if context.get('peer_info'):
            personality_context += f"\nTeam context:\n{context['peer_info']}\n"
        
        if context.get('task_info'):
            personality_context += f"\nTask under discussion:\n{context['task_info']}\n"
        
        return f"{personality_context}\n\nPlease respond as {self.person_name} would: {prompt}"
    
    async def _generate_api_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate response using API (OpenAI, Anthropic, etc.)"""
        try:
            from digital_twin_backend.config.settings import settings
            from digital_twin_backend.config.api_keys import api_key_manager
            
            # Get API key
            api_key = api_key_manager.get_key(self.api_provider)
            if not api_key:
                print(f"⚠️  No API key for {self.api_provider}, using fallback")
                return await self._generate_fallback_response(prompt, context)
            
            # Build contextual prompt
            full_prompt = self._build_contextual_prompt(prompt, context)
            
            # Call OpenAI API
            if self.api_provider == "openai":
                import openai
                
                client = openai.OpenAI(api_key=api_key)
                
                # Determine the actual model to use
                model_to_use = self.api_model
                
                # If it's an Assistant ID, retrieve the assistant to get the fine-tuned model
                if self.api_model.startswith('asst_'):
                    try:
                        assistant = client.beta.assistants.retrieve(self.api_model)
                        model_to_use = assistant.model
                        print(f"💡 Retrieved model from assistant: {model_to_use}")
                    except Exception as e:
                        print(f"⚠️  Could not retrieve assistant, will try Chat API directly: {e}")
                        # Fall back to using assistant_id as model (might fail but worth trying)
                        model_to_use = self.api_model
                
                # Try Chat Completions API first (works with fine-tuned models)
                try:
                    response = client.chat.completions.create(
                        model=model_to_use,
                        messages=[
                            {"role": "system", "content": f"You are {self.person_name}, a digital twin agent. Respond in character based on your personality and capabilities."},
                            {"role": "user", "content": full_prompt}
                        ],
                        max_tokens=500,
                        temperature=0.7
                    )
                    
                    return response.choices[0].message.content.strip()
                
                except Exception as chat_error:
                    # If Chat API fails and we have an assistant ID, try Assistants API as fallback
                    if self.api_model.startswith('asst_'):
                        print(f"⚠️  Chat API failed, trying Assistants API: {chat_error}")
                        return await self._use_assistants_api(client, full_prompt)
                    else:
                        raise chat_error
            
            # Add support for other providers (Anthropic, etc.) here
            else:
                print(f"⚠️  Provider {self.api_provider} not yet supported")
                return await self._generate_fallback_response(prompt, context)
                
        except ImportError:
            print(f"⚠️  OpenAI package not installed. Install with: pip install openai")
            return await self._generate_fallback_response(prompt, context)
        except Exception as e:
            print(f"❌ API error for {self.agent_id}: {e}")
            return await self._generate_fallback_response(prompt, context)
    
    async def _use_assistants_api(self, client, full_prompt: str) -> str:
        """Fallback: Use Assistants API when Chat Completions fails"""
        import time
        
        try:
            # Create thread
            thread = client.beta.threads.create()
            
            # Add message to thread
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=full_prompt
            )
            
            # Run the assistant
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.api_model
            )
            
            # Wait for completion
            max_wait = 30
            start_time = time.time()
            while run.status in ['queued', 'in_progress']:
                if time.time() - start_time > max_wait:
                    return f"[Timeout] Assistant took too long to respond."
                time.sleep(0.5)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                # Get the messages
                messages = client.beta.threads.messages.list(
                    thread_id=thread.id,
                    order='desc',
                    limit=1
                )
                return messages.data[0].content[0].text.value.strip()
            else:
                return f"[Error] Assistant run failed with status: {run.status}"
        
        except Exception as e:
            return f"[Assistants API Error] {str(e)}"
    
    async def _generate_fallback_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate fallback response when model is not available"""
        
        # Extract key information from prompt
        if "task" in prompt.lower():
            if any(skill in self.capabilities.technical_skills for skill in ["technical", "documentation"]):
                return f"Hi! I'd be happy to help with this task. Given my background in {', '.join(self.capabilities.technical_skills.keys())}, I think I can contribute effectively. Let me know if you need more details about my availability or approach."
            else:
                return f"Thanks for considering me for this task. I'd like to discuss the requirements in more detail to see how I can best contribute. What are the main priorities and timeline?"
        
        elif "negotiation" in prompt.lower() or "discuss" in prompt.lower():
            if self.capabilities.work_style.get("collaborative", False):
                return f"I appreciate being part of this discussion. Based on what I'm seeing, I think we should consider everyone's workload and expertise. What does the team think about the best approach here?"
            else:
                return f"Looking at this situation, here's my honest assessment of how we should proceed. I'm happy to take on tasks that match my skills, but I want to make sure we're making the best decision for the team."
        
        else:
            # Generic professional response
            return f"Thanks for reaching out! As {self.person_name}, I'm ready to contribute to the team's success. Could you provide more context about what you need from me?"
    
    async def send_message(self, recipient_id: str, content: str, message_type: str = "general") -> None:
        """Send a message to another agent"""
        message = {
            "from": self.agent_id,
            "to": recipient_id,
            "content": content,
            "message_type": message_type,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to conversation history
        self.conversation_history.append(message)
        
        # Send via shared knowledge system (Redis pub/sub or queue)
        await self._route_message(message)
    
    async def receive_message(self, message: Dict[str, Any]) -> None:
        """Receive and queue a message for processing"""
        await self.message_queue.put(message)
    
    async def _process_messages(self) -> None:
        """Background task to process incoming messages"""
        while self.is_active:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                
                # Process the message based on type
                if message["message_type"] == "task_consultation":
                    await self._handle_task_consultation(message)
                elif message["message_type"] == "negotiation":
                    await self._handle_negotiation_message(message)
                elif message["message_type"] == "general":
                    await self._handle_general_message(message)
                
                # Update last active time
                self.context.last_active = datetime.now()
                await self.shared_knowledge.update_agent_context(self.agent_id, self.context)
                
            except asyncio.TimeoutError:
                continue  # No messages, continue loop
            except Exception as e:
                print(f"❌ Message processing error for {self.agent_id}: {e}")
    
    async def _route_message(self, message: Dict[str, Any]) -> None:
        """Route message through shared knowledge system"""
        # In a full implementation, this would use Redis pub/sub
        # For now, we'll simulate direct delivery
        recipient_id = message["to"]
        
        # This would normally be handled by the communication protocol
        print(f"📨 {message['from']} -> {recipient_id}: {message['content'][:50]}...")
    
    # Task-related methods
    async def assess_task(self, task: TaskInfo) -> TaskAssessment:
        """Assess whether agent can handle a task (Phase 1)"""
        
        # Build context for task assessment
        context = {
            "task_info": {
                "title": task.title,
                "type": task.task_type,
                "priority": task.priority,
                "estimated_hours": task.estimated_hours,
                "required_skills": task.required_skills,
                "deadline": task.deadline.isoformat() if task.deadline else None
            },
            "agent_status": {
                "current_workload": self.context.current_workload,
                "max_capacity": self.context.max_capacity,
                "utilization": self.context.utilization,
                "stress_level": self.context.stress_level
            }
        }
        
        # Generate reasoning using personality model
        assessment_prompt = f"""
I've been asked to consider taking on this task: {task.title}

Task details:
- Type: {task.task_type}
- Priority: {task.priority}/10
- Estimated time: {task.estimated_hours} hours
- Required skills: {', '.join(task.required_skills)}
- Deadline: {task.deadline.strftime('%Y-%m-%d %H:%M') if task.deadline else 'None specified'}

My current situation:
- Workload: {self.context.current_workload}/{self.context.max_capacity} tasks
- Utilization: {self.context.utilization:.1%}
- Stress level: {self.context.stress_level:.1f}/1.0

Based on my skills, availability, and work style, should I take this task? 
Please provide your honest assessment including concerns and reasoning.
"""
        
        reasoning = await self.generate_response(assessment_prompt, context)
        
        # Parse response and create assessment
        # In a real implementation, you'd use more sophisticated parsing
        can_handle = self._can_handle_task(task)
        confidence = self._calculate_confidence(task)
        estimated_time = max(task.estimated_hours, task.estimated_hours * (1 + self.context.stress_level))
        concerns = self._identify_concerns(task)
        
        return TaskAssessment(
            can_handle=can_handle,
            confidence=confidence,
            estimated_time=estimated_time,
            concerns=concerns,
            reasoning=reasoning
        )
    
    async def participate_in_negotiation(
        self, 
        task: TaskInfo, 
        other_assessments: Dict[str, TaskAssessment]
    ) -> NegotiationMessage:
        """Participate in peer negotiation (Phase 2)"""
        
        # Get current team context
        peer_contexts = await self.shared_knowledge.get_all_agent_contexts()
        peer_capabilities = await self.shared_knowledge.get_agent_capabilities()
        
        # Build negotiation context
        negotiation_context = {
            "task_info": task.__dict__,
            "peer_assessments": {
                agent_id: {
                    "can_handle": assess.can_handle,
                    "confidence": assess.confidence,
                    "concerns": assess.concerns,
                    "estimated_time": assess.estimated_time
                }
                for agent_id, assess in other_assessments.items()
            },
            "peer_workloads": {
                agent_id: {
                    "utilization": context.utilization,
                    "stress_level": context.stress_level,
                    "current_tasks": len(context.current_tasks)
                }
                for agent_id, context in peer_contexts.items()
                if agent_id != self.agent_id
            }
        }
        
        negotiation_prompt = f"""
We're discussing who should take on the task: {task.title}

Here's what my colleagues said:
{self._format_peer_assessments(other_assessments)}

Team workload status:
{self._format_team_workloads(peer_contexts)}

Based on this information and my own assessment, I should contribute to the discussion.
Should I volunteer, suggest someone else, or ask for more information?
Please respond naturally as I would in a team discussion.
"""
        
        response_content = await self.generate_response(negotiation_prompt, negotiation_context)
        
        # Determine message type and recipients
        message_type = "negotiation_contribution"
        recipients = [aid for aid in other_assessments.keys() if aid != self.agent_id]
        
        return NegotiationMessage(
            from_agent=self.agent_id,
            to_agents=recipients,
            task_id=task.task_id,
            message_type=message_type,
            content=response_content,
            reasoning=f"Negotiation based on task fit and team workload",
            confidence=self._calculate_negotiation_confidence(task, other_assessments),
            timestamp=datetime.now()
        )
    
    # Helper methods
    def _can_handle_task(self, task: TaskInfo) -> bool:
        """Basic capability check"""
        # Check if agent has required skills
        for skill in task.required_skills:
            if skill not in self.capabilities.technical_skills:
                return False
            if self.capabilities.technical_skills[skill] < 0.5:  # Minimum threshold
                return False
        
        # Check availability
        if self.context.utilization >= 1.0:
            return False
        
        return True
    
    def _calculate_confidence(self, task: TaskInfo) -> float:
        """Calculate confidence in handling task"""
        if not task.required_skills:
            return 0.7  # Default confidence
        
        skill_confidences = []
        for skill in task.required_skills:
            skill_level = self.capabilities.technical_skills.get(skill, 0.0)
            skill_confidences.append(skill_level)
        
        avg_skill_confidence = sum(skill_confidences) / len(skill_confidences)
        
        # Adjust for workload
        availability_factor = 1.0 - self.context.stress_level
        
        return avg_skill_confidence * availability_factor
    
    def _identify_concerns(self, task: TaskInfo) -> List[str]:
        """Identify potential concerns with the task"""
        concerns = []
        
        if self.context.utilization > 0.8:
            concerns.append("High current workload")
        
        if task.deadline:
            time_pressure = (task.deadline - datetime.now()).total_seconds() / 3600
            if time_pressure < 24:
                concerns.append("Very tight deadline")
            elif time_pressure < 72:
                concerns.append("Short timeline")
        
        missing_skills = [
            skill for skill in task.required_skills 
            if skill not in self.capabilities.technical_skills or 
            self.capabilities.technical_skills[skill] < 0.6
        ]
        if missing_skills:
            concerns.append(f"Limited experience with: {', '.join(missing_skills)}")
        
        return concerns
    
    def _calculate_negotiation_confidence(self, task: TaskInfo, other_assessments: Dict[str, TaskAssessment]) -> float:
        """Calculate confidence in negotiation position"""
        my_assessment = asyncio.create_task(self.assess_task(task))
        # This is simplified - in reality you'd await the assessment
        return 0.7  # Placeholder
    
    def _format_peer_assessments(self, assessments: Dict[str, TaskAssessment]) -> str:
        """Format peer assessments for prompt"""
        formatted = []
        for agent_id, assessment in assessments.items():
            formatted.append(
                f"- {agent_id}: {'Can handle' if assessment.can_handle else 'Cannot handle'} "
                f"(confidence: {assessment.confidence:.1%}, estimated: {assessment.estimated_time:.1f}h)"
            )
        return '\n'.join(formatted)
    
    def _format_team_workloads(self, contexts: Dict[str, AgentContext]) -> str:
        """Format team workload information"""
        formatted = []
        for agent_id, context in contexts.items():
            if agent_id != self.agent_id:
                formatted.append(
                    f"- {agent_id}: {context.utilization:.1%} utilization, "
                    f"stress: {context.stress_level:.1f}/1.0"
                )
        return '\n'.join(formatted)
    
    # Abstract methods for subclasses
    @abstractmethod
    async def _handle_task_consultation(self, message: Dict[str, Any]) -> None:
        """Handle task consultation message"""
        pass
    
    @abstractmethod
    async def _handle_negotiation_message(self, message: Dict[str, Any]) -> None:
        """Handle negotiation message"""
        pass
    
    @abstractmethod
    async def _handle_general_message(self, message: Dict[str, Any]) -> None:
        """Handle general message"""
        pass
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the agent"""
        self.is_active = False
        print(f"🔄 Agent {self.agent_id} shutting down...")
