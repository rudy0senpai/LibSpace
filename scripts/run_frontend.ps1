$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$frontend = Join-Path $repoRoot 'frontend'
Set-Location $frontend

# Expose the local name, ID, role, and password form only in the testing UI.
$env:VITE_API_URL = 'http://localhost:5001'
$env:VITE_AUTH_MODE = 'testing'

if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    npm.cmd install
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
}
npm.cmd run dev -- --port 5173
exit $LASTEXITCODE
