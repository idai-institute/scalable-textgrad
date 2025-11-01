from __future__ import annotations

from pathlib import Path

from scalable_textgrad.config import AgentSettings
from scalable_textgrad.state_manager import StateManager


def make_manager(tmp_path: Path) -> StateManager:
    settings = AgentSettings(workspace_root=tmp_path)
    dirs = settings.paths_for(tmp_path / "agent")
    manager = StateManager(dirs)
    manager.ensure_layout()
    return manager


def test_write_and_read(tmp_path: Path) -> None:
    manager = make_manager(tmp_path)
    initial = manager.read_state()
    assert initial.payload == {}

    manager.write_state({"value": 42})
    active = manager.read_state()
    assert active.payload["value"] == 42


def test_layout_only_includes_state_file(tmp_path: Path) -> None:
    manager = make_manager(tmp_path)

    assert manager.dirs.state_dir.exists()
    assert manager.dirs.active_state_file.exists()
    assert not (manager.dirs.state_dir / ".lock").exists()
