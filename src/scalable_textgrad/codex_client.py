"""Integration with the Codex CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from .config import AgentSettings


class CodexError(RuntimeError):
    pass


@dataclass
class CodexResult:
    """Response returned by the Codex CLI."""

    exit_code: int
    stdout: str
    stderr: str
    last_message: str | None = None
    events: Optional[List[dict]] = None


class CodexRunner:
    """Small wrapper over the `codex` CLI executable."""

    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings

    def run(
        self,
        prompt: str,
        workdir: Path,
        *,
        json_output: bool = False,
        full_auto: bool = True,
        sandbox: str = "danger-full-access",
        extra_args: Optional[Iterable[str]] = None,
    ) -> CodexResult:
        if self.settings.codex_simulate:
            return CodexResult(
                exit_code=0,
                stdout="",
                stderr="",
                last_message="Simulation mode enabled; Codex execution skipped.",
                events=[],
            )

        executable = shutil.which(self.settings.codex_command)
        if not executable:
            raise CodexError("Codex CLI not found in PATH; set STG_CODEX_COMMAND or enable simulation")

        cmd: List[str] = [executable, "exec", prompt]
        if sandbox:
            cmd += ["--sandbox", sandbox]
        if full_auto:
            cmd.append("--full-auto")
        if json_output:
            cmd.append("--json")
        if self.settings.codex_profile:
            cmd += ["--profile", self.settings.codex_profile]
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
        last_message = process.stdout.strip().splitlines()[-1] if process.stdout.strip() else None
        result = CodexResult(
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
            last_message=last_message,
        )
        if json_output and process.stdout.strip():
            result.events = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
        return result
