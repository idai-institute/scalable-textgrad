from __future__ import annotations

from scalable_textgrad.registry import VersionRegistry


def test_registry_persists(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry = VersionRegistry(registry_path)
    registry.register_service(
        commit_hash="abc123",
        version="0.0.1",
        component="runner",
        base_url="http://localhost:9000",
    )
    registry.upsert(
        commit_hash="abc123",
        version="0.0.1",
        changelog_uri="https://example/changelog",
        tags=["stable"],
    )

    reopened = VersionRegistry(registry_path)
    record = reopened.get_by_commit("abc123")
    assert record is not None
    assert record.runner is not None
    assert record.runner.base_url == "http://localhost:9000"
    assert record.changelog_uri == "https://example/changelog"
    assert "stable" in record.tags
