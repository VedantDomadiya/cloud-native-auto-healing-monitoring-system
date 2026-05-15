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

### Phase 1 — Project scaffolding + Git init  *(in progress)*

- Created `.gitignore`, `README.md`, `PROGRESS.md`, `.env.example`
- Configured local git identity: `vedantdomadiya` / `vedantdomadiya1809@gmail.com`
- Initialized repo, added remote `origin` pointing to GitHub
- Initial commit + push

### Phase 2+ — Pending

- Phase 2: Flask demo services (service-a, service-b, service-c)
- Phase 3: Docker Compose observability stack
- Phase 4: Grafana container-summary dashboard
- Phase 5: PromQL alert rules + Alertmanager routing (S1 only)
- Phase 6: Webhook skeleton (Flask + docker-py)
- Phase 7: Wire S1 end-to-end and verify auto-heal
- Phase 8: End-of-session commit + push

---

## Session 2 — TBD

Goal: Remaining 4 fault scenarios, Kubernetes integration, evaluation harness,
Terraform validation, full polish.
