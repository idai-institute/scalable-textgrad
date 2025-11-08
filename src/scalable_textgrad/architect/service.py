"""FastAPI service implementing the Architect endpoints."""

from __future__ import annotations

import asyncio
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..codex_client import CodexRunner, CodexError
from ..config import AgentDirectories, AgentSettings, resolve_workspace
from ..logging_utils import configure_logging, log_event
from ..state_manager import StateManager

app = FastAPI(title="Architect Service", version="0.1.0")


class StartAgentRequest(BaseModel):
    agent_name: str = Field(default="ROOT", description="Name of the agent workspace")
    description: str = Field(..., description="High-level description of the system")


class StartAgentResponse(BaseModel):
    workspace: str
    agent_name: str


class ArchitectChatRequest(BaseModel):
    message: str


class ArchitectChatResponse(BaseModel):
    result: str


class ArchitectService:
    def __init__(self) -> None:
        self.settings = AgentSettings()
        self.codex = CodexRunner(self.settings)
        self.logger = configure_logging("architect")
        self._locks: Dict[str, asyncio.Lock] = {}
        self.settings.workspace_root.mkdir(parents=True, exist_ok=True)

    def _lock_for(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def _bootstrap_prompt(self, description: str) -> str:
        guidance = (
            "You are the Architect for the scalable-textgrad agent. "
            "Bootstrap runner.py and tests.py according to the design docs. "
            "Honor the repository layout: runner.py, tests.py, logs/, state/. "
            "Use the helper library where possible."
        )
        return f"""{guidance}\nSystem description:\n{description}\n"""

    def _feedback_prompt(self, message: str) -> str:
        return (
            "You are Codex acting as the Architect's implementation sub-agent. "
            "Interpret the following feedback and apply necessary updates.\n"
            f"Feedback:\n{message}\n"
        )

    def start_agent(self, request: StartAgentRequest) -> StartAgentResponse:
        dirs = resolve_workspace(self.settings, request.agent_name)
        if dirs.root.exists() and any(dirs.root.iterdir()):
            raise HTTPException(status_code=409, detail=f"Workspace {dirs.root} is not empty")
        dirs.root.mkdir(parents=True, exist_ok=True)
        gitignore = dirs.root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("state/\nlogs/\n*.pyc\n__pycache__/\n" + "\n")

        manager = StateManager(dirs)
        manager.ensure_layout()

        try:
            result = self.codex.run(self._bootstrap_prompt(request.description), dirs.root)
        except CodexError as err:
            raise HTTPException(status_code=500, detail=str(err)) from err
        if result.exit_code != 0:
            raise HTTPException(status_code=500, detail="Codex bootstrap failed")

        log_event(self.logger, "workspace_bootstrap", agent=request.agent_name)

        return StartAgentResponse(
            workspace=str(dirs.root),
            agent_name=request.agent_name,
        )

    def _resolve_agent(self, agent_name: str) -> AgentDirectories:
        workspace = self.settings.workspace_root / agent_name
        if not workspace.exists():
            raise HTTPException(status_code=404, detail=f"Unknown agent {agent_name}")
        return self.settings.paths_for(workspace)

    async def handle_chat(self, agent_name: str, request: ArchitectChatRequest) -> ArchitectChatResponse:
        dirs = self._resolve_agent(agent_name)
        lock = self._lock_for(dirs.root.name)
        async with lock:
            return await asyncio.get_running_loop().run_in_executor(
                None, self._sync_handle_chat, agent_name, request, dirs
            )

    def _sync_handle_chat(
        self, agent_name: str, request: ArchitectChatRequest, dirs: AgentDirectories
    ) -> ArchitectChatResponse:
        prompt = self._feedback_prompt(request.message)
        try:
            result = self.codex.run(prompt, dirs.root)
        except CodexError as err:
            raise HTTPException(status_code=500, detail=str(err)) from err
        if result.exit_code != 0:
            raise HTTPException(status_code=500, detail="Codex update failed")

        log_event(
            self.logger,
            "architect_update",
            agent=agent_name,
            message=request.message,
        )
        return ArchitectChatResponse(result="applied")


_service = ArchitectService()


@app.post("/agent/start")
def start_agent(request: StartAgentRequest) -> StartAgentResponse:
    return _service.start_agent(request)


@app.post("/agent/{agent_name}/architect/chat")
async def architect_chat(agent_name: str, request: ArchitectChatRequest) -> JSONResponse:
    response = await _service.handle_chat(agent_name, request)
    return JSONResponse(content=response.model_dump())
