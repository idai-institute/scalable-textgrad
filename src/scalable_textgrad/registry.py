"""Persistent registry of agent versions."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class VersionRecord(BaseModel):
    version: str
    commit_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(extra="ignore")


class VersionRegistry:
    """Thread-safe registry persisted to a JSON file."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._lock = RLock()
        self._records: Dict[str, VersionRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps({"records": []}, indent=2) + "\n")
            return
        data = json.loads(self.storage_path.read_text())
        for entry in data.get("records", []):
            record = VersionRecord(**entry)
            self._records[record.commit_hash] = record

    def _flush(self) -> None:
        payload = {"records": [record.model_dump(mode="json") for record in self._records.values()]}
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(payload, indent=2) + "\n")

    def upsert(
        self,
        *,
        commit_hash: str,
        version: str,
    ) -> VersionRecord:
        with self._lock:
            record = self._records.get(commit_hash)
            if not record:
                record = VersionRecord(version=version, commit_hash=commit_hash)
            record.version = version
            record.updated_at = datetime.utcnow()
            self._records[commit_hash] = record
            self._flush()
            return record

    def get_by_version(self, version: str) -> Optional[VersionRecord]:
        with self._lock:
            for record in self._records.values():
                if record.version == version:
                    return record
            return None

    def get_by_commit(self, commit_hash: str) -> Optional[VersionRecord]:
        with self._lock:
            return self._records.get(commit_hash)
