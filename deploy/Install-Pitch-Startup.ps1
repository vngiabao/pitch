$ErrorActionPreference = 'Stop'
$Starter = Join-Path $PSScriptRoot 'Start-Pitch-Deployment.ps1'
& $Starter -CheckOnly
if ($LASTEXITCODE -ne 0) { throw 'Deployment readiness check failed.' }
$TaskName = 'A Story - Protected Pitch Website'
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) { throw 'Startup task already exists; inspect it before changing it.' }
$Owner = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $Starter + '"')
$Logon = New-ScheduledTaskTrigger -AtLogOn -User $Owner
$Retry = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$Principal = New-ScheduledTaskPrincipal -UserId $Owner -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger @($Logon, $Retry) -Principal $Principal -Settings $Settings -Description 'Restart the owner-only pitch.gbaonvo.com origin and Cloudflare Tunnel at sign-in and after failures.' | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Output 'Owner-level startup and five-minute restart checks installed.'
