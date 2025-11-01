from __future__ import annotations

from pathlib import Path

import pytest

from scalable_textgrad.codex_client import CodexError, CodexRunner
from scalable_textgrad.config import AgentSettings


def test_codex_runner_requires_executable(tmp_path: Path) -> None:
    settings = AgentSettings(workspace_root=tmp_path, codex_command="__missing_codex__")
    runner = CodexRunner(settings)

    with pytest.raises(CodexError):
        runner.run("echo hello", tmp_path)
