Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "   Starting Razorpay Abuse & RTO Defense Sentinel Pipeline" -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan

 = Split-Path -Parent System.Management.Automation.InvocationInfo.MyCommand.Definition
Set-Location 

Write-Host "
[1/2] Launching FastAPI Webhook Ingestion Service on http://127.0.0.1:8000..." -ForegroundColor Green
 = Start-Process python -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000" -PassThru

Write-Host "Waiting for backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

Write-Host "
[2/2] Launching Streamlit Interactive Dashboard on http://localhost:8501..." -ForegroundColor Green
try {
    python -m streamlit run frontend/app.py --server.port 8501
} finally {
    Write-Host "
Stopping backend process (PID: )..." -ForegroundColor Yellow
    Stop-Process -Id .Id -Force -ErrorAction SilentlyContinue
}
