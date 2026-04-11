FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (graphviz needed by the graphviz Python package)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for runtime data
RUN mkdir -p uploads logs

# HF Spaces expects port 7860
ENV PORT=7860
EXPOSE 7860

# Use gunicorn for production; --preload ensures cleanup daemon starts once
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "2", "--threads", "4", "--timeout", "120", "--preload", "app:app"]
