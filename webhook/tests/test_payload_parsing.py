"""Unit tests for Alertmanager payload parsing."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import parse_alert  # noqa: E402


def _alert(**labels):
    return {"status": "firing", "labels": labels}


def test_parse_alert_extracts_all_fields():
    alert = _alert(
        alertname="ContainerDown",
        service="service-a",
        autoheal_action="restart_container",
        environment="docker",
        severity="critical",
    )
    parsed = parse_alert(alert)
    assert parsed["alertname"] == "ContainerDown"
    assert parsed["service"] == "service-a"
    assert parsed["autoheal_action"] == "restart_container"
    assert parsed["environment"] == "docker"
    assert parsed["status"] == "firing"


def test_parse_alert_defaults_environment_to_docker():
    alert = _alert(alertname="X", service="s", autoheal_action="restart_container")
    parsed = parse_alert(alert)
    assert parsed["environment"] == "docker"


def test_parse_alert_returns_empty_strings_for_missing_labels():
    parsed = parse_alert({"labels": {}, "status": "firing"})
    assert parsed["alertname"] == ""
    assert parsed["service"] == ""
    assert parsed["autoheal_action"] == ""


def test_parse_alert_preserves_resolved_status():
    alert = {"status": "resolved", "labels": {"alertname": "ContainerDown", "service": "service-a"}}
    parsed = parse_alert(alert)
    assert parsed["status"] == "resolved"


def test_parse_alert_handles_missing_labels_key():
    parsed = parse_alert({"status": "firing"})
    assert parsed["service"] == ""
    assert parsed["status"] == "firing"


def test_parse_alert_handles_kubernetes_environment():
    alert = _alert(
        alertname="ContainerDown",
        service="service-a",
        autoheal_action="restart_container",
        environment="kubernetes",
    )
    parsed = parse_alert(alert)
    assert parsed["environment"] == "kubernetes"
