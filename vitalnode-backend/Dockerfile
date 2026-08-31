# ── VitalNode Backend Dockerfile ──────────────────────────────────────────
# Python 3.12 slim for minimal image size
FROM python:3.12-slim

# Metadata
LABEL maintainer="VitalNode Team"
LABEL description="VitalNode AI-assisted triage backend — Accenture Innovation Challenge 2026"

# Set working directory
WORKDIR /app

# Install system dependencies (PostgreSQL client libs for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (for Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user for security
RUN adduser --disabled-password --gecos "" vitalnode && \
    chown -R vitalnode:vitalnode /app
USER vitalnode

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
# Use --workers 1 for prototype (single process, no shared state issues)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
