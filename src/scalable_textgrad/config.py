"""Configuration helpers for the Scalable TextGrad platform."""

from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentDirectories(BaseModel):
    """Resolved directory and file locations for an agent workspace."""

    root: Path
    state_dir: Path
    logs_dir: Path
    metadata_file: Path
    active_state_file: Path
    staging_state_file: Path
    state_lock_file: Path
    tests_file: Path
    runner_file: Path

    def staging_path(self, suffix: str) -> Path:
        """Return the path for the staging clone, typically `<root>-staging`."""

        return self.root.parent / f"{self.root.name}{suffix}"


class AgentSettings(BaseSettings):
    """Global configuration for services and helpers."""

    workspace_root: Path = Field(default_factory=lambda: Path.cwd() / "agents")
    staging_suffix: str = "-staging"
    metadata_filename: str = "metadata.json"
    active_state_filename: str = "active.state.json"
    staging_state_filename: str = "staging.state.json"
    state_dirname: str = "state"
    logs_dirname: str = "logs"
    codex_command: str = "codex"
    default_version: str = "0.0.0"
    tests_filename: str = "tests.py"
    runner_filename: str = "runner.py"
    registry_filename: str = "version_registry.json"

    model_config = SettingsConfigDict(env_prefix="STG_", env_file=".env", extra="allow")

    def paths_for(self, root: Path) -> AgentDirectories:
        state_dir = root / self.state_dirname
        logs_dir = root / self.logs_dirname
        return AgentDirectories(
            root=root,
            state_dir=state_dir,
            logs_dir=logs_dir,
            metadata_file=root / self.metadata_filename,
            active_state_file=state_dir / self.active_state_filename,
            staging_state_file=state_dir / self.staging_state_filename,
            state_lock_file=state_dir / ".lock",
            tests_file=root / self.tests_filename,
            runner_file=root / self.runner_filename,
        )

    @property
    def registry_file(self) -> Path:
        return self.workspace_root / self.registry_filename


def resolve_workspace(settings: AgentSettings, agent_name: str) -> AgentDirectories:
    """Return directories for a named agent workspace inside the workspace root."""

    root = settings.workspace_root / agent_name
    return settings.paths_for(root)
