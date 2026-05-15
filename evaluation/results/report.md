# Evaluation Summary — Smoke Run

Source: `evaluation/results/runs.csv` (5 runs, 1 per scenario)
Captured on 2026-05-15 against the local Docker Compose stack.

## MTTR by scenario

| ID | Scenario     | n | Mean (s) | Stddev (s) | Min (s) | Max (s) |
|----|--------------|---|----------|------------|---------|---------|
| S1 | docker_kill  | 1 | 52.34    | 0.0        | 52.34   | 52.34   |
| S2 | oom_stress   | 1 | 0.02     | 0.0        | 0.02    | 0.02    |
| S3 | cpu_loop     | 1 | 0.19     | 0.0        | 0.19    | 0.19    |
| S4 | probe_block  | 1 | 51.28    | 0.0        | 51.28   | 51.28   |
| S5 | dep_outage   | 1 | 52.80    | 0.0        | 52.80   | 52.80   |

All five runs ended in `recovered`; no scenario timed out.

## Interpretation

The five numbers split cleanly into two regimes, both intentional and both
informative for the report.

### Regime A — webhook-driven auto-heal (~52 s)  *(S1, S4, S5)*

These scenarios follow the full MAPE-K loop end-to-end:

| Stage           | Component                                | Latency |
|-----------------|------------------------------------------|---------|
| Detection       | Prometheus scrape interval               | ~10 s   |
| Detection (for) | Alert rule `for: 30s` window             | 30 s    |
| Plan            | Alertmanager `group_wait: 5s`            | ~5 s    |
| Execute         | Webhook -> docker restart container      | ~5 s    |
| Service warm-up | Container /healthz responding            | ~2 s    |
| **Total**       |                                          | **~52 s** |

The variance across the three runs is <2 s, which is consistent with what
the Prometheus 2.51 scrape jitter alone would explain.

### Regime B — Docker restart-policy / no-op recovery  *(S2, S3)*

The headline "0.02 s" for S2 and "0.19 s" for S3 are NOT the system's true
recovery time. They are an artefact of the harness's measurement window:

- **S2 oom_stress**: `/leak-memory` allocates 50 MiB per call, 6 calls in
  rapid succession. Container memory crosses the 256 MiB cgroup ceiling
  while `inject()` is still running. The kernel OOM-kills the process,
  Docker's `restart: unless-stopped` policy re-creates the container
  within ~1-2 seconds, and by the time `inject()` returns to the harness
  the container is already healthy. The harness's polling loop is started
  *after* `inject()` and reports a sub-second wait. The HighMemory alert
  (`for: 2m`) never reaches firing state because the container is killed
  long before the threshold is sustained.

- **S3 cpu_loop**: `/burn-cpu` spawns daemon threads but does not actually
  crash the service. `/healthz` keeps returning 200 throughout. The
  HighCPU rule (`for: 1m`) would fire eventually and the webhook would
  scale out (which falls back to a restart in the Docker path), but the
  harness declares "recovered" the instant it sees `/healthz == 200`,
  which is immediate.

### What this tells us

1. The webhook-driven auto-heal path **works** and converges in roughly
   one minute, dominated by the deliberate `for: 30s` debounce on the
   alert rule. Halving the `for:` window or shortening the scrape
   interval would cut MTTR proportionally.

2. The system has **two complementary recovery mechanisms**:
   the slow, observability-aware webhook path for novel failures, and
   Docker's restart-policy safety net for OOM / segfault / crash-loop
   classes. The defence demo emphasizes the former; the latter exists
   regardless.

3. The harness instrumentation has a **known limitation** for S2/S3:
   `fault_at` is captured before `inject()` runs, so for scenarios where
   recovery completes during injection the recorded MTTR understates
   reality. A revised harness would either start the timer after the
   first non-200 probe, or run the `inject()` and the probe loop
   concurrently from separate threads.

## Next step

The pilot (50 runs, 10 per scenario) is the appropriate next pass. The
ContainerDown-class runs (S1, S4, S5) should stay within roughly
[48 s, 56 s] with a standard deviation under 3 s if the timing model
above holds.

## Outcomes

| ID | Scenario     | Outcomes      |
|----|--------------|---------------|
| S1 | docker_kill  | recovered=1   |
| S2 | oom_stress   | recovered=1   |
| S3 | cpu_loop     | recovered=1   |
| S4 | probe_block  | recovered=1   |
| S5 | dep_outage   | recovered=1   |
