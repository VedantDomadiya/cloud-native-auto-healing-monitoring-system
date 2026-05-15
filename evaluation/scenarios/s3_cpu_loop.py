"""S3: HighCPU. Spawn CPU-burning threads inside the service."""
from __future__ import annotations

from .. import fault_injector as fi

ID = "S3"
NAME = "cpu_loop"
DESCRIPTION = "Pin service-a's CPU above 95% for >1 minute."
TARGET_SERVICE = "service-a"


def inject(service: str = TARGET_SERVICE) -> None:
    # 3 burners running concurrently is plenty to push past 0.95 for a minute.
    fi.post_endpoint(service, "/burn-cpu", repeat=3)
