"""FastAPI service for the Version Manager."""

from __future__ import annotations

from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..config import AgentSettings
from ..logging_utils import configure_logging, log_event
from ..registry import ServiceEndpoint, VersionRecord, VersionRegistry

app = FastAPI(title="Version Manager", version="0.1.0")


class RegisterServiceRequest(BaseModel):
    version: str
    commit_hash: str
    component: Literal["runner", "tuner"]
    base_url: str = Field(..., description="Base URL where the component listens")


class RegisterServiceResponse(BaseModel):
    version: str
    commit_hash: str
    component: str
    base_url: str


class VersionManagerService:
    def __init__(self) -> None:
        self.settings = AgentSettings()
        self.registry = VersionRegistry(self.settings.registry_file)
        self.logger = configure_logging("version-manager")
        self._client = httpx.AsyncClient(timeout=30)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def proxy(self, version: str, component: str, path_suffix: str, request: Request) -> Response:
        record = self._resolve_record(version)
        if component not in {"runner", "tuner"}:
            raise HTTPException(status_code=404, detail="Unknown component")
        endpoint = getattr(record, component, None)
        if not isinstance(endpoint, ServiceEndpoint):
            raise HTTPException(status_code=404, detail=f"{component} not registered for {version}")
        url = endpoint.base_url.rstrip("/")
        if path_suffix:
            url = f"{url}/{path_suffix}"
        try:
            resp = await self._client.request(
                request.method,
                url,
                content=await request.body(),
                headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
                params=list(request.query_params.multi_items()),
            )
        except httpx.HTTPError as err:
            raise HTTPException(status_code=502, detail=str(err)) from err
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

    def register_service(self, payload: RegisterServiceRequest) -> RegisterServiceResponse:
        record = self.registry.register_service(
            commit_hash=payload.commit_hash,
            version=payload.version,
            component=payload.component,
            base_url=payload.base_url,
        )
        log_event(
            self.logger,
            "service_registered",
            version=payload.version,
            commit=payload.commit_hash,
            component=payload.component,
            base_url=payload.base_url,
        )
        return RegisterServiceResponse(
            version=record.version,
            commit_hash=record.commit_hash,
            component=payload.component,
            base_url=payload.base_url,
        )

    def list_versions(self) -> dict:
        records = self.registry.list_versions()
        return {"versions": [self._serialize_record(record) for record in records]}

    def _serialize_record(self, record: VersionRecord) -> dict:
        payload = {
            "version": record.version,
            "created_at": record.created_at.isoformat(),
        }
        if record.runner:
            payload["runner"] = {"mcp_endpoint": f"/agent/{record.version}/runner"}
        if record.tuner:
            payload["tuner"] = {"mcp_endpoint": f"/agent/{record.version}/tuner"}
        return payload

    def _resolve_record(self, version: str) -> VersionRecord:
        record = self.registry.get_by_version(version)
        if record:
            return record
        raise HTTPException(status_code=404, detail=f"Unknown version {version}")


_service = VersionManagerService()


@app.post("/agents/register")
def register_service(payload: RegisterServiceRequest) -> RegisterServiceResponse:
    return _service.register_service(payload)


@app.get("/versions")
def list_versions() -> dict:
    return _service.list_versions()


@app.api_route(
    "/agent/{version}/{component}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def proxy_component_root(version: str, component: str, request: Request) -> Response:
    return await _service.proxy(version, component, "", request)


@app.api_route(
    "/agent/{version}/{component}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def proxy_component(version: str, component: str, path: str, request: Request) -> Response:
    return await _service.proxy(version, component, path, request)


@app.on_event("shutdown")
async def _shutdown() -> None:
    await _service.aclose()
