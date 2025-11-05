"""Simple CI helpers for the Architect."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .process import run_command


@dataclass
class StepResult:
    name: str
    success: bool
    stdout: str
    stderr: str


@dataclass
class PipelineResult:
    success: bool
    steps: List[StepResult]

    @property
    def summary(self) -> str:
        lines = []
        for step in self.steps:
            status = "PASS" if step.success else "FAIL"
            lines.append(f"[{status}] {step.name}")
            if step.stderr:
                lines.append(step.stderr.strip())
        return "\n".join(lines)


def run_ci(workdir: Path) -> PipelineResult:
    steps: List[StepResult] = []

    tests_path = workdir / "tests.py"
    pytest_bin = shutil.which("pytest")
    if tests_path.exists() and pytest_bin:
        pytest_cmd = [pytest_bin, "-q", str(tests_path)]
        result = run_command(pytest_cmd, cwd=workdir)
        steps.append(StepResult("pytest", result.exit_code == 0, result.stdout, result.stderr))
    elif tests_path.exists():
        steps.append(StepResult("pytest", False, "", "pytest not available"))
    else:
        steps.append(StepResult("pytest", False, "", "tests.py missing"))

    success = all(step.success for step in steps)
    return PipelineResult(success=success, steps=steps)
