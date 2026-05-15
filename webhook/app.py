"""Auto-healing webhook (Execute stage of MAPE-K).

Receives Alertmanager webhook payloads, parses the autoheal labels, and
dispatches the appropriate remediation action. Returns 200 when every alert
in the batch was handled; 4xx/5xx with a reason otherwise.

Authentication:
    If WEBHOOK_TOKEN env var is set, requests must include
    ``Authorization: Bearer <token>``. If unset, the endpoint accepts any
    caller on the private Docker network (suitable for the in-cluster demo).

Idempotency:
    A short rolling window (default 30s) suppresses duplicate firings of the
    same (alertname, service) pair so flapping alerts don't cause restart
    storms.

Audit log:
    Every received alert is logged as one JSON object, both to stdout and
    to a rotating file under /var/log/webhook/.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import logging.handlers
import os
import threading
import time
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, request

from dispatch import DISPATCH, RemediationError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PORT: int = int(os.environ.get("PORT", "5000"))
WEBHOOK_TOKEN: str = os.environ.get("WEBHOOK_TOKEN", "").strip()
IDEMPOTENCY_WINDOW: float = float(os.environ.get("IDEMPOTENCY_WINDOW_SECONDS", "30"))
AUDIT_LOG_PATH: str = os.environ.get("AUDIT_LOG_PATH", "/var/log/webhook/audit.log")


# ---------------------------------------------------------------------------
# Structured JSON logging
# ---------------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "ts": _dt.datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        # Anything passed via the `extra=` kwarg becomes a top-level key.
        for k, v in record.__dict__.items():
            if k not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "message", "module",
                "msecs", "msg", "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName", "taskName",
            ):
                base[k] = v
        return json.dumps(base, default=str)


def _build_logger() -> logging.Logger:
    log = logging.getLogger("webhook")
    log.setLevel(logging.INFO)
    log.handlers.clear()

    stream = logging.StreamHandler()
    stream.setFormatter(JsonFormatter())
    log.addHandler(stream)

    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        rotating = logging.handlers.RotatingFileHandler(
            AUDIT_LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        rotating.setFormatter(JsonFormatter())
        log.addHandler(rotating)
    except OSError as exc:  # /var/log/webhook may not be writable in tests
        log.warning("Could not open audit log file at %s: %s", AUDIT_LOG_PATH, exc)

    log.propagate = False
    return log


log = _build_logger()


# ---------------------------------------------------------------------------
# Idempotency: drop duplicate (alertname, service) firings within the window
# ---------------------------------------------------------------------------
_recent_actions: Dict[Tuple[str, str], float] = {}
_recent_lock = threading.Lock()


def _is_duplicate(alertname: str, service: str) -> bool:
    key = (alertname, service)
    now = time.monotonic()
    with _recent_lock:
        last = _recent_actions.get(key)
        if last is not None and (now - last) < IDEMPOTENCY_WINDOW:
            return True
        _recent_actions[key] = now
        # Garbage-collect old entries so the dict doesn't grow forever.
        cutoff = now - IDEMPOTENCY_WINDOW * 2
        for k in [k for k, ts in _recent_actions.items() if ts < cutoff]:
            _recent_actions.pop(k, None)
        return False


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def _check_auth() -> bool:
    if not WEBHOOK_TOKEN:
        return True
    hdr = request.headers.get("Authorization", "")
    return hdr == f"Bearer {WEBHOOK_TOKEN}"


# ---------------------------------------------------------------------------
# Payload parsing
# ---------------------------------------------------------------------------
def parse_alert(alert: Dict[str, Any]) -> Dict[str, str]:
    """Pull the fields we care about out of an Alertmanager alert dict.

    Returns a dict with: alertname, service, autoheal_action, environment, status.
    Missing labels are returned as empty strings (the caller decides if that's fatal).
    """
    labels = alert.get("labels", {}) or {}
    return {
        "alertname": labels.get("alertname", ""),
        "service": labels.get("service", ""),
        "autoheal_action": labels.get("autoheal_action", ""),
        "environment": labels.get("environment", "docker"),
        "status": alert.get("status", "firing"),
    }


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.route("/healthz")
def healthz():
    return jsonify(healthy=True), 200


@app.route("/readyz")
def readyz():
    return jsonify(ready=True), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    if not _check_auth():
        log.warning("auth_failed", extra={"event": "auth_failed"})
        return jsonify(error="unauthorized"), 401

    payload = request.get_json(silent=True) or {}
    alerts: List[Dict[str, Any]] = payload.get("alerts", [])
    if not alerts:
        return jsonify(error="no alerts in payload"), 400

    results = []
    overall_ok = True

    for alert in alerts:
        parsed = parse_alert(alert)
        if parsed["status"] != "firing":
            # We only act on firing alerts. Resolutions are logged but skipped.
            log.info("alert_resolved", extra={"event": "alert_resolved", **parsed})
            results.append({**parsed, "action": "skipped_resolved"})
            continue

        if _is_duplicate(parsed["alertname"], parsed["service"]):
            log.info(
                "duplicate_suppressed",
                extra={"event": "duplicate_suppressed", **parsed},
            )
            results.append({**parsed, "action": "skipped_duplicate"})
            continue

        action_name = parsed["autoheal_action"]
        handler = DISPATCH.get(action_name)
        if handler is None:
            log.error(
                "no_dispatch_handler",
                extra={"event": "no_dispatch_handler", **parsed},
            )
            results.append({**parsed, "action": "unhandled", "error": f"no handler for '{action_name}'"})
            overall_ok = False
            continue

        try:
            outcome = handler(parsed["service"], parsed["environment"])
            log.info(
                "remediation_ok",
                extra={"event": "remediation_ok", **parsed, "outcome": outcome},
            )
            results.append({**parsed, "action": action_name, "outcome": outcome})
        except RemediationError as exc:
            log.error(
                "remediation_failed",
                extra={"event": "remediation_failed", **parsed, "error": str(exc)},
            )
            results.append({**parsed, "action": action_name, "error": str(exc)})
            overall_ok = False
        except Exception as exc:  # noqa: BLE001 - last-chance safety net
            log.exception(
                "remediation_crash",
                extra={"event": "remediation_crash", **parsed},
            )
            results.append({**parsed, "action": action_name, "error": f"crash: {exc}"})
            overall_ok = False

    status_code = 200 if overall_ok else 503
    return jsonify(handled=len(results), results=results), status_code


if __name__ == "__main__":
    log.info("webhook_starting", extra={"event": "webhook_starting", "port": PORT})
    app.run(host="0.0.0.0", port=PORT, threaded=True)
