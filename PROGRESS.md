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

## Session 2 — TBD

Goal: Remaining 4 fault scenarios, Kubernetes integration, evaluation harness,
Terraform validation, full polish.
