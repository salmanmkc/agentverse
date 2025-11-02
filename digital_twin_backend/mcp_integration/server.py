"""
Digital Twin MCP Server (stdio)
--------------------------------
Exposes tools via the Model Context Protocol (MCP) to control the
Digital Twin Workplace backend without the FastAPI layer.

Tools:
System Management:
- initialize_system()
- get_system_status()

Task Management:
- create_task(title, description, task_type, priority, estimated_hours, deadline?, required_skills?)
- get_tasks(status?)
- get_task(task_id)
- assign_task(task_id, agent_id?)
- update_task_status(task_id, status)

Agent Management:
- get_agents()
- get_agent_status(agent_id)
- get_agent_directory()
- update_agent_name(agent_id, person_name)

Model Management:
- list_available_models()
- get_agent_model_info(agent_id)
- update_agent_model(agent_id, model_path, reload=True)
- configure_agent(agent_id, person_name?, model_path?, capabilities?)
- reload_agent_model(agent_id)
- set_base_model(base_model_name)

API Key Management:
- add_api_key(provider, api_key, label?)
- list_api_keys()
- remove_api_key(provider)
- validate_api_key(provider)
- get_api_key_status(provider)
- configure_agent_with_api(agent_id, provider, model_name, person_name?)
- list_supported_api_providers()

Run:
  pip install mcp
  python -m digital_twin_backend.mcp_integration.server

Notes:
- Works in-memory by default; if Redis is running, shared knowledge and
  protocol will use it automatically per settings.
- Does not require FastAPI/Uvicorn.
- Model management functions allow hot-swapping agent personalities
"""
import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

# Prefer the official MCP Python SDK if available
# Note: Must use 'from mcp.server import FastMCP' not 'from mcp.server.fastmcp'
try:
    from mcp.server import FastMCP
    MCP_IMPL = "fastmcp"
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
        MCP_IMPL = "fastmcp"
    except Exception:  # pragma: no cover
        FastMCP = None
        MCP_IMPL = None

from digital_twin_backend.communication.shared_knowledge import (
    SharedKnowledgeBase,
    TaskInfo,
    TaskStatus,
    AgentStatus,
    AgentCapabilities,
)
from digital_twin_backend.communication.protocol import AgentCommunicationProtocol
from digital_twin_backend.agents.manager_agent import ManagerAgent
from digital_twin_backend.agents.worker_agent import WorkerAgent
from digital_twin_backend.config.settings import settings, AGENT_CONFIGS
from digital_twin_backend.config.api_keys import api_key_manager


# --- Global runtime state for the MCP server ---
class ServerState:
    def __init__(self) -> None:
        self.shared: Optional[SharedKnowledgeBase] = None
        self.protocol: Optional[AgentCommunicationProtocol] = None
        self.manager: Optional[ManagerAgent] = None
        self.workers: Dict[str, WorkerAgent] = {}
        self.initialized: bool = False

    async def initialize(self) -> Dict[str, Any]:
        if self.initialized:
            return {"message": "System already initialized", "status": "success"}

        self.shared = SharedKnowledgeBase()
        await self.shared.initialize()

        self.protocol = AgentCommunicationProtocol(self.shared)
        await self.protocol.initialize()

        # Manager
        self.manager = ManagerAgent(shared_knowledge=self.shared, worker_agent_ids=settings.WORKER_AGENT_IDS)
        await self.manager.initialize()
        await self.protocol.register_agent("manager", self.manager.receive_message)

        # Workers
        self.workers = {}
        for agent_id in settings.WORKER_AGENT_IDS:
            cfg = AGENT_CONFIGS.get(agent_id)
            if not cfg:
                continue
            caps = AgentCapabilities(technical_skills=cfg.capabilities)
            worker = WorkerAgent(
                agent_id=agent_id,
                person_name=cfg.person_name,
                shared_knowledge=self.shared,
                capabilities=caps,
                model_path=cfg.model_path if cfg.fine_tuned else None,
            )
            await worker.initialize()
            self.workers[agent_id] = worker
            await self.protocol.register_agent(agent_id, worker.receive_message)

        self.initialized = True
        return {
            "message": "System initialized successfully",
            "status": "success",
            "agents": {"manager": "manager", "workers": list(self.workers.keys())},
        }

    async def shutdown(self) -> None:
        # Graceful shutdown
        try:
            if self.protocol:
                await self.protocol.shutdown()
        finally:
            if self.shared:
                await self.shared.close()
        self.initialized = False


STATE = ServerState()


def _serialize_task(task: TaskInfo) -> Dict[str, Any]:
    return {
        "task_id": task.task_id,
        "title": task.title,
        "description": task.description,
        "task_type": task.task_type,
        "priority": task.priority,
        "estimated_hours": task.estimated_hours,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "required_skills": task.required_skills,
        "dependencies": task.dependencies,
        "created_at": task.created_at.isoformat(),
        "status": task.status.value,
        "assigned_agent": STATE.shared.task_assignments.get(task.task_id) if STATE.shared else None,
    }


def _agent_directory() -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    if STATE.manager is not None:
        items.append({"agent_id": "manager", "person_name": STATE.manager.person_name, "role": "manager"})
    for aid, agent in STATE.workers.items():
        items.append({"agent_id": aid, "person_name": agent.person_name, "role": "worker"})
    return {
        "total_agents": len(items),
        "total_workers": len(STATE.workers),
        "agents": items,
        "last_updated": datetime.now().isoformat(),
    }


def _persist_agent_names() -> None:
    """Persist current agent names to data/agent_profiles.json (best-effort)."""
    try:
        from pathlib import Path

        path = Path(__file__).resolve().parents[1] / "data" / "agent_profiles.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        mapping: Dict[str, str] = {}
        if STATE.manager is not None:
            mapping["manager"] = STATE.manager.person_name
        for aid, agent in STATE.workers.items():
            mapping[aid] = agent.person_name
        path.write_text(json.dumps(mapping, indent=2))
    except Exception:
        pass


async def ensure_initialized() -> None:
    if not STATE.initialized:
        await STATE.initialize()


def create_app() -> FastMCP:
    if FastMCP is None:
        raise RuntimeError(
            "The 'mcp' package is required. Install with: pip install mcp"
        )

    app = FastMCP("digital-twin-mcp")

    @app.tool()
    async def initialize_system() -> Dict[str, Any]:
        """Initialize shared knowledge, communication protocol, manager and workers."""
        return await STATE.initialize()

    @app.tool()
    async def get_system_status() -> Dict[str, Any]:
        """Return overall system status with agent/task counts."""
        await ensure_initialized()
        shared = STATE.shared
        # Task counts
        tasks = list(shared.tasks.values()) if shared else []
        pending = len([t for t in tasks if t.status == TaskStatus.PENDING])
        in_progress = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
        completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        # Agent counts
        agent_contexts = await shared.get_all_agent_contexts()
        active_agents = len([c for c in agent_contexts.values() if c.availability_status != AgentStatus.OFFLINE])
        return {
            "total_agents": len(STATE.workers),
            "active_agents": active_agents,
            "pending_tasks": pending,
            "in_progress_tasks": in_progress,
            "completed_tasks": completed,
            "system_uptime": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }

    @app.tool()
    async def create_task(
        title: str,
        description: str,
        task_type: str,
        priority: int,
        estimated_hours: float,
        deadline: Optional[str] = None,
        required_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a task and synchronously run distribution via the manager."""
        await ensure_initialized()
        shared = STATE.shared
        # Construct TaskInfo
        task_id = f"task_{int(datetime.now().timestamp() * 1000)}"
        dt = datetime.fromisoformat(deadline) if deadline else None
        task = TaskInfo(
            task_id=task_id,
            title=title,
            description=description,
            task_type=task_type,
            priority=int(priority),
            estimated_hours=float(estimated_hours),
            deadline=dt,
            required_skills=required_skills or [],
            dependencies=[],
            created_at=datetime.now(),
            status=TaskStatus.PENDING,
        )
        # Add and distribute
        await shared.add_task(task)
        result = await STATE.manager.distribute_task(task)
        return {"task": _serialize_task(task), "distribution": result}

    @app.tool()
    async def get_tasks(status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status (pending|assigned|in_progress|completed|cancelled)."""
        await ensure_initialized()
        shared = STATE.shared
        tasks = list(shared.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status.value == status]
        return [_serialize_task(t) for t in tasks]

    @app.tool()
    async def get_task(task_id: str) -> Dict[str, Any]:
        await ensure_initialized()
        task = await STATE.shared.get_task(task_id)
        if not task:
            return {"error": "Task not found", "task_id": task_id}
        return _serialize_task(task)

    @app.tool()
    async def assign_task(task_id: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Assign a task to a specific agent or trigger automatic distribution."""
        await ensure_initialized()
        task = await STATE.shared.get_task(task_id)
        if not task:
            return {"error": "Task not found", "task_id": task_id}
        if agent_id:
            if agent_id not in STATE.workers:
                return {"error": "Invalid agent ID", "agent_id": agent_id}
            await STATE.shared.assign_task(task_id, agent_id, "Manual assignment via MCP")
            task = await STATE.shared.get_task(task_id)
            return {"message": "Assigned", "task": _serialize_task(task)}
        # Automatic distribution
        result = await STATE.manager.distribute_task(task)
        task = await STATE.shared.get_task(task_id)
        return {"message": "Distributed", "task": _serialize_task(task), "distribution": result}

    @app.tool()
    async def update_task_status(task_id: str, status: str) -> Dict[str, Any]:
        await ensure_initialized()
        task = await STATE.shared.get_task(task_id)
        if not task:
            return {"error": "Task not found", "task_id": task_id}
        try:
            task.status = TaskStatus(status)
            await STATE.shared.add_task(task)
            return {"message": "Updated", "task": _serialize_task(task)}
        except ValueError:
            return {"error": "Invalid status", "status": status}

    @app.tool()
    async def get_agents() -> List[Dict[str, Any]]:
        await ensure_initialized()
        results = []
        for _, agent in STATE.workers.items():
            status = await agent.get_current_status()
            results.append(status)
        return results

    @app.tool()
    async def get_agent_status(agent_id: str) -> Dict[str, Any]:
        await ensure_initialized()
        if agent_id not in STATE.workers:
            return {"error": "Agent not found", "agent_id": agent_id}
        return await STATE.workers[agent_id].get_current_status()

    @app.tool()
    async def get_agent_directory() -> Dict[str, Any]:
        await ensure_initialized()
        return _agent_directory()

    @app.tool()
    async def update_agent_name(agent_id: str, person_name: str) -> Dict[str, Any]:
        await ensure_initialized()
        person_name = (person_name or "").strip()
        if not person_name:
            return {"error": "Name cannot be empty"}
        if agent_id == "manager":
            if STATE.manager is None:
                return {"error": "Manager not available"}
            STATE.manager.person_name = person_name
        elif agent_id in STATE.workers:
            STATE.workers[agent_id].person_name = person_name
        else:
            return {"error": "Agent not found", "agent_id": agent_id}
        # Update config snapshot as best effort
        if agent_id in AGENT_CONFIGS:
            try:
                AGENT_CONFIGS[agent_id].person_name = person_name
            except Exception:
                pass
        _persist_agent_names()
        return {"message": "Renamed", "agent_id": agent_id, "person_name": person_name}

    @app.tool()
    async def list_available_models() -> Dict[str, Any]:
        """List all trained models in the models directory."""
        from pathlib import Path
        
        models_dir = Path(settings.MODELS_DIR)
        if not models_dir.exists():
            return {"models": [], "models_dir": str(models_dir), "message": "Models directory not found"}
        
        models = []
        for model_dir in models_dir.iterdir():
            if model_dir.is_dir() and not model_dir.name.startswith('.'):
                model_info = {
                    "name": model_dir.name,
                    "path": str(model_dir),
                    "has_config": (model_dir / "config.json").exists(),
                    "has_adapter": (model_dir / "adapter_model.bin").exists() or (model_dir / "adapter_model.safetensors").exists(),
                    "has_tokenizer": (model_dir / "tokenizer.json").exists() or (model_dir / "tokenizer_config.json").exists(),
                    "size_mb": sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file()) / (1024 * 1024)
                }
                models.append(model_info)
        
        return {
            "models": models,
            "total": len(models),
            "models_dir": str(models_dir)
        }

    @app.tool()
    async def get_agent_model_info(agent_id: str) -> Dict[str, Any]:
        """Get detailed model information for an agent."""
        await ensure_initialized()
        
        if agent_id == "manager":
            agent = STATE.manager
        elif agent_id in STATE.workers:
            agent = STATE.workers[agent_id]
        else:
            return {"error": "Agent not found", "agent_id": agent_id}
        
        return {
            "agent_id": agent_id,
            "person_name": agent.person_name,
            "model_path": agent.model_path,
            "model_loaded": agent.is_model_loaded,
            "has_fine_tuned_model": agent.model_path is not None,
            "using_fallback": not agent.is_model_loaded,
            "capabilities": agent.capabilities.technical_skills if hasattr(agent.capabilities, 'technical_skills') else {}
        }

    @app.tool()
    async def update_agent_model(
        agent_id: str,
        model_path: str,
        reload: bool = True
    ) -> Dict[str, Any]:
        """Update the model path for a specific agent and optionally reload it."""
        await ensure_initialized()
        
        if agent_id == "manager":
            return {"error": "Cannot update manager model via this method", "agent_id": agent_id}
        
        if agent_id not in STATE.workers:
            return {"error": "Agent not found", "agent_id": agent_id}
        
        from pathlib import Path
        model_path_obj = Path(model_path)
        
        # Validate model path exists
        if not model_path_obj.exists():
            return {"error": "Model path does not exist", "model_path": model_path}
        
        agent = STATE.workers[agent_id]
        old_model_path = agent.model_path
        
        # Update model path
        agent.model_path = model_path
        
        # Reload model if requested
        load_success = False
        if reload:
            try:
                await agent.load_model()
                load_success = agent.is_model_loaded
            except Exception as e:
                return {
                    "error": f"Failed to load model: {str(e)}",
                    "agent_id": agent_id,
                    "model_path": model_path
                }
        
        # Update config
        if agent_id in AGENT_CONFIGS:
            AGENT_CONFIGS[agent_id].model_path = model_path
            AGENT_CONFIGS[agent_id].fine_tuned = True
        
        return {
            "message": f"Model updated for {agent.person_name}",
            "agent_id": agent_id,
            "old_model_path": old_model_path,
            "new_model_path": model_path,
            "model_loaded": load_success,
            "reload_attempted": reload
        }

    @app.tool()
    async def configure_agent(
        agent_id: str,
        person_name: Optional[str] = None,
        model_path: Optional[str] = None,
        capabilities: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Configure an agent's name, model, and capabilities all at once."""
        await ensure_initialized()
        
        if agent_id not in STATE.workers:
            return {"error": "Agent not found", "agent_id": agent_id}
        
        agent = STATE.workers[agent_id]
        updates = {}
        
        # Update person name
        if person_name:
            person_name = person_name.strip()
            if person_name:
                agent.person_name = person_name
                updates["person_name"] = person_name
        
        # Update model
        if model_path:
            from pathlib import Path
            if Path(model_path).exists():
                agent.model_path = model_path
                try:
                    await agent.load_model()
                    updates["model_path"] = model_path
                    updates["model_loaded"] = agent.is_model_loaded
                except Exception as e:
                    updates["model_error"] = str(e)
            else:
                updates["model_error"] = "Model path does not exist"
        
        # Update capabilities
        if capabilities:
            agent.capabilities.technical_skills.update(capabilities)
            await STATE.shared.register_agent(agent_id, agent.capabilities)
            updates["capabilities"] = capabilities
        
        # Persist changes to config
        if agent_id in AGENT_CONFIGS:
            if person_name:
                AGENT_CONFIGS[agent_id].person_name = person_name
            if model_path and Path(model_path).exists():
                AGENT_CONFIGS[agent_id].model_path = model_path
                AGENT_CONFIGS[agent_id].fine_tuned = True
            if capabilities:
                AGENT_CONFIGS[agent_id].capabilities.update(capabilities)
        
        _persist_agent_names()
        
        return {
            "message": f"Agent {agent_id} configured successfully",
            "agent_id": agent_id,
            "updates": updates
        }

    @app.tool()
    async def reload_agent_model(agent_id: str) -> Dict[str, Any]:
        """Reload an agent's model from disk."""
        await ensure_initialized()
        
        if agent_id not in STATE.workers:
            return {"error": "Agent not found", "agent_id": agent_id}
        
        agent = STATE.workers[agent_id]
        
        if not agent.model_path:
            return {
                "error": "No model path configured for this agent",
                "agent_id": agent_id,
                "person_name": agent.person_name
            }
        
        try:
            await agent.load_model()
            return {
                "message": f"Model reloaded for {agent.person_name}",
                "agent_id": agent_id,
                "model_path": agent.model_path,
                "model_loaded": agent.is_model_loaded
            }
        except Exception as e:
            return {
                "error": f"Failed to reload model: {str(e)}",
                "agent_id": agent_id,
                "model_path": agent.model_path
            }

    @app.tool()
    async def set_base_model(base_model_name: str) -> Dict[str, Any]:
        """Set the base model for future training operations."""
        settings.BASE_MODEL_NAME = base_model_name
        
        # Update environment variable for persistence
        import os
        os.environ["BASE_MODEL_NAME"] = base_model_name
        
        return {
            "message": "Base model updated",
            "base_model": base_model_name,
            "note": "This affects new training operations. Existing models unchanged."
        }

    # ============= API Key Management Functions =============
    
    @app.tool()
    async def add_api_key(provider: str, api_key: str, label: Optional[str] = None) -> Dict[str, Any]:
        """Add or update an API key for a provider (openai, anthropic, huggingface, etc.)."""
        result = api_key_manager.add_key(provider, api_key, label)
        return result
    
    @app.tool()
    async def list_api_keys() -> Dict[str, Any]:
        """List all configured API keys (masked for security)."""
        keys = api_key_manager.list_keys()
        return {
            "api_keys": keys,
            "total": len(keys),
            "supported_providers": api_key_manager.SUPPORTED_PROVIDERS
        }
    
    @app.tool()
    async def remove_api_key(provider: str) -> Dict[str, Any]:
        """Remove an API key for a provider."""
        result = api_key_manager.remove_key(provider)
        return result
    
    @app.tool()
    async def validate_api_key(provider: str) -> Dict[str, Any]:
        """Validate an API key by testing it with the provider."""
        result = api_key_manager.validate_key(provider)
        return result
    
    @app.tool()
    async def get_api_key_status(provider: str) -> Dict[str, Any]:
        """Check if an API key exists and is configured for a provider."""
        has_key = api_key_manager.has_key(provider)
        
        if has_key:
            keys = api_key_manager.list_keys()
            key_info = next((k for k in keys if k["provider"] == provider), None)
            return {
                "provider": provider,
                "has_key": True,
                "key_info": key_info
            }
        else:
            return {
                "provider": provider,
                "has_key": False,
                "message": f"No API key configured for {provider}"
            }
    
    @app.tool()
    async def configure_agent_with_api(
        agent_id: str,
        provider: str,
        model_name: str,
        person_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Configure an agent to use an API-based model instead of local fine-tuned model."""
        await ensure_initialized()
        
        if agent_id not in STATE.workers:
            return {"error": "Agent not found", "agent_id": agent_id}
        
        # Check if API key exists
        if not api_key_manager.has_key(provider):
            return {
                "error": f"No API key configured for {provider}",
                "message": f"Use add_api_key('{provider}', 'your-key') first"
            }
        
        agent = STATE.workers[agent_id]
        
        # Update agent configuration
        updates = {}
        
        if person_name:
            agent.person_name = person_name.strip()
            updates["person_name"] = agent.person_name
        
        # Store API provider info in agent metadata
        agent.metadata = getattr(agent, 'metadata', {})
        agent.metadata['use_api'] = True
        agent.metadata['api_provider'] = provider
        agent.metadata['api_model'] = model_name
        
        # Set model_path to indicate API usage
        agent.model_path = f"api://{provider}/{model_name}"
        agent.is_model_loaded = True  # Mark as loaded (uses API)
        
        updates["api_provider"] = provider
        updates["api_model"] = model_name
        updates["model_type"] = "api"
        
        return {
            "message": f"Agent {agent_id} configured to use {provider} API",
            "agent_id": agent_id,
            "person_name": agent.person_name,
            "updates": updates
        }
    
    @app.tool()
    async def list_supported_api_providers() -> Dict[str, Any]:
        """List all supported API providers for cloud-based models."""
        
        providers_info = {
            "openai": {
                "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                "description": "OpenAI GPT models"
            },
            "anthropic": {
                "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
                "description": "Anthropic Claude models"
            },
            "huggingface": {
                "models": ["any HuggingFace model"],
                "description": "HuggingFace Hub models"
            },
            "cohere": {
                "models": ["command", "command-light"],
                "description": "Cohere language models"
            },
            "groq": {
                "models": ["llama3-70b", "mixtral-8x7b"],
                "description": "Groq ultra-fast inference"
            },
            "together": {
                "models": ["various open-source models"],
                "description": "Together AI platform"
            }
        }
        
        return {
            "supported_providers": api_key_manager.SUPPORTED_PROVIDERS,
            "total": len(api_key_manager.SUPPORTED_PROVIDERS),
            "provider_details": providers_info
        }

    return app


def main() -> None:
    if MCP_IMPL != "fastmcp":  # pragma: no cover
        raise SystemExit(
            "The 'mcp' package is required to run this server.\n"
            "Install it with: pip install mcp\n"
            "Then run: python -m digital_twin_backend.mcp.server"
        )
    app = create_app()
    # Run stdio server (blocks)
    app.run()


if __name__ == "__main__":
    main()

