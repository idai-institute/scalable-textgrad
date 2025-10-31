"""Configuration helpers for the Scalable TextGrad platform."""

from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentDirectories(BaseModel):
    """Resolved directory and file locations for an agent workspace."""

    root: Path
    state_dir: Path
    active_state_file: Path


class AgentSettings(BaseSettings):
    """Global configuration for services and helpers."""

    workspace_root: Path = Field(default_factory=lambda: Path.cwd() / "agents")
    active_state_filename: str = "active.state.json"
    state_dirname: str = "state"
    codex_command: str = "codex"

    model_config = SettingsConfigDict(env_prefix="STG_", env_file=".env", extra="allow")

    def paths_for(self, root: Path) -> AgentDirectories:
        state_dir = root / self.state_dirname
        return AgentDirectories(
            root=root,
            state_dir=state_dir,
            active_state_file=state_dir / self.active_state_filename,
        )


def resolve_workspace(settings: AgentSettings, agent_name: str) -> AgentDirectories:
    """Return directories for a named agent workspace inside the workspace root."""

    root = settings.workspace_root / agent_name
    return settings.paths_for(root)
