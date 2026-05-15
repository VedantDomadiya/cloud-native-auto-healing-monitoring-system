"""S2: HighMemory. Allocate enough memory to cross the 90% threshold.

The demo service's /leak-memory endpoint reserves 50 MiB per call. With a
256 MiB cgroup limit, 6 calls cross the threshold and the kernel OOM-kills
the container (or memory pressure trips the rule before that). Either way
the auto-heal path applies.
"""
from __future__ import annotations

from .. import fault_injector as fi

ID = "S2"
NAME = "oom_stress"
DESCRIPTION = "Allocate ~300 MiB inside service-a until it crosses the memory ceiling."
TARGET_SERVICE = "service-a"


def inject(service: str = TARGET_SERVICE) -> None:
    # 6 calls × 50 MiB = ~300 MiB, well past the 90% threshold of 256 MiB.
    fi.post_endpoint(service, "/leak-memory", repeat=6)
