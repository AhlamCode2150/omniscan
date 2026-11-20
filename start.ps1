# Starts API (:8000) and web UI (:3000). Run from the repo root.
$root = $PSScriptRoot
Start-Process "$root\.venv\Scripts\python.exe" -ArgumentList '-m','uvicorn','app.main:app','--port','8000','--host','127.0.0.1' -WorkingDirectory "$root\backend"
Push-Location "$root\frontend"; if (-not (Test-Path .next\BUILD_ID)) { npm run build }; Start-Process npm -ArgumentList 'run','start'; Pop-Location
Write-Host "OMNISCAN: http://localhost:3000"
