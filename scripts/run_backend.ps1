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
$env:CORS_ORIGINS = 'http://localhost:5174,http://127.0.0.1:5174'
$env:JWT_SECRET_KEY = [guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()

& $python (Join-Path $repoRoot 'backend\seed_test_db.py')
if ($LASTEXITCODE -ne 0) { throw 'SQLite test database seeding failed.' }

Set-Location (Join-Path $repoRoot 'backend')
& $python app.py
exit $LASTEXITCODE
