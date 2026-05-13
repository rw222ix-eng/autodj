# AutoDJ

Local tool that mixes two audio files into one with a natural-sounding transition.

See `docs/specs/2026-05-13-autodj-design.md` for the design and `docs/plans/2026-05-13-autodj-implementation.md` for the build plan.

## Pre-built binaries (recommended)

Download from the **Releases** page of this repo:
- `AutoDJ.exe` — Windows 10/11
- `AutoDJ-macos.zip` — macOS 11+ (unzip → drag `AutoDJ.app` to Applications)

Both require `ffmpeg` on your PATH:
- Windows: `winget install ffmpeg`
- macOS: `brew install ffmpeg`

Launching the binary starts the backend on `localhost:8000` and opens your browser automatically. On macOS, the first launch will be blocked by Gatekeeper — right-click the `.app` and choose Open to allow it.

## Run from source

Windows:
```powershell
.\scripts\setup.ps1
.\scripts\run.ps1
```

macOS / Linux:
```bash
./scripts/setup.sh
./scripts/run.sh
```

Then open <http://localhost:5173>.

## Build the binary yourself

Windows:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install pyinstaller
cd ..\frontend; npm run build
cd ..\backend; pyinstaller AutoDJ.spec --clean --noconfirm
```
Produces `backend\dist\AutoDJ.exe`.

macOS / Linux:
```bash
./scripts/build_app.sh
```
Produces `backend/dist/AutoDJ.app` (macOS) or `backend/dist/AutoDJ` (Linux).

## Continuous integration

A GitHub Actions workflow (`.github/workflows/build.yml`) builds both Windows and macOS binaries on every push to `main`/`master` and on every tag push. To get fresh binaries:

1. Push the repo to GitHub.
2. The workflow runs automatically. Find the binaries in the **Actions** tab → click the latest run → scroll to **Artifacts**.
3. To cut a release: `git tag v1.0.0 && git push --tags`. The workflow creates a GitHub Release with both binaries attached.
