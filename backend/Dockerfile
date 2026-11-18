FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    NLTK_DATA=/usr/share/nltk_data

WORKDIR /app

# Install curl for container healthcheck and create data directory
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /usr/share/nltk_data /data

# Install pinned Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Download required NLTK datasets at build time
COPY scripts/download_nltk.py /app/download_nltk.py
RUN python /app/download_nltk.py && rm -f /app/download_nltk.py

# Copy backend application source
COPY backend/ /app/

# Expose API port
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
