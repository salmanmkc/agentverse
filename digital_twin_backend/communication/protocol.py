"""
Agent Communication Protocol
Handles message routing, agent-to-agent communication, and system coordination
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as redis
from concurrent.futures import ThreadPoolExecutor

from communication.shared_knowledge import (
    SharedKnowledgeBase, 
    NegotiationMessage, 
    TaskInfo
)


class MessageType(Enum):
    TASK_CONSULTATION = "task_consultation"
    CONSULTATION_RESPONSE = "consultation_response"
    NEGOTIATION = "negotiation"
    NEGOTIATION_RESPONSE = "negotiation_response"
    TASK_ASSIGNMENT = "task_assignment"
    ASSIGNMENT_ACK = "assignment_acknowledgment"
    STATUS_REQUEST = "status_request"
    STATUS_RESPONSE = "status_response"
    GENERAL = "general"
    SYSTEM = "system"


class MessagePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Message:
    """Standard message format for agent communication"""
    id: str
    from_agent: str
    to_agent: str
    message_type: MessageType
    content: str
    metadata: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        
        # Set expiration based on message type
        if self.expires_at is None:
            if self.message_type in [MessageType.TASK_CONSULTATION, MessageType.NEGOTIATION]:
                self.expires_at = self.created_at + timedelta(minutes=30)
            else:
                self.expires_at = self.created_at + timedelta(hours=24)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission"""
        data = asdict(self)
        data['message_type'] = self.message_type.value
        data['priority'] = self.priority.value
        data['created_at'] = self.created_at.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        data = data.copy()
        data['message_type'] = MessageType(data['message_type'])
        data['priority'] = MessagePriority(data['priority'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


class AgentCommunicationProtocol:
    """Main communication protocol for digital twin agents"""
    
    def __init__(self, shared_knowledge: SharedKnowledgeBase, redis_url: str = "redis://localhost:6379"):
        self.shared_knowledge = shared_knowledge
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # Message routing
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.agent_handlers: Dict[str, Callable] = {}
        self.active_connections: Set[str] = set()
        
        # Background tasks
        self.message_router_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Performance tracking
        self.message_stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "avg_delivery_time": 0.0
        }
        
        # Executor for CPU-bound tasks
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def initialize(self) -> None:
        """Initialize the communication protocol"""
        try:
            # Connect to Redis for message persistence and pub/sub
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            print("✅ Communication protocol connected to Redis")
            
            # Start background tasks
            self.is_running = True
            self.message_router_task = asyncio.create_task(self._message_router())
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
            
            print("✅ Communication protocol initialized")
            
        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            print("📝 Using in-memory message routing (no persistence)")
            self.redis_client = None
            
            # Still start background tasks for in-memory routing
            self.is_running = True
            self.message_router_task = asyncio.create_task(self._message_router())
    
    async def register_agent(self, agent_id: str, message_handler: Callable) -> None:
        """Register an agent with the communication protocol"""
        
        # Create message queue for agent
        self.message_queues[agent_id] = asyncio.Queue(maxsize=100)
        self.agent_handlers[agent_id] = message_handler
        self.active_connections.add(agent_id)
        
        # Subscribe to Redis channel for this agent
        if self.redis_client:
            await self.redis_client.subscribe(f"agent:{agent_id}")
        
        print(f"📡 Agent {agent_id} registered with communication protocol")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent"""
        
        if agent_id in self.message_queues:
            del self.message_queues[agent_id]
        
        if agent_id in self.agent_handlers:
            del self.agent_handlers[agent_id]
        
        if agent_id in self.active_connections:
            self.active_connections.remove(agent_id)
        
        # Unsubscribe from Redis
        if self.redis_client:
            await self.redis_client.unsubscribe(f"agent:{agent_id}")
        
        print(f"📡 Agent {agent_id} unregistered from communication protocol")
    
    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: MessageType,
        content: str,
        metadata: Dict[str, Any] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> bool:
        """Send a message from one agent to another"""
        
        # Generate unique message ID
        message_id = f"msg_{from_agent}_{to_agent}_{int(time.time() * 1000)}"
        
        # Create message
        message = Message(
            id=message_id,
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            priority=priority
        )
        
        try:
            # Route message
            success = await self._route_message(message)
            
            # Update stats
            if success:
                self.message_stats["total_sent"] += 1
                self.message_stats["total_delivered"] += 1
            else:
                self.message_stats["total_failed"] += 1
            
            # Store in Redis for persistence
            if self.redis_client:
                await self._store_message_history(message)
            
            return success
            
        except Exception as e:
            print(f"❌ Failed to send message {message_id}: {e}")
            self.message_stats["total_failed"] += 1
            return False
    
    async def broadcast_message(
        self,
        from_agent: str,
        recipient_agents: List[str],
        message_type: MessageType,
        content: str,
        metadata: Dict[str, Any] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Dict[str, bool]:
        """Broadcast a message to multiple agents"""
        
        results = {}
        
        # Send to each recipient
        send_tasks = []
        for recipient in recipient_agents:
            if recipient != from_agent:  # Don't send to self
                task = self.send_message(
                    from_agent=from_agent,
                    to_agent=recipient,
                    message_type=message_type,
                    content=content,
                    metadata=metadata,
                    priority=priority
                )
                send_tasks.append((recipient, task))
        
        # Wait for all sends to complete
        for recipient, task in send_tasks:
            try:
                success = await task
                results[recipient] = success
            except Exception as e:
                print(f"❌ Broadcast failed to {recipient}: {e}")
                results[recipient] = False
        
        return results
    
    async def _route_message(self, message: Message) -> bool:
        """Route message to the appropriate agent"""
        
        recipient = message.to_agent
        
        # Check if recipient is registered
        if recipient not in self.active_connections:
            print(f"⚠️  Recipient {recipient} not connected")
            return False
        
        # Check if message has expired
        if message.expires_at and datetime.now() > message.expires_at:
            print(f"⚠️  Message {message.id} expired")
            return False
        
        try:
            # Add to recipient's queue
            queue = self.message_queues[recipient]
            
            # Handle queue overflow based on priority
            if queue.full():
                if message.priority in [MessagePriority.HIGH, MessagePriority.URGENT]:
                    # Remove lowest priority message to make room
                    try:
                        queue.get_nowait()  # Remove old message
                    except asyncio.QueueEmpty:
                        pass
                else:
                    print(f"⚠️  Message queue full for {recipient}, dropping message")
                    return False
            
            # Add message to queue
            await queue.put(message)
            
            # Notify via Redis if available
            if self.redis_client:
                await self.redis_client.publish(
                    f"agent:{recipient}",
                    json.dumps(message.to_dict())
                )
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to route message to {recipient}: {e}")
            return False
    
    async def _message_router(self) -> None:
        """Background task to route messages to agent handlers"""
        
        while self.is_running:
            try:
                # Process messages for each active agent
                for agent_id in list(self.active_connections):
                    if agent_id not in self.message_queues:
                        continue
                    
                    queue = self.message_queues[agent_id]
                    handler = self.agent_handlers.get(agent_id)
                    
                    if not handler:
                        continue
                    
                    # Process available messages (non-blocking)
                    try:
                        while not queue.empty():
                            message = await asyncio.wait_for(queue.get(), timeout=0.1)
                            
                            # Track delivery time
                            delivery_time = (datetime.now() - message.created_at).total_seconds()
                            self._update_delivery_time_stats(delivery_time)
                            
                            # Call agent handler in background
                            asyncio.create_task(self._handle_message_delivery(handler, message))
                            
                    except asyncio.TimeoutError:
                        continue  # No messages available
                
                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Message router error: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message_delivery(self, handler: Callable, message: Message) -> None:
        """Handle message delivery to agent"""
        
        try:
            # Convert message to format expected by agent
            message_dict = {
                "id": message.id,
                "from": message.from_agent,
                "to": message.to_agent,
                "message_type": message.message_type.value,
                "content": message.content,
                "metadata": message.metadata,
                "created_at": message.created_at.isoformat(),
                "priority": message.priority.value
            }
            
            # Call agent's message handler
            await handler(message_dict)
            
        except Exception as e:
            print(f"❌ Message delivery failed: {e}")
    
    async def _store_message_history(self, message: Message) -> None:
        """Store message in Redis for history/debugging"""
        
        if not self.redis_client:
            return
        
        try:
            # Store message data
            message_key = f"message:{message.id}"
            await self.redis_client.hset(message_key, mapping=message.to_dict())
            
            # Set expiration (keep for 24 hours)
            await self.redis_client.expire(message_key, 86400)
            
            # Add to conversation thread
            thread_key = f"thread:{message.from_agent}:{message.to_agent}"
            await self.redis_client.lpush(thread_key, message.id)
            await self.redis_client.expire(thread_key, 86400)
            
        except Exception as e:
            print(f"⚠️  Failed to store message history: {e}")
    
    async def _cleanup_expired_messages(self) -> None:
        """Background task to clean up expired messages"""
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Clean up message queues
                for agent_id, queue in self.message_queues.items():
                    cleaned_messages = []
                    
                    # Extract all messages
                    while not queue.empty():
                        try:
                            message = queue.get_nowait()
                            if message.expires_at is None or current_time < message.expires_at:
                                cleaned_messages.append(message)
                            else:
                                print(f"🧹 Cleaned expired message {message.id}")
                        except asyncio.QueueEmpty:
                            break
                    
                    # Put back non-expired messages
                    for message in cleaned_messages:
                        try:
                            queue.put_nowait(message)
                        except asyncio.QueueFull:
                            break  # Queue is full, skip remaining
                
                # Sleep for 5 minutes before next cleanup
                await asyncio.sleep(300)
                
            except Exception as e:
                print(f"❌ Message cleanup error: {e}")
                await asyncio.sleep(60)
    
    def _update_delivery_time_stats(self, delivery_time: float) -> None:
        """Update average delivery time statistics"""
        
        current_avg = self.message_stats["avg_delivery_time"]
        total_delivered = self.message_stats["total_delivered"]
        
        if total_delivered == 0:
            self.message_stats["avg_delivery_time"] = delivery_time
        else:
            # Rolling average
            self.message_stats["avg_delivery_time"] = (
                (current_avg * (total_delivered - 1)) + delivery_time
            ) / total_delivered
    
    # Utility methods for agents
    async def get_conversation_history(
        self, 
        agent1: str, 
        agent2: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history between two agents"""
        
        if not self.redis_client:
            return []
        
        try:
            # Get thread messages
            thread_key = f"thread:{agent1}:{agent2}"
            reverse_thread_key = f"thread:{agent2}:{agent1}"
            
            # Get message IDs from both directions
            message_ids = []
            message_ids.extend(await self.redis_client.lrange(thread_key, 0, limit // 2))
            message_ids.extend(await self.redis_client.lrange(reverse_thread_key, 0, limit // 2))
            
            # Get message details
            messages = []
            for msg_id in message_ids[:limit]:
                message_data = await self.redis_client.hgetall(f"message:{msg_id}")
                if message_data:
                    messages.append(message_data)
            
            # Sort by timestamp
            messages.sort(key=lambda x: x.get('created_at', ''))
            
            return messages
            
        except Exception as e:
            print(f"❌ Failed to get conversation history: {e}")
            return []
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get communication status for an agent"""
        
        queue_size = 0
        if agent_id in self.message_queues:
            queue_size = self.message_queues[agent_id].qsize()
        
        return {
            "agent_id": agent_id,
            "connected": agent_id in self.active_connections,
            "queue_size": queue_size,
            "queue_max": 100,
            "has_handler": agent_id in self.agent_handlers
        }
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide communication statistics"""
        
        return {
            "active_agents": len(self.active_connections),
            "total_queues": len(self.message_queues),
            "message_stats": self.message_stats.copy(),
            "redis_connected": self.redis_client is not None,
            "system_uptime": datetime.now().isoformat(),
            "is_running": self.is_running
        }
    
    # Specialized methods for agent coordination
    async def initiate_task_negotiation(
        self,
        task: TaskInfo,
        participating_agents: List[str],
        manager_id: str = "manager"
    ) -> str:
        """Initiate a task negotiation session"""
        
        negotiation_id = f"negotiation_{task.task_id}_{int(time.time())}"
        
        # Create negotiation metadata
        negotiation_metadata = {
            "negotiation_id": negotiation_id,
            "task_id": task.task_id,
            "participants": participating_agents,
            "initiated_by": manager_id,
            "started_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Send negotiation start message to all participants
        start_message = f"Starting negotiation for task: {task.title}"
        
        await self.broadcast_message(
            from_agent=manager_id,
            recipient_agents=participating_agents,
            message_type=MessageType.NEGOTIATION,
            content=start_message,
            metadata=negotiation_metadata,
            priority=MessagePriority.HIGH
        )
        
        return negotiation_id
    
    async def end_negotiation(
        self,
        negotiation_id: str,
        final_assignment: str,
        manager_id: str = "manager"
    ) -> None:
        """End a negotiation session and announce results"""
        
        # This would retrieve participants from stored negotiation metadata
        # For now, broadcast to all active agents
        
        end_message = f"Negotiation {negotiation_id} concluded. Task assigned to {final_assignment}."
        
        await self.broadcast_message(
            from_agent=manager_id,
            recipient_agents=list(self.active_connections),
            message_type=MessageType.SYSTEM,
            content=end_message,
            metadata={
                "negotiation_id": negotiation_id,
                "final_assignment": final_assignment,
                "concluded_at": datetime.now().isoformat()
            }
        )
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the communication protocol"""
        
        print("🔄 Shutting down communication protocol...")
        
        self.is_running = False
        
        # Cancel background tasks
        if self.message_router_task:
            self.message_router_task.cancel()
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        print("✅ Communication protocol shutdown complete")


# Global instance
communication_protocol = AgentCommunicationProtocol(None)  # Will be initialized with shared_knowledge
