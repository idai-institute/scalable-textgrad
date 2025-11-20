from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from textwrap import dedent

from scalable_textgrad.architect.service import (
    ArchitectChatRequest,
    ArchitectService,
    StartAgentRequest,
)
from scalable_textgrad.codex_client import CodexResult
from scalable_textgrad.version_manager.service import VersionManagerService


class DummyCodexRunner:
    """Deterministic Codex stub that writes/updates files for the demo."""

    def __init__(self) -> None:
        self.calls = 0

    def run(self, prompt: str, workdir: Path, **_: object) -> CodexResult:  # type: ignore[override]
        path = Path(workdir)
        if self.calls == 0:
            self._write_initial_files(path)
        else:
            self._update_runner(path)
        self.calls += 1
        return CodexResult(
            exit_code=0,
            stdout="dummy",
            stderr="",
            last_message=f"dummy run #{self.calls}",
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
        tuner = dedent(
            """
            def record_reward(conversation_id: str, reward: float) -> dict:
                return {"conversation_id": conversation_id, "reward": reward}
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
        (path / "tuner.py").write_text(tuner)
        (path / "tests.py").write_text(tests)

    def _update_runner(self, path: Path) -> None:
        runner = dedent(
            """
            FORECAST = {
                "condition": "sunny",
                "temperature_c": 22,
                "wind_kph": 12,
            }


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


            def test_describe_weather_with_wind():
                result = describe_weather("Demo City")
                assert result["wind_kph"] == 12
            """
        ).strip() + "\n"
        (path / "runner.py").write_text(runner)
        (path / "tests.py").write_text(tests)


async def main() -> None:
    workspace_root = Path("examples/mock_weather_workspaces").resolve()
    shutil.rmtree(workspace_root, ignore_errors=True)
    workspace_root.mkdir(parents=True, exist_ok=True)
    os.environ["STG_WORKSPACE_ROOT"] = str(workspace_root)

    architect = ArchitectService()
    architect.codex = DummyCodexRunner()

    start_response = architect.start_agent(
        StartAgentRequest(
            agent_name="ROOT",
            description="A mock weather system that exposes runner/tuner skeletons.",
        )
    )
    print("Bootstrap:", start_response)

    chat_response = await architect.handle_chat(
        start_response.version,
        ArchitectChatRequest(
            message="Add wind speed to the weather payload and update tests.",
        ),
    )
    print("Chat:", chat_response)

    vm = VersionManagerService()
    listing = vm.list_versions(limit=10, offset=0)
    print("Versions:", listing)
    await vm.aclose()


if __name__ == "__main__":
    asyncio.run(main())
