"""FastAPI service implementing the Architect endpoints."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..codex_client import CodexRunner, CodexError
from ..config import AgentSettings, resolve_workspace
from ..logging_utils import configure_logging, log_event
from ..state_manager import StateManager

app = FastAPI(title="Architect Service", version="0.1.0")


class StartAgentRequest(BaseModel):
    agent_name: str = Field(default="ROOT", description="Name of the agent workspace")
    description: str = Field(..., description="High-level description of the system")


class StartAgentResponse(BaseModel):
    workspace: str
    agent_name: str

class ArchitectService:
    def __init__(self) -> None:
        self.settings = AgentSettings()
        self.codex = CodexRunner(self.settings)
        self.logger = configure_logging("architect")
        self.settings.workspace_root.mkdir(parents=True, exist_ok=True)

    def _bootstrap_prompt(self, description: str) -> str:
        guidance = (
            "You are the Architect for the scalable-textgrad agent. "
            "Bootstrap runner.py and tests.py according to the design docs. "
            "Honor the repository layout: runner.py, tests.py, logs/, state/. "
            "Use the helper library where possible."
        )
        return f"""{guidance}\nSystem description:\n{description}\n"""

    def start_agent(self, request: StartAgentRequest) -> StartAgentResponse:
        dirs = resolve_workspace(self.settings, request.agent_name)
        if dirs.root.exists() and any(dirs.root.iterdir()):
            raise HTTPException(status_code=409, detail=f"Workspace {dirs.root} is not empty")
        dirs.root.mkdir(parents=True, exist_ok=True)

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


_service = ArchitectService()


@app.post("/agent/start")
def start_agent(request: StartAgentRequest) -> StartAgentResponse:
    return _service.start_agent(request)
