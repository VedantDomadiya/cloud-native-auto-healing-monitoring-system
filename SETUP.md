# Setup Guide

This document captures everything you need to reproduce the project on a clean
Windows 11 machine. The same steps work on Linux/macOS with minor adjustments.

---

## 1. Prerequisites

| Tool            | Version pin | Why                                          |
|-----------------|-------------|----------------------------------------------|
| Docker Desktop  | 25.x+       | Container runtime, WSL 2 backend             |
| Docker Compose  | v2 plugin   | Multi-container orchestration                |
| Python (host)   | 3.11/3.12   | Runs the evaluation harness on the host      |
| Git             | 2.30+       | Source control                               |
| Minikube        | 1.33+       | Optional (for the Kubernetes integration)    |
| kubectl         | 1.29+       | Bundled with Docker Desktop                  |
| Terraform       | 1.6+        | Optional (for the cloud track)               |

### Resource budget
- Docker Desktop allocation: 8 GB memory, 4 CPU, 30 GB disk (the project uses
  ~1 GB at runtime; the rest is headroom for builds and minikube).
- Close OneDrive / browser tabs / Slack before bringing the stack up if free
  RAM is below 6 GB.

---

## 2. First-time setup

```powershell
git clone https://github.com/VedantDomadiya/cloud-native-auto-healing-monitoring-system.git
cd cloud-native-auto-healing-monitoring-system
git config --global core.autocrlf input   # one-time, keeps LF in YAML/scripts
Copy-Item .env.example .env               # gitignored; tweak if you want
./make.ps1 up                             # builds 4 images, pulls 5, brings everything up
./make.ps1 status                         # prints scrape target health
```

Browser endpoints (default ports):

| Service       | URL                                       |
|---------------|-------------------------------------------|
| Grafana       | http://localhost:3000  (admin / admin)    |
| Prometheus    | http://localhost:9090                     |
| Alertmanager  | http://localhost:9093                     |
| cAdvisor      | http://localhost:8080                     |
| Webhook       | http://localhost:5000/healthz             |
| service-a/b/c | http://localhost:8001 / 8002 / 8003       |

---

## 3. Live demo

```powershell
./make.ps1 demo
```

This kills `service-a`, waits 90 seconds, and prints the recovered state.
The expected sequence:

1. `docker kill service-a` immediately at t=0.
2. Prometheus detects `up{job="demo-services",service="service-a"} == 0`.
3. After the 30-second `for:` clause, the `ContainerDown` alert fires.
4. Alertmanager forwards the alert to the webhook receiver.
5. Webhook calls `docker_client.restart_container("service-a")`.
6. service-a is back at roughly t=55 seconds.

You can also kill the container manually:
```powershell
docker kill service-a
# Watch http://localhost:9090/alerts and webhook logs in another window:
docker logs -f webhook
```

---

## 4. Evaluation

```powershell
./make.ps1 evaluate-smoke    # 5 runs (1 per scenario)         ~10 min
./make.ps1 evaluate-pilot    # 50 runs (10 per scenario)       ~2.5 h
./make.ps1 evaluate-full     # 300 runs (30 per scenario x 2)  ~15 h
python evaluation/analyze_results.py
```

Outputs:
- `evaluation/results/runs.csv` — one row per run, line-buffered (safe across crashes).
- `evaluation/results/summary.csv` — mean / stddev per scenario.
- `evaluation/results/report.md` — Markdown table ready to paste into Chapter 3.

---

## 5. Tests

```powershell
./make.ps1 test
```

This runs `pytest` inside the webhook container. Tests cover the dispatch
table, payload parsing, and audit log structure.

---

## 6. Kubernetes integration (optional)

The Docker-Compose path is the primary demo. The Kubernetes manifests in
`kubernetes/` prove the dispatch table's K8s code path is wired up.

```powershell
minikube start --driver=docker --memory=4g --cpus=2

# Build the demo images against minikube's docker daemon so it can find them:
& minikube docker-env --shell powershell | Invoke-Expression
docker compose build service-a service-b service-c

# Apply the manifests:
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/

# Verify:
kubectl -n demo get pods
kubectl -n demo logs deploy/service-b
```

The webhook's `k8s_client.delete_pod` looks up pods by `app=<service>` in
the `demo` namespace, which matches the manifests.

To stop:
```powershell
minikube stop
```

---

## 7. Cloud track (optional)

```powershell
cd terraform
terraform init
terraform validate                # syntax check only, no resources created
# To actually provision (requires gcloud auth and a real GCP project):
# terraform apply -var project_id=YOUR-PROJECT -var allowed_cidr=YOUR-IP/32 \
#                 -var ssh_public_key="$(Get-Content $HOME/.ssh/id_ed25519.pub)"
# terraform destroy   # tears everything back down
```

Estimated cost: ~$0.034/hr for the e2-medium VM, ~$0.27 for an 8-hour demo day.

---

## 8. Troubleshooting

### "docker command not found" after install
Existing PowerShell sessions don't see PATH updates installers make.
Either open a new shell, or refresh in-session:
```powershell
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path','User')
```

### Port already in use
The most common offender on Windows is a native Grafana install on port 3000.
Stop and disable the service from an **elevated** PowerShell:
```powershell
Stop-Service Grafana
Set-Service Grafana -StartupType Disabled
```

### Prometheus rule changes don't appear after editing `prometheus.yml`
Single-file bind mounts on Docker Desktop Windows don't always propagate
file replacements. Restart the container:
```powershell
docker compose restart prometheus
```

### `python` is the Microsoft Store stub instead of a real interpreter
Install a real Python via winget:
```powershell
winget install --id Python.Python.3.12 --scope user --silent
```

### Webhook returns 401
You set `WEBHOOK_TOKEN` in `.env` but Alertmanager isn't sending a matching
Bearer header. Either clear `WEBHOOK_TOKEN` for the demo or add a static
token to `alertmanager.yml`'s `webhook_configs` entry.

---

## 9. File map

```
.
├── README.md                    # overview + quick start
├── SETUP.md                     # this file
├── PROGRESS.md                  # build journal
├── docker-compose.yml           # the whole observability + demo stack
├── Makefile                     # WSL/Linux make targets
├── make.ps1                     # PowerShell equivalent
├── .env.example                 # env var template
├── prometheus/                  # scrape config + alert rules
├── alertmanager/                # routing config
├── grafana/                     # datasource + dashboard provisioning + JSON
├── blackbox/                    # HTTP probe module config
├── webhook/                     # Flask service + docker_client + k8s_client + tests
├── demo-services/               # service-a, service-b, service-c
├── kubernetes/                  # Deployment/Service manifests for the K8s path
├── evaluation/                  # scenarios + run_evaluation + analyze_results
└── terraform/                   # GCP e2-medium provisioning module
```
