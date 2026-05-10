#!/bin/bash

# 1. Start the FastAPI Backend in the background
# We run it on port 8000 so the Frontend can find it at localhost:8000
echo "🚀 Starting FastAPI Backend..."
python -m uvicorn Backend.api:app --host 0.0.0.0 --port 8000 &

# 2. Wait a few seconds for the backend to initialize models
sleep 5

# 3. Start the Streamlit Frontend in the foreground
# Hugging Face Spaces requires port 7860
echo "💎 Starting Streamlit Frontend..."
python -m streamlit run Frontend/app.py --server.port 7860 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
