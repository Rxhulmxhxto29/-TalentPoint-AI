# Production Dockerfile for TalentPoint AI
# Optimized for Hugging Face Spaces (CPU-only)

FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

# Copy the rest of the application (includes .streamlit/config.toml)
COPY . .

# Create directory for persistent data
RUN mkdir -p /app/data/embeddings /app/data/processed

# Expose port for Hugging Face Spaces
EXPOSE 7860

# Write entrypoint script using printf to avoid echo escape issues
RUN printf '#!/bin/bash\n\
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &\n\
streamlit run ui/app.py \\\n\
    --server.port 7860 \\\n\
    --server.address 0.0.0.0 \\\n\
    --server.enableXsrfProtection=false \\\n\
    --server.enableCORS=false \\\n\
    --server.maxUploadSize=200\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
