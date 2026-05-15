"""Unit tests for the structured JSON log format and idempotency window."""
from __future__ import annotations

import json
import logging
import sys
import time
from io import StringIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import JsonFormatter, _is_duplicate, _recent_actions  # noqa: E402


def _capture(fn, *args, **kwargs):
    """Run fn while capturing JSON log lines on a temporary stream handler."""
    log = logging.getLogger("webhook-test")
    log.handlers.clear()
    log.setLevel(logging.INFO)
    stream = StringIO()
    h = logging.StreamHandler(stream)
    h.setFormatter(JsonFormatter())
    log.addHandler(h)
    fn(log, *args, **kwargs)
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_json_formatter_outputs_valid_json():
    records = _capture(lambda log: log.info("hello"))
    assert len(records) == 1
    assert records[0]["msg"] == "hello"
    assert records[0]["level"] == "INFO"
    assert "ts" in records[0]


def test_json_formatter_includes_extra_fields():
    records = _capture(
        lambda log: log.info("alert", extra={"service": "service-a", "action": "restart"})
    )
    assert records[0]["service"] == "service-a"
    assert records[0]["action"] == "restart"


def test_json_formatter_serializes_unserializable_types():
    class Custom:
        def __str__(self):
            return "custom-value"

    records = _capture(lambda log: log.info("x", extra={"obj": Custom()}))
    assert records[0]["obj"] == "custom-value"


def test_idempotency_suppresses_duplicate_within_window():
    _recent_actions.clear()
    assert _is_duplicate("ContainerDown", "service-a") is False
    assert _is_duplicate("ContainerDown", "service-a") is True


def test_idempotency_allows_distinct_services():
    _recent_actions.clear()
    assert _is_duplicate("ContainerDown", "service-a") is False
    assert _is_duplicate("ContainerDown", "service-b") is False


def test_idempotency_allows_distinct_alertnames():
    _recent_actions.clear()
    assert _is_duplicate("ContainerDown", "service-a") is False
    assert _is_duplicate("HighMemory", "service-a") is False


def test_idempotency_releases_after_window(monkeypatch):
    import app as app_module

    _recent_actions.clear()
    fake_now = [1000.0]
    monkeypatch.setattr(app_module.time, "monotonic", lambda: fake_now[0])
    monkeypatch.setattr(app_module, "IDEMPOTENCY_WINDOW", 30)

    assert _is_duplicate("ContainerDown", "service-a") is False
    fake_now[0] += 31
    assert _is_duplicate("ContainerDown", "service-a") is False
