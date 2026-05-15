# Cloud-Native Auto-Healing Monitoring System

Self-healing observability stack implementing the **MAPE-K** reference model
(Monitor → Analyse → Plan → Execute → Knowledge), built with open-source
components only. Detects faults in containerized workloads via Prometheus
alerts and remediates them automatically through a Python webhook that can
act against Docker or Kubernetes APIs.

Developed as an M.E. Computer Engineering mini project (GTU, 2026).

---

## Architecture

| MAPE-K Stage | Component                                                    |
|--------------|--------------------------------------------------------------|
| **Monitor**  | Prometheus scraping demo services, node-exporter, cAdvisor   |
| **Analyse**  | PromQL alert rules evaluated continuously                    |
| **Plan**     | Alertmanager routing alerts by labels                        |
| **Execute**  | Flask webhook calling Docker / Kubernetes APIs               |
| **Knowledge**| Prometheus TSDB (shared state)                               |

## Quick Start (Windows 11 + Docker Desktop)

```powershell
# Copy the env template and fill in a real WEBHOOK_TOKEN
Copy-Item .env.example .env

# Bring the full stack up
./make.ps1 up

# Live demo: inject a fault, watch the system auto-heal
./make.ps1 demo

# Stop everything cleanly
./make.ps1 down
```

For Linux / WSL there is an equivalent `Makefile`.
See [SETUP.md](SETUP.md) for prerequisites and troubleshooting.

## Fault Scenarios

| ID  | Detection rule                  | Remediation action |
|-----|---------------------------------|--------------------|
| S1  | ContainerDown (`up == 0` 30s)   | `restart_container` |
| S2  | HighMemory (>90% for 2m)        | `scale_out`         |
| S3  | HighCPU (>95% for 1m)           | `scale_out`         |
| S4  | ProbeFailing (`probe_success==0`) | `restart_container` |
| S5  | DependencyDown (5xx burst 1m)   | `capture_snapshot` + restart |

## Tech Stack (pinned)

- Prometheus 2.51.2, Grafana 11.0.0, Alertmanager 0.27.0
- node-exporter 1.7.0, cAdvisor 0.49.1
- Python 3.11 inside the webhook container; Flask 3.0, docker-py 7.0, kubernetes 29.0
- Minikube 1.33+, kubectl 1.29+
- Terraform 1.6+ (optional cloud track — single GCP e2-medium VM)

## Endpoints (default ports)

| Service       | URL                       |
|---------------|---------------------------|
| Grafana       | http://localhost:3000     |
| Prometheus    | http://localhost:9090     |
| Alertmanager  | http://localhost:9093     |
| Webhook       | http://localhost:5000     |
| cAdvisor      | http://localhost:8080     |

## Repository Layout

See `PROGRESS.md` for a build journal and the directory listing under `docs/`
for the full project report.

## License

Academic project. Source code is MIT-licensed.
