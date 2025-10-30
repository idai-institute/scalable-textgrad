"""Integration with the Codex CLI."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .config import AgentSettings


class CodexError(RuntimeError):
    pass


@dataclass
class CodexResult:
    """Response returned by the Codex CLI."""

    exit_code: int
    stdout: str
    stderr: str


class CodexRunner:
    """Small wrapper over the `codex` CLI executable."""

    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings

    def run(
        self,
        prompt: str,
        workdir: Path,
        *,
        full_auto: bool = True,
        sandbox: str = "danger-full-access",
        extra_args: Optional[Iterable[str]] = None,
    ) -> CodexResult:
        executable = shutil.which(self.settings.codex_command)
        if not executable:
            raise CodexError("Codex CLI not found in PATH; set STG_CODEX_COMMAND")

        cmd: list[str] = [executable, "exec", prompt]
        if sandbox:
            cmd += ["--sandbox", sandbox]
        if full_auto:
            cmd.append("--full-auto")
        if extra_args:
            cmd.extend(extra_args)

        process = subprocess.run(
            cmd,
            cwd=str(workdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ,
            text=True,
            check=False,
        )
        result = CodexResult(
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
        )
        return result
