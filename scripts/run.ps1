#!/usr/bin/env pwsh
Write-Host "Starting Flask app..."
. .\.venv\Scripts\Activate.ps1
$env:FLASK_APP = 'app.py'
$env:FLASK_ENV = 'development'
python -m flask run
