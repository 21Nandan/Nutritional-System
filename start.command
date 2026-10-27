#!/usr/bin/env bash
# EATGOOD — Double-Click Finder Launcher for macOS
cd "$(dirname "$0")"

echo "============================================================"
echo "🌱 Starting EATGOOD AI Platform..."
echo "============================================================"

# Ensure virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "Setting up Python virtual environment..."
    python3 -m venv backend/venv
    source backend/venv/bin/activate
    pip install --upgrade pip
    pip install fastapi uvicorn pandas numpy scikit-learn joblib pydantic pytest python-multipart
else
    source backend/venv/bin/activate
fi

# Ensure frontend build exists
if [ ! -d "frontend/dist" ]; then
    echo "Building frontend bundle..."
    cd frontend && npm install && npm run build && cd ..
fi

echo "------------------------------------------------------------"
echo "🚀 Launching EATGOOD at http://127.0.0.1:8000"
echo "------------------------------------------------------------"

# Open browser automatically after 1.5 seconds in background
(sleep 1.5 && open "http://127.0.0.1:8000") &

PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8000
