"""service-b uses the same image template as service-a.

The only differences are injected at runtime via environment variables in
docker-compose.yml / the Kubernetes Deployment:

    SERVICE_NAME=service-b
    UPSTREAM_URL=http://service-a:8000   # so GET / proxies to service-a

Keeping the code identical keeps maintenance overhead low. See the module
docstring in ``demo-services/service-a/app.py`` for endpoint documentation.
"""
from __future__ import annotations

import os
import threading
import time
from typing import List

import requests
from flask import Flask, Response, jsonify
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

SERVICE_NAME: str = os.environ.get("SERVICE_NAME", "service-b")
PORT: int = int(os.environ.get("PORT", "8000"))
UPSTREAM_URL: str = os.environ.get("UPSTREAM_URL", "").strip()

app = Flask(__name__)

REQUESTS = Counter(
    "http_requests_total",
    "Count of HTTP requests handled by this service.",
    ["service", "method", "endpoint", "code"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "End-to-end request latency in seconds.",
    ["service", "endpoint"],
)
LEAKED_BYTES = Gauge(
    "demo_leaked_bytes",
    "Cumulative bytes retained by /leak-memory calls.",
    ["service"],
)

_leak: List[bytearray] = []
_cpu_lock = threading.Lock()
_cpu_burners = 0


def _cpu_burn(duration_seconds: float = 60.0) -> None:
    end = time.monotonic() + duration_seconds
    x = 0.0
    while time.monotonic() < end:
        x = (x + 1.0) * 1.000001


@app.route("/")
def root():
    with LATENCY.labels(SERVICE_NAME, "/").time():
        if UPSTREAM_URL:
            try:
                r = requests.get(f"{UPSTREAM_URL.rstrip('/')}/", timeout=2)
                code = r.status_code
                payload = r.json() if "application/json" in r.headers.get("Content-Type", "") else None
                REQUESTS.labels(SERVICE_NAME, "GET", "/", str(code)).inc()
                status = 200 if code == 200 else 502
                return (
                    jsonify(
                        service=SERVICE_NAME,
                        upstream_url=UPSTREAM_URL,
                        upstream_status=code,
                        upstream_data=payload,
                    ),
                    status,
                )
            except requests.exceptions.RequestException as exc:
                REQUESTS.labels(SERVICE_NAME, "GET", "/", "502").inc()
                return (
                    jsonify(
                        service=SERVICE_NAME,
                        upstream_url=UPSTREAM_URL,
                        error=str(exc),
                    ),
                    502,
                )
        REQUESTS.labels(SERVICE_NAME, "GET", "/", "200").inc()
        return jsonify(service=SERVICE_NAME, status="ok")


@app.route("/healthz")
def healthz():
    return jsonify(service=SERVICE_NAME, healthy=True), 200


@app.route("/readyz")
def readyz():
    return jsonify(service=SERVICE_NAME, ready=True), 200


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/burn-cpu", methods=["GET", "POST"])
def burn_cpu():
    global _cpu_burners
    with _cpu_lock:
        _cpu_burners += 1
        active = _cpu_burners
    threading.Thread(target=_cpu_burn, daemon=True).start()
    return jsonify(service=SERVICE_NAME, cpu_burners=active), 200


@app.route("/leak-memory", methods=["GET", "POST"])
def leak_memory():
    chunk = bytearray(50 * 1024 * 1024)
    _leak.append(chunk)
    total = sum(len(b) for b in _leak)
    LEAKED_BYTES.labels(SERVICE_NAME).set(total)
    return jsonify(service=SERVICE_NAME, total_leaked_mb=round(total / 1024 / 1024, 1)), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, threaded=True)
