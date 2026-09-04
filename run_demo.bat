@echo off
echo =======================================================================
echo   Starting Razorpay Abuse & RTO Defense Sentinel Pipeline
echo =======================================================================

echo [1/2] Starting FastAPI Risk Evaluation Backend on port 8000...
start "Razorpay Sentinel Backend (:8000)" cmd /k "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Streamlit Interactive Audit Dashboard on port 8501...
python -m streamlit run frontend/app.py --server.port 8501
