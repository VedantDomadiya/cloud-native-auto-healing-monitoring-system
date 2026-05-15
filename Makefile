# Makefile equivalent of make.ps1 for WSL / Linux users.
# Targets mirror the PowerShell script.

SHELL := /bin/bash

.PHONY: help up down clean status logs demo test \
        evaluate-smoke evaluate-pilot evaluate-full \
        cloud-up cloud-down

help:
	@echo "Usage: make <target>"
	@echo
	@echo "Targets:"
	@echo "  up              start the full stack"
	@echo "  down            stop containers (volumes preserved)"
	@echo "  clean           down + remove volumes + remove built images"
	@echo "  status          health summary of every component"
	@echo "  logs            tail webhook + alertmanager logs"
	@echo "  demo            scripted live demo (S1 fault + recovery)"
	@echo "  test            pytest on webhook"
	@echo "  evaluate-smoke  5-run smoke evaluation"
	@echo "  evaluate-pilot  50-run pilot evaluation"
	@echo "  evaluate-full   300-run full evaluation"
	@echo "  cloud-up        terraform apply"
	@echo "  cloud-down      terraform destroy"

up:
	@[ -f .env ] || cp .env.example .env
	docker compose up -d --build
	@echo
	@echo "Stack up. UIs:"
	@echo "  Grafana       http://localhost:3000  (admin/admin)"
	@echo "  Prometheus    http://localhost:9090"
	@echo "  Alertmanager  http://localhost:9093"
	@echo "  cAdvisor      http://localhost:8080"
	@echo "  service-a     http://localhost:8001"
	@echo "  service-b     http://localhost:8002"
	@echo "  service-c     http://localhost:8003"

down:
	docker compose down

clean:
	docker compose down -v --rmi local
	-rm -f evaluation/results/*.csv

status:
	docker compose ps
	@echo
	@echo "--- Prometheus scrape targets ---"
	@curl -s http://localhost:9090/api/v1/targets | python3 -c "\
import json,sys; \
d=json.load(sys.stdin); \
[print(f\"  {t['labels']['job']:<25} {t['health']:<10} {t['scrapeUrl']}\") for t in d['data']['activeTargets']]" \
	|| echo "  (Prometheus not reachable)"

logs:
	docker compose logs -f --tail=50 webhook alertmanager

demo:
	@echo "DEMO: S1 ContainerDown auto-heal"
	@docker ps --filter 'name=service-a' --format 'table {{.Names}}\t{{.Status}}'
	@echo "Killing service-a..."
	@docker kill service-a
	@echo "Waiting 90s for heal..."
	@sleep 90
	@docker ps --filter 'name=service-a' --format 'table {{.Names}}\t{{.Status}}'

test:
	docker compose run --rm webhook pytest /app/tests -v

evaluate-smoke:
	python3 evaluation/run_evaluation.py --mode smoke

evaluate-pilot:
	python3 evaluation/run_evaluation.py --mode pilot

evaluate-full:
	python3 evaluation/run_evaluation.py --mode full

cloud-up:
	cd terraform && terraform apply

cloud-down:
	cd terraform && terraform destroy
