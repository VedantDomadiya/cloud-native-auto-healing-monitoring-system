FROM python:3.11-slim

WORKDIR /app

# System-level dependency for Kubernetes client cert verification (kept slim).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py dispatch.py docker_client.py k8s_client.py ./
COPY tests ./tests

ENV PORT=5000 \
    PYTHONUNBUFFERED=1 \
    AUDIT_LOG_PATH=/var/log/webhook/audit.log

RUN mkdir -p /var/log/webhook

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; \
    r=urllib.request.urlopen('http://localhost:5000/healthz',timeout=2); \
    sys.exit(0 if r.status==200 else 1)" || exit 1

CMD ["python", "-u", "app.py"]
