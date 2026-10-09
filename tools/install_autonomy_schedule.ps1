$ErrorActionPreference = 'Stop'
$AutonomyRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$AutonomyPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe'
if (-not (Test-Path -LiteralPath $AutonomyPython)) { $AutonomyPython = (Get-Command pythonw -ErrorAction Stop).Source }
$AutonomyWorker = Join-Path $AutonomyRoot 'tools\autonomy_worker.py'
$AutonomyTaskName = 'AStory-FounderOS-ApplicationPilot-DailyReport-01a107b5'
$AutonomyExisting = Get-ScheduledTask -TaskName $AutonomyTaskName -ErrorAction SilentlyContinue
if ($AutonomyExisting -and $AutonomyExisting.Actions.Arguments -notlike "*$AutonomyWorker*") { throw 'An unrelated task already uses this name; nothing overwritten.' }
$AutonomyAction = New-ScheduledTaskAction -Execute $AutonomyPython -Argument ('"' + $AutonomyWorker + '" --poll') -WorkingDirectory $AutonomyRoot
$AutonomyTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 5)
$AutonomyLogon = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$AutonomyPrincipal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$AutonomySettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $AutonomyTaskName -Action $AutonomyAction -Trigger @($AutonomyTrigger,$AutonomyLogon) -Principal $AutonomyPrincipal -Settings $AutonomySettings -Description 'A Story authorized free-application pilot, daily credits discovery 07:30 Eastern, daily owner email 09:00 Eastern. No paid applications, legal acceptance, confidential uploads or guessed facts.' -Force | Out-Null
[pscustomobject]@{TaskName=$AutonomyTaskName;State=(Get-ScheduledTask -TaskName $AutonomyTaskName).State.ToString();Reports='Daily 09:00 America/New_York';CreditDiscovery='Daily 07:30 America/New_York';Email='Requires local Gmail connection';RunsWhen='PC awake, online and Windows owner signed in'} | ConvertTo-Json
