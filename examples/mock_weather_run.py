from __future__ import annotations

import shutil
from pathlib import Path
from textwrap import dedent

from scalable_textgrad.ci import run_ci
from scalable_textgrad.codex_client import CodexResult
from scalable_textgrad.config import AgentSettings, resolve_workspace
from scalable_textgrad.state_manager import StateManager


class DummyCodexRunner:
    """Deterministic Codex stub that writes initial files for the demo."""

    def run(self, prompt: str, workdir: Path, **_: object) -> CodexResult:  # type: ignore[override]
        path = Path(workdir)
        self._write_initial_files(path)
        return CodexResult(
            exit_code=0,
            stdout="dummy",
            stderr="",
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


def bootstrap_workspace(workspace_root: Path) -> Path:
    settings = AgentSettings(workspace_root=workspace_root)
    dirs = resolve_workspace(settings, "ROOT")
    dirs.root.mkdir(parents=True, exist_ok=True)

    manager = StateManager(dirs)
    manager.ensure_layout()

    DummyCodexRunner().run("seed weather agent", dirs.root)
    return dirs.root


def main() -> None:
    workspace_root = Path("examples/mock_weather_workspaces").resolve()
    shutil.rmtree(workspace_root, ignore_errors=True)
    workspace_root.mkdir(parents=True, exist_ok=True)

    workspace = bootstrap_workspace(workspace_root)
    pipeline = run_ci(workspace)

    print("Workspace:", workspace)
    print(pipeline.summary)


if __name__ == "__main__":
    main()
