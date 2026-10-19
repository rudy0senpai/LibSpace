$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

$python = Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    py -3 -m venv (Join-Path $repoRoot 'backend\.venv')
}
& $python -m pip install -r (Join-Path $repoRoot 'backend\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
# This launcher is for local SQLite testing only. These explicit settings
# prevent a repository .env PostgreSQL URL from being used by accident.
$env:APP_ENV = 'testing'
$env:DATABASE_URL = 'sqlite:///libsphere_test.db'
$env:CORS_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173'
$env:JWT_SECRET_KEY = [guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()

# File-backed seeding is gated because the legacy test catalog has no ISBNs.
# Require an already initialized test DB and never run a seeder during startup.
$testDatabase = Join-Path $repoRoot 'backend\instance\libsphere_test.db'
if (-not (Test-Path $testDatabase)) {
    throw 'No existing testing DB found. Fresh file-backed seeding is disabled until an ISBN-backed test seed source is reviewed.'
}

Set-Location (Join-Path $repoRoot 'backend')
& $python app.py
exit $LASTEXITCODE
