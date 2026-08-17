# USPC Media Service Production Container
FROM docker.io/library/python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies including FFmpeg 6.x
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml /app/
RUN pip install --no-cache-dir \
    fastapi>=0.100.0 \
    uvicorn>=0.23.0 \
    pydantic>=2.0.0 \
    pillow>=10.0.0 \
    pyyaml>=6.0.0 \
    psutil>=5.9.0 \
    jsonschema>=4.20.0 \
    cryptography>=41.0.0 \
    python-multipart>=0.0.6

# Copy application source code
COPY src/ /app/src/
COPY web/ /app/web/

ENV PYTHONPATH="/app/src"

EXPOSE 8085

USER 1000:1000

CMD ["python", "-m", "media.app"]
