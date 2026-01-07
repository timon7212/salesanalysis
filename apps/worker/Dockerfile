FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (only ffmpeg for audio conversion)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --timeout=300 -r requirements.txt

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /storage

CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info"]


