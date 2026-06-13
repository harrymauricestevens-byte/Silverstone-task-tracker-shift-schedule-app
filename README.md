# Shift Task App

Simple Flask app to assign tasks and shifts to engineers.

Quick start (Windows PowerShell)

1. Create virtualenv and install dependencies:

```powershell
.\scripts\setup.ps1
```

2. Run the app:

```powershell
.\scripts\run.ps1
```

3. Open in browser: http://127.0.0.1:5000

Notes
- Sign in using a username and choose role `manager` or `engineer` (no passwords).
- Database file: `instance/app.db` (delete to reset data).
- CSV export available from the dashboard.

Files added
- `app.py` — main Flask app
- `templates/` — HTML templates
- `requirements.txt` — Python dependencies
- `scripts/setup.ps1`, `scripts/run.ps1` — helper scripts
# Silverstone-task-tracker-shift-schedule-app
making shit, who knows
