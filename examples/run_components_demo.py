from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Tuple

import httpx
import uvicorn

# Configure shared workspace before importing the FastAPI apps so settings pick it up.
WORKSPACE_ROOT = (Path(__file__).parent / "demo_workspaces").resolve()
os.environ.setdefault("STG_WORKSPACE_ROOT", str(WORKSPACE_ROOT))
# Skip Codex CLI execution by default; set STG_CODEX_SIMULATE=0 to exercise a real Codex run.
if "STG_CODEX_SIMULATE" not in os.environ:
    os.environ["STG_CODEX_SIMULATE"] = "1"
SIMULATE = os.environ.get("STG_CODEX_SIMULATE", "1")
print(f"STG_CODEX_SIMULATE={SIMULATE} (set to 0 to run Codex for real)")

from scalable_textgrad.architect.service import app as architect_app  # noqa: E402
from scalable_textgrad.version_manager.service import app as version_manager_app  # noqa: E402


def print_tree(root: Path, max_depth: int = 2) -> None:
    """Lightweight tree printer to show created files."""

    root = root.resolve()
    print(f"Workspace files in {root}:")
    for path, dirs, files in os.walk(root):
        depth = Path(path).relative_to(root).parts
        if len(depth) > max_depth:
            # Prevent walking too deep
            dirs[:] = []
            continue
        for name in sorted(files):
            rel = Path(path, name).relative_to(root)
            print(f"- {rel}")


async def start_server(app, host: str, port: int, name: str) -> Tuple[uvicorn.Server, asyncio.Task]:
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started and not task.done():
        await asyncio.sleep(0.05)
    if task.done() and not server.started:
        task.result()  # re-raise any startup failure
    print(f"{name} listening on http://{host}:{port}")
    return server, task


async def stop_server(server: uvicorn.Server, task: asyncio.Task, name: str) -> None:
    server.should_exit = True
    try:
        await asyncio.wait_for(task, timeout=5.0)
    except asyncio.TimeoutError:
        print(f"{name} shutdown timed out; cancelling task...")
        server.force_exit = True
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    print(f"{name} stopped")


async def main() -> None:
    shutil.rmtree(WORKSPACE_ROOT, ignore_errors=True)
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

    architect_host, architect_port = "127.0.0.1", 8001
    vm_host, vm_port = "127.0.0.1", 8000

    servers: list[tuple[uvicorn.Server, asyncio.Task, str]] = []
    try:
        arch_server, arch_task = await start_server(architect_app, architect_host, architect_port, "Architect")
        servers.append((arch_server, arch_task, "Architect"))

        vm_server, vm_task = await start_server(version_manager_app, vm_host, vm_port, "Version Manager")
        servers.append((vm_server, vm_task, "Version Manager"))

        architect_base = f"http://{architect_host}:{architect_port}"
        vm_base = f"http://{vm_host}:{vm_port}"

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0)) as client:
            try:
                start_resp = await client.post(
                    f"{architect_base}/agent/start",
                    json={
                        "agent_name": "ROOT",
                        "description": "Demo agent started from run_components_demo.py",
                    },
                )
                start_resp.raise_for_status()
            except httpx.RequestError as exc:
                print(f"Request to Architect failed: {exc}")
                return
            start_data = start_resp.json()
            version = start_data["version"]
            commit_hash = start_data["commit_hash"]
            print(f"Bootstrapped agent version {version} (commit {commit_hash})")
            workspace = Path(start_data["workspace"])
            print_tree(workspace, max_depth=3)

            register_payload = {
                "version": version,
                "commit_hash": commit_hash,
                "component": "architect",
                "base_url": f"{architect_base}/agent/{commit_hash}/architect",
            }
            register_resp = await client.post(f"{vm_base}/agents/register", json=register_payload)
            register_resp.raise_for_status()
            print("Registered architect service with Version Manager.")

            chat_resp = await client.post(
                f"{vm_base}/agent/{commit_hash}/architect/chat",
                json={"message": "Please add a friendly greeting to the workspace README."},
            )
            if chat_resp.is_success:
                print("Architect chat response:", chat_resp.json())
            else:
                print(
                    f"Architect chat failed ({chat_resp.status_code}): {chat_resp.text}",
                    "Proxy URL:",
                    f"{vm_base}/agent/{commit_hash}/architect/chat",
                )
                return

            versions_resp = await client.get(f"{vm_base}/versions", params={"limit": 5, "offset": 0})
            versions_resp.raise_for_status()
            print("Known versions from Version Manager:", versions_resp.json())
            print_tree(workspace, max_depth=3)
    finally:
        for server, task, name in reversed(servers):
            await stop_server(server, task, name)


if __name__ == "__main__":
    asyncio.run(main())
