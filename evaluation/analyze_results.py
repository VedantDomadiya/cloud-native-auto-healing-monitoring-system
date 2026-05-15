"""Summarize evaluation/results/runs.csv into summary.csv + report.md.

Outputs go in evaluation/results/ next to the raw CSV.
The Markdown table is shaped to drop straight into Chapter 3 (Table 3.4)
of the project report.

Run:
    python evaluation/analyze_results.py
"""
from __future__ import annotations

import csv
import math
import statistics as stats
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "evaluation" / "results"
RUNS_CSV = RESULTS_DIR / "runs.csv"
SUMMARY_CSV = RESULTS_DIR / "summary.csv"
REPORT_MD = RESULTS_DIR / "report.md"


def load_rows():
    if not RUNS_CSV.exists():
        return []
    with RUNS_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    rows = load_rows()
    if not rows:
        print(f"No data in {RUNS_CSV}. Did the evaluation run finish?")
        return 1

    # Group by (scenario_id, scenario_name)
    by_key: dict[tuple[str, str], list[float]] = {}
    outcomes: dict[tuple[str, str], dict[str, int]] = {}
    for r in rows:
        key = (r["scenario_id"], r["scenario_name"])
        outcomes.setdefault(key, {}).setdefault(r["outcome"], 0)
        outcomes[key][r["outcome"]] += 1
        if r["outcome"] == "recovered" and r["mttr_seconds"]:
            try:
                by_key.setdefault(key, []).append(float(r["mttr_seconds"]))
            except ValueError:
                pass

    summary_rows = []
    for key, mttrs in sorted(by_key.items()):
        sid, name = key
        n = len(mttrs)
        mean = stats.mean(mttrs)
        sd = stats.stdev(mttrs) if n > 1 else 0.0
        summary_rows.append(
            {
                "scenario_id": sid,
                "scenario_name": name,
                "n_recovered": n,
                "mttr_mean_s": round(mean, 2),
                "mttr_stddev_s": round(sd, 2),
                "mttr_min_s": round(min(mttrs), 2),
                "mttr_max_s": round(max(mttrs), 2),
                "outcomes": outcomes.get(key, {}),
            }
        )

    # Write summary.csv
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "scenario_id", "scenario_name", "n_recovered",
                "mttr_mean_s", "mttr_stddev_s", "mttr_min_s", "mttr_max_s",
            ],
        )
        w.writeheader()
        for r in summary_rows:
            w.writerow({k: r[k] for k in w.fieldnames})

    # Write report.md
    lines = [
        "# Evaluation Summary",
        "",
        f"Source: `{RUNS_CSV.relative_to(ROOT)}` ({len(rows)} runs)",
        "",
        "## MTTR by scenario (recovered runs only)",
        "",
        "| ID | Scenario | n | MTTR mean (s) | MTTR stddev (s) | MTTR min (s) | MTTR max (s) |",
        "|----|----------|---|---------------|-----------------|--------------|--------------|",
    ]
    for r in summary_rows:
        lines.append(
            f"| {r['scenario_id']} | {r['scenario_name']} | {r['n_recovered']} "
            f"| {r['mttr_mean_s']} | {r['mttr_stddev_s']} | {r['mttr_min_s']} | {r['mttr_max_s']} |"
        )
    lines += ["", "## Run outcomes", ""]
    lines += ["| ID | Scenario | Outcomes |", "|----|----------|----------|"]
    for r in summary_rows:
        outs = ", ".join(f"{k}={v}" for k, v in sorted(r["outcomes"].items()))
        lines.append(f"| {r['scenario_id']} | {r['scenario_name']} | {outs} |")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"summary -> {SUMMARY_CSV.relative_to(ROOT)}")
    print(f"report  -> {REPORT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
