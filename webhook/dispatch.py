"""Dispatch table mapping ``autoheal_action`` labels to handler functions.

Each handler has the signature ``(service: str, environment: str) -> dict``
and returns a JSON-serializable outcome dict that the webhook records in
the audit log. Handlers raise ``RemediationError`` on a recoverable failure
(e.g. Docker socket unreachable, container not found); any other exception
is caught upstream and treated as a crash.
"""
from __future__ import annotations

from typing import Any, Callable, Dict

import docker_client
import k8s_client


class RemediationError(RuntimeError):
    """Raised when a remediation action fails in a known way."""


def _restart_container(service: str, environment: str) -> Dict[str, Any]:
    if environment == "kubernetes":
        return k8s_client.delete_pod(service)
    # Default to Docker, which is the Session 1 path.
    return docker_client.restart_container(service)


def _scale_out(service: str, environment: str) -> Dict[str, Any]:
    if environment == "kubernetes":
        return k8s_client.scale_deployment(service, replicas_delta=+1)
    # Docker Compose doesn't support replicas the same way; we restart instead
    # and record a hint so the operator can review.
    out = docker_client.restart_container(service)
    out["note"] = "scale_out fell back to restart_container (docker env)"
    return out


def _capture_snapshot(service: str, environment: str) -> Dict[str, Any]:
    """Capture the last 100 log lines from the failing service for the report."""
    if environment == "kubernetes":
        return k8s_client.capture_logs(service, lines=100)
    return docker_client.capture_logs(service, lines=100)


# Public dispatch table. The webhook imports this dict directly.
DISPATCH: Dict[str, Callable[[str, str], Dict[str, Any]]] = {
    "restart_container": _restart_container,
    "scale_out": _scale_out,
    "capture_snapshot": _capture_snapshot,
}
