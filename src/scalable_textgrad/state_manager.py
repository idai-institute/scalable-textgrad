"""State manager shared between Runner, Tuner, and Architect."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from filelock import FileLock

from .config import AgentDirectories

StateTarget = Literal["active", "staging"]


class StateDocument(dict):
    """Represents the contents of a state file, tracking an OCC token."""

    @property
    def token(self) -> str:
        token = self.get("version_id")
        if not isinstance(token, str):
            token = uuid4().hex
            self["version_id"] = token
        return token

    @property
    def payload(self) -> Dict[str, Any]:
        data = self.get("data")
        if not isinstance(data, dict):
            data = {}
            self["data"] = data
        return data


class StateValidationError(RuntimeError):
    pass


class StateManager:
    """Provides typed access to active and staging state files."""

    def __init__(self, dirs: AgentDirectories) -> None:
        self.dirs = dirs
        self._lock = FileLock(str(dirs.state_lock_file))

    def ensure_layout(self) -> None:
        self.dirs.state_dir.mkdir(parents=True, exist_ok=True)
        for path in (self.dirs.active_state_file, self.dirs.staging_state_file):
            if not path.exists():
                doc = StateDocument(version_id=uuid4().hex, data={})
                path.write_text(json.dumps(doc, indent=2) + "\n")
        self.dirs.state_lock_file.touch(exist_ok=True)

    def read_state(self, target: StateTarget) -> StateDocument:
        path = self._path_for(target)
        if not path.exists():
            self.ensure_layout()
        raw = json.loads(path.read_text()) if path.exists() else {}
        doc = StateDocument(raw)
        doc.token  # ensure token
        doc.payload  # ensure payload
        return doc

    def write_state(self, target: StateTarget, payload: Dict[str, Any], expected_token: Optional[str]) -> str:
        doc = self.read_state(target)
        if expected_token and doc.token != expected_token:
            raise StateValidationError(
                f"Stale state token for {target}: have {expected_token}, current {doc.token}"
            )
        doc["data"] = payload
        doc["version_id"] = uuid4().hex
        path = self._path_for(target)
        path.write_text(json.dumps(doc, indent=2) + "\n")
        return doc.token

    def promote(self, expected_staging_token: Optional[str] = None) -> str:
        staging = self.read_state("staging")
        if expected_staging_token and staging.token != expected_staging_token:
            raise StateValidationError("Staging state token mismatch during promote")
        token = self.write_state("active", staging.payload, expected_token=None)
        return token

    @contextmanager
    def lock(self) -> Any:
        with self._lock:
            yield

    def _path_for(self, target: StateTarget) -> Path:
        return self.dirs.active_state_file if target == "active" else self.dirs.staging_state_file
