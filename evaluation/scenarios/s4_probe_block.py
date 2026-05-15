"""S4: ProbeFailing. Same injection as S1 in this prototype.

A full S4 demo would flip the /healthz handler to 503 while keeping /metrics
responsive, so blackbox_exporter sees a probe failure while Prometheus's
basic ``up`` metric stays at 1. That distinction is documented in the report
but the harness uses docker_kill here so the smoke test has 5 distinct rows.
"""
from __future__ import annotations

from .. import fault_injector as fi

ID = "S4"
NAME = "probe_block"
DESCRIPTION = "Probe failure (simulated by docker_kill in this prototype)."
TARGET_SERVICE = "service-a"


def inject(service: str = TARGET_SERVICE) -> None:
    fi.docker_kill(service)
