"""FastAPI service for the Version Manager."""

from __future__ import annotations

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
        self._client = httpx.AsyncClient(timeout=30)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def proxy(self, version: str, path_suffix: str, request: Request) -> Response:
        record = self._resolve_record(version)
        endpoint = record.runner
        if not isinstance(endpoint, ServiceEndpoint):
            raise HTTPException(status_code=404, detail=f"runner not registered for {version}")
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

    def _resolve_record(self, version: str) -> VersionRecord:
        record = self.registry.get_by_version(version)
        if record:
            return record
        raise HTTPException(status_code=404, detail=f"Unknown version {version}")


_service = VersionManagerService()


@app.post("/agents/register")
def register_service(payload: RegisterServiceRequest) -> RegisterServiceResponse:
    return _service.register_service(payload)


@app.api_route(
    "/agent/{version}/runner",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def proxy_runner_root(version: str, request: Request) -> Response:
    return await _service.proxy(version, "", request)


@app.api_route(
    "/agent/{version}/runner/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def proxy_runner(version: str, path: str, request: Request) -> Response:
    return await _service.proxy(version, path, request)


@app.on_event("shutdown")
async def _shutdown() -> None:
    await _service.aclose()
