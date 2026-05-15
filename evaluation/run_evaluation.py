"""Evaluation orchestrator.

Modes:
    --mode smoke   5 runs, 1 per scenario, baseline only (~15 min)
    --mode pilot   50 runs, 10 per scenario, baseline only (~2.5 h)
    --mode full    300 runs, 30 per scenario x 2 configs (~15 h)

Each run:
    1. Verifies the target service is healthy
    2. Injects the scenario's fault
    3. Records t_fault
    4. Polls /healthz every second until it succeeds (or 180 s timeout)
    5. Writes one CSV row to evaluation/results/runs.csv (line-buffered so
       a crash mid-run doesn't lose history)

Run from the repository root:

    python evaluation/run_evaluation.py --mode smoke
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib
import os
import sys
import time
from pathlib import Path

# Allow `python evaluation/run_evaluation.py` to import siblings.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation import fault_injector as fi  # noqa: E402

SCENARIOS = ["s1_docker_kill", "s2_oom_stress", "s3_cpu_loop", "s4_probe_block", "s5_dep_outage"]

RESULTS_DIR = ROOT / "evaluation" / "results"
RUNS_CSV = RESULTS_DIR / "runs.csv"
RECOVERY_TIMEOUT_SECONDS = 180


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--mode",
        choices=["smoke", "pilot", "full"],
        default="smoke",
        help="smoke=5, pilot=50, full=300 runs",
    )
    return ap.parse_args()


def runs_for_mode(mode: str) -> int:
    return {"smoke": 1, "pilot": 10, "full": 30}[mode]


def ensure_csv() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if not RUNS_CSV.exists():
        with RUNS_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                [
                    "ts_utc",
                    "scenario_id",
                    "scenario_name",
                    "target_service",
                    "fault_at_unix",
                    "recovered_at_unix",
                    "mttr_seconds",
                    "outcome",
                ]
            )


def warm_up(target: str, seconds: int = 5) -> bool:
    """Make sure the target service is healthy before we inject a fault."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if fi.healthz_ok(target):
            return True
        time.sleep(1)
    return False


def run_once(scenario_mod) -> dict:
    target = scenario_mod.TARGET_SERVICE
    if not warm_up(target, seconds=10):
        return {
            "scenario_id": scenario_mod.ID,
            "scenario_name": scenario_mod.NAME,
            "target_service": target,
            "fault_at_unix": "",
            "recovered_at_unix": "",
            "mttr_seconds": "",
            "outcome": "skipped_unhealthy_target",
        }

    fault_at = time.time()
    scenario_mod.inject()

    elapsed = fi.wait_for_recovery(target, timeout=RECOVERY_TIMEOUT_SECONDS)
    if elapsed is None:
        return {
            "scenario_id": scenario_mod.ID,
            "scenario_name": scenario_mod.NAME,
            "target_service": target,
            "fault_at_unix": f"{fault_at:.3f}",
            "recovered_at_unix": "",
            "mttr_seconds": "",
            "outcome": "timeout",
        }
    recovered_at = fault_at + elapsed
    return {
        "scenario_id": scenario_mod.ID,
        "scenario_name": scenario_mod.NAME,
        "target_service": target,
        "fault_at_unix": f"{fault_at:.3f}",
        "recovered_at_unix": f"{recovered_at:.3f}",
        "mttr_seconds": f"{elapsed:.3f}",
        "outcome": "recovered",
    }


def append_row(row: dict) -> None:
    with RUNS_CSV.open("a", newline="", encoding="utf-8", buffering=1) as f:
        csv.writer(f).writerow(
            [
                dt.datetime.utcnow().isoformat() + "Z",
                row["scenario_id"],
                row["scenario_name"],
                row["target_service"],
                row["fault_at_unix"],
                row["recovered_at_unix"],
                row["mttr_seconds"],
                row["outcome"],
            ]
        )


def cool_off(seconds: int = 45) -> None:
    """Give the system time to settle between runs (idempotency window + alert decay)."""
    time.sleep(seconds)


def main() -> int:
    args = parse_args()
    n_per_scenario = runs_for_mode(args.mode)
    ensure_csv()

    print(f"Mode: {args.mode}  ({n_per_scenario} run(s) per scenario, {len(SCENARIOS)} scenarios)")
    total_runs = 0

    for module_name in SCENARIOS:
        mod = importlib.import_module(f"evaluation.scenarios.{module_name}")
        for i in range(n_per_scenario):
            print(f"[{mod.ID}] run {i + 1}/{n_per_scenario}: {mod.NAME} - {mod.DESCRIPTION}")
            row = run_once(mod)
            append_row(row)
            total_runs += 1
            print(f"   outcome={row['outcome']}  mttr={row['mttr_seconds']}s")
            cool_off()

    print(f"Done. {total_runs} runs recorded in {RUNS_CSV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
