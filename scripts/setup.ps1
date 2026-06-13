#!/usr/bin/env pwsh
Write-Host "Creating virtual environment and installing requirements..."
if (-not (Test-Path -Path .venv)) {
    python -m venv .venv
}
Write-Host "Activating virtual environment and installing packages..."
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Write-Host "Setup complete. Run '.\scripts\run.ps1' to start the app."
