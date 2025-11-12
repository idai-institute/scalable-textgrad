"""FastAPI service for the Version Manager."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ..config import AgentSettings
from ..logging_utils import configure_logging, log_event
from ..registry import VersionRegistry

app = FastAPI(title="Version Manager", version="0.1.0")


class RegisterServiceRequest(BaseModel):
    version: str
    commit_hash: str
    base_url: str = Field(..., description="Base URL where the runner listens")


class RegisterServiceResponse(BaseModel):
    version: str
    commit_hash: str
    base_url: str


class VersionManagerService:
    def __init__(self) -> None:
        self.settings = AgentSettings()
        self.registry = VersionRegistry(self.settings.registry_file)
        self.logger = configure_logging("version-manager")

    def register_service(self, payload: RegisterServiceRequest) -> RegisterServiceResponse:
        record = self.registry.register_service(
            commit_hash=payload.commit_hash,
            version=payload.version,
            base_url=payload.base_url,
        )
        log_event(
            self.logger,
            "service_registered",
            version=payload.version,
            commit=payload.commit_hash,
            base_url=payload.base_url,
        )
        return RegisterServiceResponse(
            version=record.version,
            commit_hash=record.commit_hash,
            base_url=payload.base_url,
        )


_service = VersionManagerService()


@app.post("/agents/register")
def register_service(payload: RegisterServiceRequest) -> RegisterServiceResponse:
    return _service.register_service(payload)
