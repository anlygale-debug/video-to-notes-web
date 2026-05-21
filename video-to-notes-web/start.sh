#!/bin/bash
cd "$(dirname "$0")"
echo "🎬 Video to Notes Web App"
echo "========================="
source ~/.agent-reach-venv/bin/activate
pip install fastapi uvicorn 2>/dev/null | tail -1
echo ""
echo "Starting at http://localhost:3000"
echo "Press Ctrl+C to stop"
echo ""
uvicorn app:app --host 0.0.0.0 --port 3000 --reload
