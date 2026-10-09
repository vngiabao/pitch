$ErrorActionPreference = 'Stop'
$FounderRoot = $PSScriptRoot
$FounderPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $FounderPython)) { $FounderPython = (Get-Command python -ErrorAction Stop).Source }
try { Invoke-WebRequest -Uri 'http://127.0.0.1:8765/' -UseBasicParsing -TimeoutSec 2 | Out-Null }
catch { Start-Process -FilePath $FounderPython -ArgumentList '-m founder_os serve --port 8765' -WorkingDirectory $FounderRoot -WindowStyle Hidden }
Write-Output 'A Story Founder OS: http://127.0.0.1:8765/'
