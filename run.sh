#!/usr/bin/env bash
# EATGOOD — Single-Command Local Launch Script
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "============================================================"
echo "🌱 Starting EATGOOD AI Platform..."
echo "============================================================"

# Check venv
if [ ! -d "backend/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv backend/venv
    source backend/venv/bin/activate
    pip install --upgrade pip
    pip install fastapi uvicorn pandas numpy scikit-learn joblib pydantic pytest python-multipart
else
    source backend/venv/bin/activate
fi

# Build frontend if dist missing
if [ ! -d "frontend/dist" ]; then
    echo "Building frontend bundle..."
    cd frontend && npm install && npm run build && cd ..
fi

echo "------------------------------------------------------------"
echo "🚀 Launching EATGOOD server at: http://127.0.0.1:8000"
echo "------------------------------------------------------------"
PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8000
