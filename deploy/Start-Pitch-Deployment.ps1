param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$PrivateDir = Join-Path $PSScriptRoot 'private'
$AccessConfig = Join-Path $PrivateDir 'cloudflare.json'
$TokenFile = Join-Path $PrivateDir 'tunnel-token.txt'
$CloudflareBinary = Join-Path $env:USERPROFILE '.cache\astory-deployment\cloudflared.exe'
$BundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
foreach ($RequiredFile in @($AccessConfig, $TokenFile, $CloudflareBinary, $BundledPython)) {
    if (-not (Test-Path -LiteralPath $RequiredFile -PathType Leaf)) { throw "Deployment file is missing: $RequiredFile" }
}
$Config = Get-Content -LiteralPath $AccessConfig -Raw | ConvertFrom-Json
if ($Config.hostname -ne 'pitch.gbaonvo.com' -or $Config.team_domain -ne 'astoryapp.cloudflareaccess.com' -or $Config.email -ne 'gbao.n.vo@gmail.com' -or $Config.audience -notmatch '^[a-fA-F0-9]{64}$') {
    throw 'Deployment must use the reviewed hostname, team, owner email and exact Access audience.'
}
if ($CheckOnly) { Write-Output 'Deployment files and owner-only configuration are ready.'; exit 0 }
$DeploymentMutex = New-Object System.Threading.Mutex($false, 'Local\AStoryPitchDeployment')
if (-not $DeploymentMutex.WaitOne(0)) { exit 0 }
try {
    $Processes = @(Get-CimInstance Win32_Process)
    $OriginProcesses = @($Processes | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($AccessConfig) -and $_.CommandLine.Contains('founder_os serve') })
    if ($OriginProcesses.Count -eq 0) {
        $PortOwner = Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue
        if ($PortOwner) { throw 'Port 8766 is occupied by a different process; refusing to alter it.' }
        Start-Process -FilePath $BundledPython -ArgumentList @('-m', 'founder_os', 'serve', '--port', '8766', '--cloudflare-config', ('"' + $AccessConfig + '"')) -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PrivateDir 'origin.stdout.log') -RedirectStandardError (Join-Path $PrivateDir 'origin.stderr.log') | Out-Null
    }
    $TunnelProcesses = @($Processes | Where-Object { $_.ExecutablePath -eq $CloudflareBinary -and $_.CommandLine -and $_.CommandLine.Contains($TokenFile) })
    if ($TunnelProcesses.Count -eq 0) {
        Start-Process -FilePath $CloudflareBinary -ArgumentList @('tunnel', '--loglevel', 'warn', '--log-directory', ('"' + $PrivateDir + '"'), 'run', '--token-file', ('"' + $TokenFile + '"')) -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PrivateDir 'tunnel.stdout.log') -RedirectStandardError (Join-Path $PrivateDir 'tunnel.stderr.log') | Out-Null
    }
    Write-Output 'Protected origin and tunnel restart checks completed.'
} finally {
    $DeploymentMutex.ReleaseMutex()
    $DeploymentMutex.Dispose()
}
