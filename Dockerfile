FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg + system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY backend/ .

# Optional: copy frontend (not needed for API-only, but good for health check)
COPY www/ /app/static/

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Start
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips *"]
