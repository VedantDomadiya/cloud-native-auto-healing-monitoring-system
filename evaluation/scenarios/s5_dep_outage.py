"""S5: DependencyDown. Kill service-a so service-b starts returning 502s.

The harness tracks recovery on service-b (the dependent) rather than the
killed service-a, because the alert fires against service-b and the
capture_snapshot remediation gathers its logs.
"""
from __future__ import annotations

from .. import fault_injector as fi

ID = "S5"
NAME = "dep_outage"
DESCRIPTION = "Kill an upstream so the dependent service emits 5xx."

# We probe service-a's /healthz to measure recovery: as soon as the upstream
# is back, service-b's 502 stream stops. (service-b's own /healthz never
# went down, so probing that wouldn't give us a meaningful MTTR.)
TARGET_SERVICE = "service-a"
UPSTREAM = "service-a"


def inject(service: str = TARGET_SERVICE) -> None:
    fi.docker_kill(UPSTREAM)
