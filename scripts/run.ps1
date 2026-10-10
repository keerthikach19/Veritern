param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv-local\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Install dependencies with uv sync --locked first.'
}
if ($Demo) { $env:APP_MODE = 'demo' }
& $pythonPath -m streamlit run app.py --server.address 127.0.0.1
