# Multi-stage build for production optimization
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Add labels for metadata
LABEL maintainer="Cancer Genomics Team <support@cancer-genomics.com>" \
      org.opencontainers.image.title="Cancer Genomics Analysis Suite" \
      org.opencontainers.image.description="Comprehensive cancer genomics analysis suite with BLAST, annotation, ML, and reporting capabilities" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/your-org/cancer-genomics-analysis-suite" \
      org.opencontainers.image.licenses="MIT"

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    curl \
    perl \
    libperl-dev \
    r-base \
    r-base-dev \
    libxml2-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Seurat (attempt CRAN install; for full reproducibility, pin as needed)
RUN R -e "install.packages(c('Seurat','SeuratObject','Matrix','data.table'), repos='https://cloud.r-project.org')" || true

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 8050 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8050/health || exit 1

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "4", "--worker-class", "gevent", "--worker-connections", "1000", "--max-requests", "1000", "--max-requests-jitter", "100", "--timeout", "30", "--keep-alive", "2", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "main_dashboard:server"]
