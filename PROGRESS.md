# Build Progress

A running journal of how this system was assembled.
The defence demo is **2026-05-16**; build was condensed into a single intensive session.

---

## Session 1 — 2026-05-13 → 2026-05-15

### Pre-flight checks

| Date        | Item                                            | Outcome |
|-------------|-------------------------------------------------|---------|
| 2026-05-13  | Tooling survey                                  | Docker / Minikube / kubectl / Terraform missing; Python 3.14.2 OK; Git OK; WSL kernel 2.6.1.0 OK |
| 2026-05-13  | Python pin decision                             | Keep host on 3.14; pin 3.11 inside Dockerfile (`python:3.11-slim`) for webhook runtime reproducibility |
| 2026-05-13  | Install Docker Desktop                          | v29.4.3 engine running, 7.62 GB / 12 CPU allocated |
| 2026-05-14  | Port conflict: 3000                             | Native Grafana Windows service was running. Stopped + uninstalled. |
| 2026-05-15  | Install Minikube                                | v1.38.1 at `E:\Minikube\minikube.exe` |
| 2026-05-15  | kubectl                                         | v1.34.1 bundled with Docker Desktop, on PATH |
| 2026-05-15  | Re-scan ports 3000/5000/8080/9090/9093          | All free |
| 2026-05-15  | Free RAM check                                  | 5.77 GB free of 15.73 GB. Sufficient for stack (~1 GB demand) but close apps before bringing compose up |

### Phase 1 — Project scaffolding + Git init  *(done)*

- Created `.gitignore`, `README.md`, `PROGRESS.md`, `.env.example`
- Configured local git identity (`vedantdomadiya` / `vedantdomadiya1809@gmail.com`)
- Initialized repo, added remote `origin`, initial commit `15d2d22` pushed

### Phase 2 — Demo Flask services  *(done)*

- `service-a` (independent), `service-b` (depends on service-a), `service-c` (control)
- Each exposes `/`, `/healthz`, `/readyz`, `/metrics`, `/burn-cpu`, `/leak-memory`
- Metrics: `http_requests_total`, `http_request_duration_seconds`, `demo_leaked_bytes`
- Per-service Dockerfile with stdlib-only HEALTHCHECK
- Fixed a duplicate-kwarg bug in service-a's upstream branch before first build

### Phase 3 — Docker Compose observability stack  *(done)*

- 9 services: prometheus + grafana + alertmanager + node-exporter + cadvisor + webhook + 3 demo
- Single bridge network (`obs-net`); named volumes for prometheus/grafana/alertmanager data
- All scrape targets healthy at first boot

### Phase 4 — Container summary Grafana dashboard  *(done)*

- Provisioned automatically via `grafana/provisioning/dashboards/dashboards.yml`
- Panels: container CPU rate, container memory working-set, demo liveness, request rate

### Phase 5 — Alert rule + Alertmanager routing  *(done)*

- `ContainerDown` rule: `up{job="demo-services"} == 0` for 30s
- Labels: `severity`, `autoheal_action`, `service`, `environment`
- Alertmanager routes alerts matching `autoheal_action =~ ".+"` to the webhook receiver

### Phase 6 — Auto-healing webhook  *(done)*

- Flask + docker-py, dispatch table indexed by `autoheal_action`
- Structured JSON audit log (stdout + rotating 10 MB file)
- Idempotency window suppresses duplicate (alertname, service) firings within 30 s
- Optional bearer-token auth (disabled in the demo for simplicity)
- Health endpoints at `/healthz` and `/readyz`
- Unit tests for dispatch, payload parsing, and audit log structure

### Phase 7 — S1 auto-heal verified end-to-end  *(done)*

Timeline of a recorded kill-and-heal cycle:

| t (s) | Event |
|-------|-------|
|  0.0  | `docker kill service-a` |
|  5.4  | Container observed in `exited` state |
| ~10.0 | Prometheus scrape detects `up == 0` |
| ~40.0 | Alert `ContainerDown` transitions to firing (30 s `for`) |
| ~45.0 | Alertmanager group window closes; webhook POST sent |
| 56.5  | Container observed `running`; StartedAt advanced |
| 57.0  | service-a `/healthz` responding again |

Webhook log line:
```json
{"event":"remediation_ok","alertname":"ContainerDown","service":"service-a",
 "autoheal_action":"restart_container","environment":"docker",
 "outcome":{"pre_status":"exited","post_status":"running"}}
```

### Phase 8 — Commit and push  *(done)*

Single Session-1 commit pushed to `origin/main` covering Phases 1-7.

---

## Session 2 — 2026-05-15 (continued)

Original plan was to spread Session 2 over a separate day, but with the
defence on 2026-05-16 we rolled the work into the same intensive sitting.

### Phase 9-10 — Blackbox probe + S2-S5 alert rules *(done)*

- Added `prom/blackbox-exporter:v0.25.0` to compose with a custom `http_2xx`
  module that requires `"healthy": true` in the response body.
- Updated `prometheus.yml` with the `blackbox-http` scrape job using
  standard relabel rules to feed targets through the exporter.
- Added 4 alert rules to `prometheus/rules/alert-rules.yml`:
  - **HighMemory** (S2): `working_set / limit > 0.9` for 2 m -> `scale_out`
  - **HighCPU** (S3): `rate(container_cpu_usage[1m]) > 0.95` for 1 m -> `scale_out`
  - **ProbeFailing** (S4): `probe_success == 0` for 30 s -> `restart_container`
  - **DependencyDown** (S5): `5xx burst by service > 1` for 1 m -> `capture_snapshot`
- `mem_limit: 256m` added to demo services so S2's denominator is meaningful.
- After a `docker compose restart prometheus` (single-file bind mounts
  don't always propagate on Windows), all 5 rules are `health=ok` and all
  9 scrape targets (blackbox-http x 3, demo-services x 3, plus the singletons)
  are `up`.

### Phase 11 — Evaluation harness *(done)*

- `evaluation/fault_injector.py`: docker_kill, post_endpoint, healthz_ok,
  wait_for_recovery (stdlib-only -- urllib + subprocess).
- 5 scenario modules under `evaluation/scenarios/`.
- `evaluation/run_evaluation.py`: smoke / pilot / full modes with
  line-buffered CSV writes for crash safety.
- `evaluation/analyze_results.py`: produces summary.csv and report.md
  shaped for Chapter 3 Table 3.4 of the report.
- Smoke run launched in background; CSV being written incrementally.

### Phase 12 — Kubernetes integration *(manifests done)*

- `kubernetes/namespace.yaml` plus three Deployment+Service manifests
  matching the Compose service set.
- Pods are labeled `app=<service>` so the webhook's
  `k8s_client.delete_pod` lookup works out of the box.
- `imagePullPolicy: IfNotPresent` keeps minikube from chasing the registry
  for images we built locally.
- Live deployment on minikube is documented in `SETUP.md` section 6 but
  intentionally not run during this session to avoid memory contention
  with the running evaluation.

### Phase 13 — Terraform module *(files written)*

- GCP provider, e2-medium VM, ephemeral public IP, firewall locked to
  `var.allowed_cidr` for the demo ports (3000/5000/9090/9093) plus open SSH.
- `startup.sh` installs Docker / Compose / Minikube / kubectl / Python 3.11
  on Ubuntu 22.04 and clones the project repo as the demo user.
- Cost: ~$0.034/hr (~$0.27 for an 8-hour demo day).
- `terraform validate` deferred -- requires the Terraform CLI which isn't
  installed locally; the module is self-contained and ready to validate.

### Phase 14 — Smoke evaluation results

5 scenarios, 1 run each. All scenarios ended in `recovered`.

| ID | Scenario     | MTTR (s) | Notes |
|----|--------------|----------|-------|
| S1 | docker_kill  | 52.34    | Full MAPE-K loop: 30s `for` + scrape + alertmanager + webhook |
| S2 | oom_stress   | 0.02     | Docker `restart: unless-stopped` healed before harness probe started |
| S3 | cpu_loop     | 0.19     | Service never died; `for: 1m` alert would fire but harness reports immediately |
| S4 | probe_block  | 51.28    | Same path as S1 in this prototype |
| S5 | dep_outage   | 52.80    | Upstream restart drives recovery; service-b 5xx clears with service-a |

The two regimes (~52 s webhook path vs. sub-second Docker restart policy)
are intentional and informative -- see `evaluation/results/report.md` for
the full interpretation.

### Phase 15 — Final commit + push *(done at end of session)*

All Session 2 deliverables landed in one final commit so the GitHub repo
matches the state demonstrated live.

### Phase 16 — Dashboard fix-up *(post-Session-2)*

Screenshots of the live Grafana dashboards showed every panel rendering
"No data". Two root causes; both fixed:

1. **Datasource UID mismatch.** The provisioned datasource auto-generated
   a random UID, but the dashboard JSONs all referenced `uid: prometheus`.
   Fixed by pinning `uid: prometheus` on
   `grafana/provisioning/datasources/prometheus.yml` and recreating Grafana.

2. **cAdvisor cannot enumerate individual containers on Docker Desktop's
   WSL 2 backend.** Adding `--docker_only=true` to cAdvisor's command did
   not help -- it still only emits cgroup-root series with no `name`
   label. Replaced the container CPU / memory / restart panels and the
   S2 / S3 alert rules to use the demo services' own
   `process_resident_memory_bytes`, `process_cpu_seconds_total`, and
   `process_start_time_seconds` metrics (auto-exported by
   `prometheus_client`). These are pre-labeled with `service=service-X`
   via the Prometheus scrape config relabeling, so panels render
   immediately and the restart count panel shows clean evidence of an
   auto-heal cycle.

Also added a `busybox` load-generator container that hits each demo
service once per second, so the Application Performance dashboard always
has request-rate / latency data to chart even when no fault is being
injected.

Other improvements while in there:
- Container Summary picked up two new stat panels: "Restarts in last
  10 min" and "Alerts firing now".
- Host Overview picked up three current-value stat panels at the top
  (CPU busy, memory used, load average) for at-a-glance status.
- Application Performance picked up three stat panels (current req/s,
  error fraction, p95 latency) plus a status-code breakdown timeseries.
- Default time range tightened from 30 min to 15 min on all three
  dashboards; refresh interval dropped from 10 s to 5 s.
