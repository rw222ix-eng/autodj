# AutoDJ

Local tool that mixes two audio files into one with a natural-sounding transition.

See `docs/specs/2026-05-13-autodj-design.md` for the design and `docs/plans/2026-05-13-autodj-implementation.md` for the build plan.

## Run from source
```powershell
.\scripts\setup.ps1
.\scripts\run.ps1
```
Then open <http://localhost:5173>.

## Run as standalone .exe
After building (see below), launch:
```powershell
.\backend\dist\AutoDJ.exe
```
The .exe starts the backend on http://localhost:8000 and auto-opens your browser.
**Requires:** `ffmpeg` on PATH.

## Build the .exe yourself
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install pyinstaller
cd ..\frontend; npm run build
cd ..\backend; pyinstaller AutoDJ.spec --clean --noconfirm
```
Produces `backend\dist\AutoDJ.exe` (~250 MB).
