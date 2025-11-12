from __future__ import annotations

import os
import shutil
from pathlib import Path
from textwrap import dedent

from scalable_textgrad.architect.service import (
    ArchitectService,
    StartAgentRequest,
)
from scalable_textgrad.codex_client import CodexResult


class DummyCodexRunner:
    """Deterministic Codex stub that writes initial files for the demo."""

    def run(self, prompt: str, workdir: Path, **_: object) -> CodexResult:  # type: ignore[override]
        path = Path(workdir)
        self._write_initial_files(path)
        return CodexResult(
            exit_code=0,
            stdout="dummy",
            stderr="",
            last_message="dummy run",
        )

    def _write_initial_files(self, path: Path) -> None:
        runner = dedent(
            """
            FORECAST = {"condition": "sunny", "temperature_c": 22}


            def describe_weather(location: str) -> dict:
                return {"location": location, **FORECAST}


            if __name__ == "__main__":
                import json
                print(json.dumps(describe_weather("Testville")))
            """
        ).strip() + "\n"
        tests = dedent(
            """
            from runner import describe_weather


            def test_describe_weather():
                result = describe_weather("Demo City")
                assert result["location"] == "Demo City"
                assert result["condition"] == "sunny"
            """
        ).strip() + "\n"
        (path / "runner.py").write_text(runner)
        (path / "tests.py").write_text(tests)


def main() -> None:
    workspace_root = Path("examples/mock_weather_workspaces").resolve()
    shutil.rmtree(workspace_root, ignore_errors=True)
    workspace_root.mkdir(parents=True, exist_ok=True)
    os.environ["STG_WORKSPACE_ROOT"] = str(workspace_root)

    architect = ArchitectService()
    architect.codex = DummyCodexRunner()

    start_response = architect.start_agent(
        StartAgentRequest(
            agent_name="ROOT",
            description="A mock weather system that exposes runner skeletons.",
        )
    )
    print("Bootstrap:", start_response)


if __name__ == "__main__":
    main()
