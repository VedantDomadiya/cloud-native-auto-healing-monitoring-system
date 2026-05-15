"""Docker API client used by the webhook to act on containers.

Wraps the few docker-py calls we actually need. Every public function
returns a dict ready for the audit log and raises ``RemediationError``
on a known failure.
"""
from __future__ import annotations

from typing import Any, Dict

import docker
from docker.errors import APIError, NotFound

# Lazily initialized so unit tests don't try to talk to a real daemon.
_client = None


def _get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def restart_container(name: str) -> Dict[str, Any]:
    """Restart the container whose ``Name`` matches ``name``.

    Returns the container ID and pre/post status. Raises
    :class:`dispatch.RemediationError` if Docker can't be reached or the
    container doesn't exist.
    """
    from dispatch import RemediationError

    try:
        c = _get_client().containers.get(name)
        pre = c.status
        c.restart(timeout=10)
        c.reload()
        return {"id": c.short_id, "name": name, "pre_status": pre, "post_status": c.status}
    except NotFound as exc:
        raise RemediationError(f"container '{name}' not found") from exc
    except APIError as exc:
        raise RemediationError(f"docker API error restarting {name}: {exc}") from exc


def capture_logs(name: str, lines: int = 100) -> Dict[str, Any]:
    """Return the last N log lines of a container as part of a snapshot."""
    from dispatch import RemediationError

    try:
        c = _get_client().containers.get(name)
        raw = c.logs(tail=lines).decode("utf-8", errors="replace")
        return {"name": name, "lines": raw.splitlines()[-lines:]}
    except NotFound as exc:
        raise RemediationError(f"container '{name}' not found") from exc
    except APIError as exc:
        raise RemediationError(f"docker API error fetching logs for {name}: {exc}") from exc
