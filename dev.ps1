param(
    [switch]$ApiOnly,
    [switch]$WorkerOnly,
    [switch]$WebOnly
)

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = Join-Path $PSScriptRoot "backend"

if (-not $WorkerOnly -and -not $WebOnly) {
    $env:CREDIT_REVIEW_DEMO_MODE = "true"
    Start-Process -WindowStyle Hidden -FilePath "uv" -ArgumentList "run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000" -WorkingDirectory $PSScriptRoot
}

if (-not $ApiOnly -and -not $WebOnly) {
    Start-Process -WindowStyle Hidden -FilePath "uv" -ArgumentList "run python -m app.worker" -WorkingDirectory $PSScriptRoot
}

if (-not $ApiOnly -and -not $WorkerOnly) {
    Start-Process -WindowStyle Hidden -FilePath "npm.cmd" -ArgumentList "--prefix web run dev" -WorkingDirectory $PSScriptRoot
}

Write-Host "CreditGuard AI services started. API: http://127.0.0.1:8000/docs"
