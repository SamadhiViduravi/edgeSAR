$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install dependencies first; see README.md.' }
$backend = Start-Process -FilePath $pythonPath -ArgumentList '-m','uvicorn','apps.api.app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
try { npm run dev } finally { if (-not $backend.HasExited) { Stop-Process -Id $backend.Id } }
