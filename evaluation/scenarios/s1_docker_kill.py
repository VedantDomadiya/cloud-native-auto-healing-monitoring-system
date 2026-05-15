"""S1: ContainerDown. Hard-kill the container; wait for the webhook to restart it."""
from __future__ import annotations

from .. import fault_injector as fi

ID = "S1"
NAME = "docker_kill"
DESCRIPTION = "Hard-kill the container; webhook restarts it via the Docker API."
TARGET_SERVICE = "service-a"


def inject(service: str = TARGET_SERVICE) -> None:
    fi.docker_kill(service)
