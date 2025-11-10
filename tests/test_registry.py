from __future__ import annotations

from scalable_textgrad.registry import VersionRegistry


def test_registry_persists(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry = VersionRegistry(registry_path)
    registry.upsert(commit_hash="abc123", version="0.0.1")
    registry.upsert(commit_hash="abc123", version="0.0.2")

    reopened = VersionRegistry(registry_path)
    record = reopened.get_by_commit("abc123")
    assert record is not None
    assert record.version == "0.0.2"
    by_version = reopened.get_by_version("0.0.2")
    assert by_version is not None
    assert by_version.commit_hash == "abc123"
