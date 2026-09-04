import subprocess
import sys
import time
import requests
import os
import webbrowser

print("=" * 75)
print("   Starting Razorpay Abuse & RTO Defense Sentinel Pipeline")
print("=" * 75)

project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)

print("\n[1/2] Launching FastAPI Webhook Engine on http://127.0.0.1:8000...")
backend_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=project_dir
)

print("Waiting for backend to initialize (loading model & SHAP TreeExplainer)...")
online = False
for i in range(25):
    try:
        res = requests.get("http://127.0.0.1:8000/health", timeout=1.0)
        if res.status_code == 200:
            online = True
            print(">>> FastAPI Backend is ONLINE & HEALTHY!")
            break
    except Exception:
        pass
    time.sleep(1)

if not online:
    print(">>> Warning: Backend health check took longer than expected, proceeding...")

print("\n[2/2] Launching Streamlit Interactive Dashboard on http://localhost:8501...")
print("-" * 75)
print("  Interactive Dashboard URL : http://localhost:8501")
print("  FastAPI Swagger API Docs  : http://127.0.0.1:8000/docs")
print("-" * 75)

# Open dashboard in browser after a short delay
def open_browser():
    time.sleep(2)
    webbrowser.open("http://localhost:8501")

import threading
threading.Thread(target=open_browser, daemon=True).start()

try:
    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run", "frontend/app.py",
            "--server.port", "8501",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ],
        cwd=project_dir
    )
except KeyboardInterrupt:
    print("\nStopping services...")
finally:
    print("Shutting down backend process...")
    backend_proc.terminate()
    try:
        backend_proc.wait(timeout=3)
    except Exception:
        backend_proc.kill()
    print("All processes stopped.")
