"""Utilities for running subprocesses with logging."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

    def check(self) -> "CommandResult":
        if self.exit_code != 0:
            raise RuntimeError(self.stderr or f"Command failed with {self.exit_code}")
        return self


def run_command(
    args: Iterable[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = None,
) -> CommandResult:
    process = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        env=dict(env) if env else None,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(exit_code=process.returncode, stdout=process.stdout, stderr=process.stderr)
