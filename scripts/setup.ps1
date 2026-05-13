#requires -version 5.1
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot\..

Write-Host "Checking ffmpeg..."
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host "ffmpeg not found. Install with: winget install ffmpeg" -ForegroundColor Yellow
    exit 1
}

Write-Host "Setting up backend venv..."
Push-Location backend
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]" --quiet
Pop-Location

Write-Host "Installing frontend deps..."
Push-Location frontend
npm install --silent
Pop-Location

Pop-Location
Write-Host "Done. Run scripts\run.ps1 to start both servers." -ForegroundColor Green
