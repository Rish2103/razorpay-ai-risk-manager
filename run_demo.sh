#!/usr/bin/env bash
set -e

echo "======================================================================="
echo "   Starting Razorpay Abuse & RTO Defense Sentinel Pipeline"
echo "======================================================================="

echo "[1/2] Launching FastAPI Risk Ingestion Service on http://127.0.0.1:8000..."
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "Waiting for backend to initialize (PID: $BACKEND_PID)..."
sleep 3

echo "[2/2] Launching Streamlit Interactive Dashboard on http://localhost:8501..."
python -m streamlit run frontend/app.py --server.port 8501

kill $BACKEND_PID 2>/dev/null || true
