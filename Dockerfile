FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg (required by yt-dlp for MP3 conversion)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY www/ /app/static/

EXPOSE 8000

# Use shell form so Railway's $PORT is interpolated
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips "*"
