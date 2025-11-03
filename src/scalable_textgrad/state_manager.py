"""State manager for agent workspaces."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Dict

from filelock import FileLock

from .config import AgentDirectories


class StateDocument(dict):
    """Represents the contents of a state file."""

    @property
    def payload(self) -> Dict[str, Any]:
        data = self.get("data")
        if not isinstance(data, dict):
            data = {}
            self["data"] = data
        return data


class StateManager:
    """Provides typed access to the agent state file."""

    def __init__(self, dirs: AgentDirectories) -> None:
        self.dirs = dirs
        self._lock = FileLock(str(dirs.state_lock_file))

    def ensure_layout(self) -> None:
        self.dirs.state_dir.mkdir(parents=True, exist_ok=True)
        if not self.dirs.active_state_file.exists():
            doc = StateDocument(data={})
            self.dirs.active_state_file.write_text(json.dumps(doc, indent=2) + "\n")
        self.dirs.state_lock_file.touch(exist_ok=True)

    def read_state(self) -> StateDocument:
        path = self.dirs.active_state_file
        if not path.exists():
            self.ensure_layout()
        raw = json.loads(path.read_text()) if path.exists() else {}
        doc = StateDocument(raw)
        doc.payload  # ensure payload
        return doc

    def write_state(self, payload: Dict[str, Any]) -> None:
        doc = StateDocument({"data": payload})
        path = self.dirs.active_state_file
        path.write_text(json.dumps(doc, indent=2) + "\n")

    @contextmanager
    def lock(self) -> Any:
        with self._lock:
            yield
