from __future__ import annotations

from pathlib import Path

import pytest

from scalable_textgrad.architect.service import (
    ArchitectChatRequest,
    ArchitectService,
    StartAgentRequest,
)
from scalable_textgrad.codex_client import CodexResult


class StubCodexRunner:
    """Simple Codex stub that records calls and writes a marker file."""

    def __init__(self) -> None:
        self.calls: list[Path] = []

    def run(self, prompt: str, workdir: Path, **_: object) -> CodexResult:  # type: ignore[override]
        path = Path(workdir)
        self.calls.append(path)
        marker = path / "runner.py"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("print('hello')\n")
        return CodexResult(exit_code=0, stdout="", stderr="")


@pytest.fixture(autouse=True)
def set_workspace_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_root = tmp_path / "agents"
    monkeypatch.setenv("STG_WORKSPACE_ROOT", str(workspace_root))


def test_start_agent_creates_workspace() -> None:
    service = ArchitectService()
    stub = StubCodexRunner()
    service.codex = stub

    response = service.start_agent(
        StartAgentRequest(agent_name="demo", description="Sample agent"),
    )

    workspace = Path(response.workspace)
    assert response.agent_name == "demo"
    assert workspace.exists()
    assert workspace.name == "demo"
    assert (workspace / "state").exists()
    assert stub.calls == [workspace]


@pytest.mark.asyncio
async def test_chat_runs_in_place() -> None:
    service = ArchitectService()
    start_stub = StubCodexRunner()
    service.codex = start_stub

    start_response = service.start_agent(
        StartAgentRequest(agent_name="demo", description="Sample agent"),
    )
    workspace = Path(start_response.workspace)

    chat_stub = StubCodexRunner()
    service.codex = chat_stub
    response = await service.handle_chat(
        "demo", ArchitectChatRequest(message="Please refine the agent"),
    )

    assert response.result == "applied"
    assert chat_stub.calls == [workspace]
    assert not any(path.name.endswith("-staging") for path in workspace.parent.iterdir())
