#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Checking ffmpeg..."
if ! command -v ffmpeg >/dev/null; then
    echo "ffmpeg not found. Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)" >&2
    exit 1
fi

echo "Setting up backend venv..."
cd backend
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install -e ".[dev]" --quiet
deactivate
cd ..

echo "Installing frontend deps..."
cd frontend
npm install --silent
cd ..

echo "Done. Run scripts/run.sh to start both servers."
