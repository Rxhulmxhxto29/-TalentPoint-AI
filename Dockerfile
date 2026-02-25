# Production Dockerfile for TalentPoint AI
# Optimized for Render/Railway (CPU-only)

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

# Copy the rest of the application
COPY . .

# Create directory for persistent data
RUN mkdir -p /app/data/embeddings /app/data/processed

# Expose ports for both FastAPI and Streamlit
EXPOSE 8000
EXPOSE 8501

# Entry point script to run both services
RUN echo '#!/bin/bash\n\
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &\n\
streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
