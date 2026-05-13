#!/usr/bin/env bash
# Build the standalone AutoDJ binary on macOS or Linux.
# On macOS produces backend/dist/AutoDJ.app and backend/dist/AutoDJ.
# On Linux produces backend/dist/AutoDJ.
set -euo pipefail
cd "$(dirname "$0")/.."

cd frontend
npm install --silent
npm run build
cd ..

cd backend
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install -e ".[dev]" --quiet
pip install pyinstaller --quiet

pyinstaller AutoDJ.spec --clean --noconfirm

echo "Build complete. Output: backend/dist/"
ls -la dist/
