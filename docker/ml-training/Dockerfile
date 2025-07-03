# Multi-stage build for ML Training
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY docker/ml-training/requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd -r mluser && useradd -r -g mluser mluser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code from the correct relative path
# Note: Build context should be project root, not docker/ml-training/
COPY --chown=mluser:mluser src/training/ /app/
COPY --chown=mluser:mluser src/__init__.py /app/

# Create necessary directories
RUN mkdir -p /app/data /app/models /app/logs /app/artifacts && \
    chown -R mluser:mluser /app

# Switch to non-root user
USER mluser

# Default command (can be overridden)
CMD ["python", "train.py"]
