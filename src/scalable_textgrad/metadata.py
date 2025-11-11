"""Metadata helpers for agent versions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import semver
from pydantic import BaseModel, ConfigDict, Field


DEFAULT_VERSION = "0.0.0"
class VersionMetadata(BaseModel):
    """Metadata describing the active version."""

    version: str = DEFAULT_VERSION
    commit_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(extra="ignore")

    def bump(self) -> str:
        """Return the next patch version."""

        current = semver.VersionInfo.parse(self.version)
        new_version = current.bump_patch()
        self.version = str(new_version)
        self.updated_at = datetime.utcnow()
        return self.version

    def update_commit(self, commit_hash: str | None) -> None:
        self.commit_hash = commit_hash
        self.updated_at = datetime.utcnow()


def load_metadata(path: Path) -> VersionMetadata:
    if not path.exists():
        metadata = VersionMetadata()
        save_metadata(path, metadata)
        return metadata
    return VersionMetadata.model_validate_json(path.read_text())


def save_metadata(path: Path, metadata: VersionMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metadata.model_dump_json(indent=2) + "\n")
