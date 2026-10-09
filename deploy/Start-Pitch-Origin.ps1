param([string]$Config = (Join-Path $PSScriptRoot 'private\cloudflare.json'))
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$PythonCommand = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $PythonCommand)) { $PythonCommand = 'python' }
if (-not (Test-Path -LiteralPath $Config)) { throw 'Access configuration is missing. Copy cloudflare.example.json to deploy/private/cloudflare.json and set the exact app audience.' }
Push-Location $ProjectRoot
try { & $PythonCommand -m founder_os serve --port 8766 --cloudflare-config $Config; exit $LASTEXITCODE }
finally { Pop-Location }
