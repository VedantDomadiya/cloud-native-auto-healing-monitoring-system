# Defence Demo Runbook

A step-by-step playbook for the GTU defence demo of the cloud-native
auto-healing monitoring stack. Read it once cold, then keep it open on a
phone or second screen during the demo.

Sleep mode (lid close) is what you want the night before — **do not shut
down Windows** because Docker Desktop has to fully restart from cold,
and that adds 2-3 min of risk you don't need.

---

## TONIGHT — before you close the lid

### One-time PowerShell setup (only needed if you have never run `make.ps1` on this machine)

Windows blocks unsigned local scripts by default. Allow them for your
user account (no admin needed, persists forever):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# Answer Y at the prompt.
```

You only do this once. After that, `./make.ps1 <target>` just works.

### Status check

Takes 5 seconds:

```powershell
cd E:\cloud-native-auto-healing-monitoring-stack
./make.ps1 status
```

You should see all 9 services `running`. If yes, **close the lid**.
Do not run `make.ps1 down` and do not shut down Windows.

---

## DEMO DAY — T-15 min, woken laptop

The order of operations matters. Do these one at a time.

### Step 1 (T-15): Open laptop, wait

1. Open the laptop, log in.
2. Watch the system tray (bottom-right) for Docker Desktop's whale icon.
3. The whale icon **animates while resuming** — wait until it stops moving
   (typically 30-60 s after wake).
4. Do not open the browser yet — give the stack 30 more seconds to settle
   after the whale stops animating.

### Step 2 (T-13): One-command health check

Open PowerShell in the project directory:

```powershell
cd E:\cloud-native-auto-healing-monitoring-stack
./make.ps1 status
```

Expected output:
- All 9 services in `running` state.
- All 9 scrape targets `up` (blackbox-http 3, demo-services 3, plus singletons).

**If anything is not running**, run this once:

```powershell
./make.ps1 up
```

Then wait 60 seconds and re-run `./make.ps1 status`.

### Step 3 (T-10): Open browser tabs in order

Open these 5 tabs in this exact order (so the muscle memory matches what
you will show):

| Tab | URL | What faculty will see |
|----|-----|-----------------------|
| 1 | http://localhost:3000/d/auto-healing-container-summary | Container Summary dashboard (the star of the demo) |
| 2 | http://localhost:9090/alerts | Prometheus alerts page (all green / inactive) |
| 3 | http://localhost:9093 | Alertmanager (silent — no alerts) |
| 4 | http://localhost:5000/healthz | Webhook health (`{"healthy":true}`) |
| 5 | https://github.com/VedantDomadiya/cloud-native-auto-healing-monitoring-system | GitHub repo |

In Grafana (tab 1): admin / admin, then **Ctrl+Shift+R** to hard-refresh.

### Step 4 (T-5): Rehearsal kill

Do the demo once silently, alone, to confirm everything works:

```powershell
docker kill service-a
```

Now keep an eye on the Container Summary dashboard:
- "Demo service liveness" panel for `service-a` flips from green UP to red
  DOWN within ~10 s.
- "Alerts firing now" briefly shows `ContainerDown`.
- "Restarts in last 10 min" for service-a jumps from 0 to 1 around the
  55-second mark.
- Liveness goes back to green.

Total: ~60 seconds. If this works, you are ready.

---

## THE DEMO ITSELF — 8 minutes

Walk faculty through these 6 beats. Tab numbers refer to the tabs you
opened in Step 3.

### Beat 1: Architecture (1 min)

"This is a self-healing observability stack following the MAPE-K model:
Monitor -> Analyse -> Plan -> Execute -> Knowledge. Prometheus scrapes
containers, PromQL alert rules detect faults, Alertmanager routes alerts
by labels, and my Python webhook executes remediation actions against the
Docker or Kubernetes API."

Open `README.md` from the repo or GitHub (tab 5). Show the MAPE-K table.

### Beat 2: The running stack (1 min)

Switch to tab 1 (Container Summary). Point at:
- All 3 services green / UP.
- Steady request rate (~3 req/s thanks to the load-generator).
- Memory and CPU panels showing baseline (~40 MB RSS each).

### Beat 3: Live auto-heal demo (3 min)

"I'll kill `service-a` and we'll watch the system detect and recover."

In PowerShell (kept side-by-side with the Grafana tab):

```powershell
docker kill service-a
```

Narrate while pointing at the dashboard:
- **t=10s**: "service-a liveness flips to DOWN".
- **t=40s**: "the `ContainerDown` alert reaches firing state — see Alerts panel".
- **t=55s**: "the webhook restarted the container — Restarts panel jumps to 1".
- **t=60s**: "liveness is back to UP. Total time: under one minute, no
  human in the loop."

### Beat 4: Evidence in the audit log (1 min)

Open a PowerShell pane:

```powershell
docker logs --tail 20 webhook
```

Point at the structured JSON line beginning with `"event":"remediation_ok"`.
Read it out: "Alertname ContainerDown, service service-a, action
restart_container, outcome pre_status exited, post_status running."

### Beat 5: The evaluation numbers (1 min)

Open the report:

```powershell
notepad evaluation\results\report.md
```

Or just show it in GitHub. Point at:
- **S1 docker_kill: 52.34 s MTTR** — the headline number, matches the live demo.
- **S2 / S3**: explain that those are Docker's restart-policy safety net
  catching faster than the alert pipeline — the `report.md` interpretation
  block has the full explanation.

### Beat 6: The repo (1 min)

Switch to tab 5 (GitHub). Show:
- 4 commits, each phase a separate commit.
- `kubernetes/` folder — proves the design supports K8s, dispatch table
  routes via `environment` label.
- `terraform/` folder — single GCP e2-medium VM provisioning, ~$0.034/hr.
- `evaluation/results/runs.csv` — actual smoke data.

---

## Q&A QUICK REFERENCE

| Question | Short answer |
|----------|--------------|
| **"What is the MTTR?"** | "~52 seconds for the webhook path. 30 s of that is a deliberate `for:` debounce on the alert; halving it cuts MTTR proportionally." |
| **"Why not Prometheus Operator / Helm?"** | "The MAPE-K loop is the focus of the project; an operator would add a layer of indirection between the alert and the action. With raw rules and a webhook, the chain from detection to remediation is visible end-to-end." |
| **"How does this scale?"** | "Single Prometheus + Alertmanager + webhook is fine to ~1000 containers per host. For larger fleets you run HA pairs of each — that's standard Prometheus federation. The dispatch table itself is stateless." |
| **"Does this work in Kubernetes?"** | "Yes — the webhook's dispatch table routes to `k8s_client` when the alert label `environment=kubernetes`. The manifests in `kubernetes/` are ready to `kubectl apply` against minikube." |
| **"What's the difference between this and Datadog / New Relic?"** | "Same observability stack pattern, but entirely open-source, self-hosted, no per-metric pricing. The auto-heal layer is custom — commercial APMs have integrations but not a single declarative dispatch table." |
| **"How do you handle alert storms?"** | "Two layers: Alertmanager `group_by` collapses related alerts, and the webhook has a 30-second idempotency window on `(alertname, service)` so a flapping alert can't trigger a restart storm." |
| **"What if the webhook is down?"** | "Alertmanager would log delivery failures and retry. The auto-heal stops, but the rest of the observability stack — metrics, dashboards, manual operator response — keeps working. There's no single point of failure for *observability*; the webhook is only the automation layer." |
| **"What about security?"** | "Bearer token auth on the webhook (env-var `WEBHOOK_TOKEN`), Docker socket mounted read-write but only inside the webhook container, and the demo Terraform locks the firewall to a single allowed CIDR." |

---

## IF SOMETHING BREAKS

### Stack is not running

```powershell
./make.ps1 up
./make.ps1 status
```

(60-second pause to wait for everything to come up.)

### Dashboards show "No data"

Hard-refresh: **Ctrl+Shift+R** in the browser tab. If still empty:

```powershell
docker compose restart grafana
```

Wait 15 seconds, refresh again.

### Auto-heal demo doesn't trigger within 90 seconds

Don't panic. Run:

```powershell
docker compose logs --tail 30 webhook
docker compose logs --tail 30 alertmanager
```

Likely cause: webhook restart suppressed by the idempotency window from
your rehearsal. Wait 60 seconds after the rehearsal before the live demo
(or kill `service-b` or `service-c` instead — the webhook treats each
service independently).

### Docker engine not responding

1. Right-click the whale icon in the tray.
2. Restart Docker Desktop.
3. Wait 2 minutes for the engine to come back.
4. `./make.ps1 status`.

### Port 3000 is suddenly in use (rare, after Windows updates)

```powershell
Get-NetTCPConnection -LocalPort 3000 -State Listen
# If something other than Docker Desktop owns it, stop that process.
docker compose restart grafana
```

### You accidentally `docker compose down`

```powershell
./make.ps1 up
# Wait 90 seconds.
./make.ps1 status
```

Volumes persist, so historical Prometheus data is still there.

---

## DO NOT — TONIGHT OR TOMORROW MORNING

- Don't run `./make.ps1 down`.
- Don't run `./make.ps1 clean` (it deletes the images and you'd have to rebuild).
- Don't shut down Windows; lid-close to sleep is fine.
- Don't install Windows updates if prompted — defer until after the defence.

---

## ENDPOINTS QUICK CARD

| Service       | URL                                       | Credentials |
|---------------|-------------------------------------------|-------------|
| Grafana       | http://localhost:3000                     | admin / admin |
| Prometheus    | http://localhost:9090                     | none        |
| Alertmanager  | http://localhost:9093                     | none        |
| cAdvisor      | http://localhost:8080                     | none        |
| Webhook       | http://localhost:5000/healthz             | none        |
| service-a     | http://localhost:8001                     | none        |
| service-b     | http://localhost:8002                     | none        |
| service-c     | http://localhost:8003                     | none        |

---

## COMMITS ON GITHUB (in order)

```
b8007a5  Fix dashboards: pin datasource uid, switch container metrics to process_*
135e606  Session 2: full fault matrix, evaluation harness, K8s + Terraform scaffolding
ec1989d  Session 1: end-to-end auto-heal working for S1 ContainerDown
15d2d22  Session 1: initial scaffolding
```

Repo: https://github.com/VedantDomadiya/cloud-native-auto-healing-monitoring-system
