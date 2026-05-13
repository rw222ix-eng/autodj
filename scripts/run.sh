#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Starting backend on http://localhost:8000 ..."
(cd "$ROOT/backend" && source .venv/bin/activate && uvicorn app.api:app --reload) &
BACKEND_PID=$!
sleep 2
echo "Starting frontend on http://localhost:5173 ..."
(cd "$ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
