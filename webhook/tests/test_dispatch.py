"""Unit tests for the dispatch table.

These tests stub the Docker and Kubernetes clients so we can assert routing
without needing a daemon.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dispatch  # noqa: E402  (path manipulation above)
import docker_client  # noqa: E402
import k8s_client  # noqa: E402
from dispatch import DISPATCH, RemediationError  # noqa: E402


def test_dispatch_table_has_all_expected_actions():
    assert set(DISPATCH.keys()) == {"restart_container", "scale_out", "capture_snapshot"}


def test_dispatch_handlers_are_callable():
    for handler in DISPATCH.values():
        assert callable(handler)


def test_restart_container_docker_path(monkeypatch):
    called = {}

    def fake_restart(name):
        called["name"] = name
        return {"id": "abc123", "name": name, "pre_status": "running", "post_status": "running"}

    monkeypatch.setattr(docker_client, "restart_container", fake_restart)
    out = DISPATCH["restart_container"]("service-a", "docker")
    assert out["name"] == "service-a"
    assert called["name"] == "service-a"


def test_restart_container_kubernetes_path(monkeypatch):
    called = {}

    def fake_delete(service):
        called["service"] = service
        return {"service": service, "deleted": [f"{service}-pod-1"]}

    monkeypatch.setattr(k8s_client, "delete_pod", fake_delete)
    out = DISPATCH["restart_container"]("service-a", "kubernetes")
    assert out["service"] == "service-a"
    assert called["service"] == "service-a"


def test_scale_out_docker_falls_back_to_restart(monkeypatch):
    monkeypatch.setattr(
        docker_client,
        "restart_container",
        lambda name: {"name": name, "id": "x", "pre_status": "running", "post_status": "running"},
    )
    out = DISPATCH["scale_out"]("service-b", "docker")
    assert "note" in out
    assert "fell back" in out["note"]


def test_capture_snapshot_uses_capture_logs(monkeypatch):
    monkeypatch.setattr(
        docker_client,
        "capture_logs",
        lambda name, lines=100: {"name": name, "lines": ["line1", "line2"]},
    )
    out = DISPATCH["capture_snapshot"]("service-c", "docker")
    assert out["name"] == "service-c"
    assert out["lines"] == ["line1", "line2"]


def test_remediation_error_is_a_runtime_error():
    assert issubclass(RemediationError, RuntimeError)
