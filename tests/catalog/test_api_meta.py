"""Tests for ``GET /meta`` (UI footer versions)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from schema import DATA_FORMAT_VERSION
from catalog.api.main import create_app


def test_meta_reports_versions(monkeypatch):
    monkeypatch.setenv("PORTAL_VERSION", "v9.9.9")
    client = TestClient(create_app())
    body = client.get("/meta").json()
    assert body == {
        "portal_version": "v9.9.9",
        "data_format_version": DATA_FORMAT_VERSION,
    }


def test_meta_portal_version_defaults_to_dev(monkeypatch):
    monkeypatch.delenv("PORTAL_VERSION", raising=False)
    client = TestClient(create_app())
    assert client.get("/meta").json()["portal_version"] == "dev"
