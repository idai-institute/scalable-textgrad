"""FastAPI service implementing the Architect endpoints."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..codex_client import CodexRunner, CodexError
from ..config import AgentDirectories, AgentSettings, resolve_workspace
from ..git_repo import GitRepository
from ..logging_utils import configure_logging, log_event
from ..metadata import load_metadata, save_metadata
from ..registry import VersionRegistry
from ..state_manager import StateManager

app = FastAPI(title="Architect Service", version="0.1.0")


class StartAgentRequest(BaseModel):
    agent_name: str = Field(default="ROOT", description="Name of the agent workspace")
    description: str = Field(..., description="High-level description of the system")


class StartAgentResponse(BaseModel):
    workspace: str
    version: str
    commit_hash: str


class ArchitectChatRequest(BaseModel):
    message: str


class ArchitectChatResponse(BaseModel):
    result: str
    new_version: Optional[str] = None
    commit_hash: Optional[str] = None


class ArchitectService:
    def __init__(self) -> None:
        self.settings = AgentSettings()
        self.registry = VersionRegistry(self.settings.registry_file)
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
            "Honor the repository layout: runner.py, tests.py, logs/, state/, metadata.json. "
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
        metadata = load_metadata(dirs.metadata_file)

        repo = GitRepository.open(dirs.root)
        try:
            result = self.codex.run(self._bootstrap_prompt(request.description), dirs.root)
        except CodexError as err:
            raise HTTPException(status_code=500, detail=str(err)) from err
        if result.exit_code != 0:
            raise HTTPException(status_code=500, detail="Codex bootstrap failed")

        commit_hash = repo.commit_all("Bootstrap agent")
        metadata.update_commit(commit_hash)
        save_metadata(dirs.metadata_file, metadata)

        new_root = dirs.root.parent / commit_hash
        if new_root != dirs.root:
            if new_root.exists():
                raise HTTPException(status_code=409, detail=f"Workspace {new_root} already exists")
            shutil.move(str(dirs.root), str(new_root))
        self.registry.upsert(commit_hash=commit_hash, version=metadata.version)
        log_event(self.logger, "workspace_bootstrap", commit=commit_hash, version=metadata.version)

        return StartAgentResponse(
            workspace=str(new_root),
            version=metadata.version,
            commit_hash=commit_hash,
        )

    def _resolve_dirs(self, version: str) -> AgentDirectories:
        candidate = self.settings.workspace_root / version
        if candidate.exists():
            return self.settings.paths_for(candidate)
        record = self.registry.get_by_version(version)
        if record:
            commit_path = self.settings.workspace_root / record.commit_hash
            if commit_path.exists():
                return self.settings.paths_for(commit_path)
        raise HTTPException(status_code=404, detail=f"Unknown version {version}")

    async def handle_chat(self, version: str, request: ArchitectChatRequest) -> ArchitectChatResponse:
        dirs = self._resolve_dirs(version)
        lock = self._lock_for(dirs.root.name)
        async with lock:
            return await asyncio.get_running_loop().run_in_executor(
                None, self._sync_handle_chat, version, request, dirs
            )

    def _sync_handle_chat(
        self, version: str, request: ArchitectChatRequest, dirs: AgentDirectories
    ) -> ArchitectChatResponse:
        metadata = load_metadata(dirs.metadata_file)
        repo = GitRepository.open(dirs.root)
        staging_dir = dirs.staging_path()
        repo.clone_to(staging_dir)
        prompt = self._feedback_prompt(request.message)
        try:
            result = self.codex.run(prompt, staging_dir)
        except CodexError as err:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail=str(err)) from err
        if result.exit_code != 0:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail="Codex update failed")

        staging_repo = GitRepository.open(staging_dir)
        if staging_repo.is_clean():
            shutil.rmtree(staging_dir, ignore_errors=True)
            return ArchitectChatResponse(result="rejected")

        metadata.bump()
        stage_metadata = Path(staging_dir) / self.settings.metadata_filename
        save_metadata(stage_metadata, metadata)
        commit_message = f"Architect update: {request.message[:80]}"
        commit_hash = staging_repo.commit_all(commit_message)

        new_root = dirs.root.parent / commit_hash
        if new_root.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise HTTPException(status_code=409, detail=f"Workspace {new_root} already exists")
        shutil.move(str(staging_dir), str(new_root))
        self.registry.upsert(
            commit_hash=commit_hash,
            version=metadata.version,
        )
        log_event(
            self.logger,
            "architect_commit",
            commit=commit_hash,
            version=metadata.version,
            message=request.message,
        )
        return ArchitectChatResponse(
            result="committed",
            new_version=metadata.version,
            commit_hash=commit_hash,
        )


_service = ArchitectService()


@app.post("/agent/start")
def start_agent(request: StartAgentRequest) -> StartAgentResponse:
    return _service.start_agent(request)


@app.post("/agent/{version}/architect/chat")
async def architect_chat(version: str, request: ArchitectChatRequest) -> JSONResponse:
    response = await _service.handle_chat(version, request)
    return JSONResponse(content=response.model_dump())
