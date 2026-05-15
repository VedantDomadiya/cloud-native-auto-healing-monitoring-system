# PowerShell equivalent of the Makefile. Usage: ./make.ps1 <target>
#
# Targets:
#   up              start the full stack
#   down            stop and remove containers (volumes preserved)
#   clean           down + remove volumes + remove built images
#   status          health summary of every component
#   logs            tail webhook + alertmanager logs
#   demo            scripted live demo (S1 fault + recovery)
#   test            pytest on webhook
#   evaluate-smoke  5-run smoke evaluation
#   evaluate-pilot  50-run pilot evaluation
#   evaluate-full   300-run full evaluation
#   cloud-up        terraform apply
#   cloud-down      terraform destroy

[CmdletBinding()]
param(
  [Parameter(Position=0)]
  [string]$Target = 'help'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

# Refresh PATH from registry so freshly-installed tools (docker, minikube,
# kubectl, terraform) are visible without restarting the shell.
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path','User')

function _EnsureEnvFile {
  if (-not (Test-Path .env)) {
    Write-Host "No .env found - copying .env.example to .env" -ForegroundColor Yellow
    Copy-Item .env.example .env
  }
}

function Invoke-Up {
  _EnsureEnvFile
  Write-Host "Bringing observability stack up..." -ForegroundColor Cyan
  docker compose up -d --build
  Write-Host ""
  Write-Host "Stack up. UIs:" -ForegroundColor Green
  Write-Host "  Grafana       http://localhost:3000  (admin/admin)"
  Write-Host "  Prometheus    http://localhost:9090"
  Write-Host "  Alertmanager  http://localhost:9093"
  Write-Host "  cAdvisor      http://localhost:8080"
  Write-Host "  service-a     http://localhost:8001"
  Write-Host "  service-b     http://localhost:8002"
  Write-Host "  service-c     http://localhost:8003"
}

function Invoke-Down {
  Write-Host "Stopping stack..." -ForegroundColor Cyan
  docker compose down
}

function Invoke-Clean {
  Write-Host "Removing containers, volumes, and built images..." -ForegroundColor Yellow
  docker compose down -v --rmi local
  if (Test-Path evaluation/results) {
    Get-ChildItem evaluation/results -Filter '*.csv' -ErrorAction SilentlyContinue | Remove-Item -Force
  }
}

function Invoke-Status {
  docker compose ps
  Write-Host ""
  Write-Host "--- Prometheus scrape targets ---" -ForegroundColor Cyan
  try {
    $r = Invoke-RestMethod -Uri http://localhost:9090/api/v1/targets -TimeoutSec 3
    $r.data.activeTargets | ForEach-Object {
      $health = $_.health
      $color = if ($health -eq 'up') { 'Green' } else { 'Red' }
      Write-Host ("  {0,-25} {1,-10} {2}" -f $_.labels.job, $health, $_.scrapeUrl) -ForegroundColor $color
    }
  } catch {
    Write-Host "  (Prometheus not reachable yet)" -ForegroundColor Yellow
  }
}

function Invoke-Logs {
  docker compose logs -f --tail=50 webhook alertmanager
}

function Invoke-Demo {
  Write-Host "DEMO: S1 ContainerDown auto-heal" -ForegroundColor Cyan
  Write-Host ""
  Write-Host "Step 1: confirm service-a is healthy"
  docker ps --filter 'name=service-a' --format 'table {{.Names}}\t{{.Status}}'
  Start-Sleep -Seconds 2
  Write-Host ""
  Write-Host "Step 2: KILL service-a"
  docker kill service-a
  Write-Host "Watch Prometheus (http://localhost:9090/alerts) -- ContainerDown should fire in ~30s"
  Write-Host "Watch webhook logs -- it will restart the container"
  Write-Host ""
  Write-Host "(waiting 90s for the heal loop to complete...)"
  Start-Sleep -Seconds 90
  Write-Host ""
  Write-Host "Step 3: service-a state after auto-heal"
  docker ps --filter 'name=service-a' --format 'table {{.Names}}\t{{.Status}}'
}

function Invoke-Test {
  docker compose run --rm webhook pytest /app/tests -v
}

function Invoke-EvaluateSmoke  { python evaluation/run_evaluation.py --mode smoke }
function Invoke-EvaluatePilot  { python evaluation/run_evaluation.py --mode pilot }
function Invoke-EvaluateFull   { python evaluation/run_evaluation.py --mode full }

function Invoke-CloudUp    { Push-Location terraform; terraform apply;   Pop-Location }
function Invoke-CloudDown  { Push-Location terraform; terraform destroy; Pop-Location }

function Show-Help {
  Write-Host "Usage: ./make.ps1 <target>" -ForegroundColor Cyan
  Write-Host ""
  Write-Host "Targets:"
  @(
    'up              start the full stack',
    'down            stop containers (volumes preserved)',
    'clean           down + remove volumes + remove built images',
    'status          health summary of every component',
    'logs            tail webhook + alertmanager logs',
    'demo            scripted live demo (S1 fault + recovery)',
    'test            pytest on webhook',
    'evaluate-smoke  5-run smoke evaluation',
    'evaluate-pilot  50-run pilot evaluation',
    'evaluate-full   300-run full evaluation',
    'cloud-up        terraform apply',
    'cloud-down      terraform destroy'
  ) | ForEach-Object { Write-Host "  $_" }
}

switch ($Target) {
  'up'              { Invoke-Up }
  'down'            { Invoke-Down }
  'clean'           { Invoke-Clean }
  'status'          { Invoke-Status }
  'logs'            { Invoke-Logs }
  'demo'            { Invoke-Demo }
  'test'            { Invoke-Test }
  'evaluate-smoke'  { Invoke-EvaluateSmoke }
  'evaluate-pilot'  { Invoke-EvaluatePilot }
  'evaluate-full'   { Invoke-EvaluateFull }
  'cloud-up'        { Invoke-CloudUp }
  'cloud-down'      { Invoke-CloudDown }
  default           { Show-Help }
}
