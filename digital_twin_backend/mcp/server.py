"""
Digital Twin MCP Server (stdio)
--------------------------------
Exposes tools via the Model Context Protocol (MCP) to control the
Digital Twin Workplace backend without the FastAPI layer.

Tools:
- initialize_system()
- get_system_status()
- create_task(title, description, task_type, priority, estimated_hours, deadline?, required_skills?)
- get_tasks(status?)
- get_task(task_id)
- assign_task(task_id, agent_id?)
- update_task_status(task_id, status)
- get_agents()
- get_agent_status(agent_id)
- get_agent_directory()
- update_agent_name(agent_id, person_name)

Run:
  pip install mcp
  python -m digital_twin_backend.mcp.server

Notes:
- Works in-memory by default; if Redis is running, shared knowledge and
  protocol will use it automatically per settings.
- Does not require FastAPI/Uvicorn.
"""
import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

# Prefer the official MCP Python SDK if available
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

