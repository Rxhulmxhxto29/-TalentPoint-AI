#!/bin/bash
# entrypoint.sh — Start both services for TalentPoint AI

# 1. Start FastAPI in background
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &

# 2. Start Streamlit with all required HF proxy flags
streamlit run ui/app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.enableXsrfProtection false \
    --server.enableCORS false \
    --server.maxUploadSize 200 \
    --browser.gatherUsageStats false
