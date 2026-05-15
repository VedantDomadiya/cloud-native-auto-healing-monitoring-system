"""Primitive fault-injection helpers used by the scenario modules.

Each function takes a service name (``service-a``) and triggers the fault
without waiting for recovery. The orchestrator (``run_evaluation.py``)
records timestamps and polls for recovery separately.
"""
from __future__ import annotations

import subprocess
import time
from typing import Tuple

import urllib.request
import urllib.error


SERVICE_PORTS = {"service-a": 8001, "service-b": 8002, "service-c": 8003}


def docker_kill(service: str) -> None:
    """Hard-kill a Docker container by name (SIGKILL)."""
    subprocess.run(
        ["docker", "kill", service],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def post_endpoint(service: str, path: str, repeat: int = 1) -> Tuple[int, str]:
    """POST to one of the demo endpoints (``/burn-cpu``, ``/leak-memory``).

    Returns (status_code, body) from the last call.
    """
    port = SERVICE_PORTS[service]
    url = f"http://localhost:{port}{path}"
    status, body = 0, ""
    for _ in range(repeat):
        req = urllib.request.Request(url, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                status, body = r.status, r.read().decode("utf-8", "replace")
        except urllib.error.URLError as exc:
            status, body = 0, f"unreachable: {exc}"
        time.sleep(0.2)
    return status, body


def healthz_ok(service: str, timeout: float = 1.0) -> bool:
    """True iff ``GET /healthz`` returns 200 with a healthy body."""
    port = SERVICE_PORTS.get(service)
    if port is None:
        return False
    url = f"http://localhost:{port}/healthz"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200 and b'"healthy"' in r.read()
    except (urllib.error.URLError, ConnectionResetError, TimeoutError):
        return False


def wait_for_recovery(service: str, timeout: float = 120.0, interval: float = 1.0) -> float | None:
    """Poll /healthz until it returns 200. Returns elapsed seconds, or None on timeout."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if healthz_ok(service):
            return time.monotonic() - start
        time.sleep(interval)
    return None
