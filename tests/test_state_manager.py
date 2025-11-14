from __future__ import annotations

from pathlib import Path

import pytest

from scalable_textgrad.config import AgentSettings
from scalable_textgrad.state_manager import StateManager, StateValidationError


def make_manager(tmp_path: Path) -> StateManager:
    settings = AgentSettings(workspace_root=tmp_path)
    dirs = settings.paths_for(tmp_path / "agent")
    manager = StateManager(dirs)
    manager.ensure_layout()
    return manager


def test_write_and_promote(tmp_path: Path) -> None:
    manager = make_manager(tmp_path)
    staging_doc = manager.read_state("staging")
    token = manager.write_state("staging", {"value": 42}, staging_doc.token)
    assert token != staging_doc.token

    manager.promote(expected_staging_token=token)
    active = manager.read_state("active")
    assert active.payload["value"] == 42


def test_occ_guard(tmp_path: Path) -> None:
    manager = make_manager(tmp_path)
    with pytest.raises(StateValidationError):
        manager.write_state("staging", {"boom": True}, expected_token="not-valid")
