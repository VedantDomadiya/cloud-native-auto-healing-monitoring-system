FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Liveness check used by Docker's own --health and by Prometheus blackbox-style monitoring.
# Uses stdlib only so we don't pay extra image size.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; \
    r=urllib.request.urlopen('http://localhost:8000/healthz',timeout=2); \
    sys.exit(0 if r.status==200 else 1)" || exit 1

CMD ["python", "-u", "app.py"]
