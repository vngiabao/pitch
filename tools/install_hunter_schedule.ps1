$ErrorActionPreference = 'Stop'
$FundingRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$FundingPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $FundingPython -PathType Leaf)) { $FundingPython = (Get-Command python -ErrorAction Stop).Source }
$FundingWorker = Join-Path $FundingRoot 'tools\research_worker.py'
if (Test-Path -LiteralPath ($FundingPython -replace 'python.exe$','pythonw.exe')) { $FundingPython = $FundingPython -replace 'python.exe$','pythonw.exe' }
if (-not (Test-Path -LiteralPath $FundingWorker -PathType Leaf)) { throw 'Funding Hunter worker is missing.' }
$FundingTaskName = 'AStory-FounderOS-FundingHunter-01a107b5'
$FundingExisting = Get-ScheduledTask -TaskName $FundingTaskName -ErrorAction SilentlyContinue
if ($FundingExisting -and $FundingExisting.Actions.Arguments -notlike "*$FundingWorker*") { throw 'A different task already uses the target name; nothing overwritten.' }
$FundingAction = New-ScheduledTaskAction -Execute $FundingPython -Argument ('"' + $FundingWorker + '" --poll') -WorkingDirectory $FundingRoot
$FundingTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 5)
$FundingLogon = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$FundingPrincipal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$FundingSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 22) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$FundingDescription = 'A Story Founder OS Funding Hunter. Polls durable requests without model calls when idle; broad research Monday/Thursday 08:00 America/New_York, plus due rechecks. Uses existing Codex ChatGPT sign-in. No external submissions or messages.'
Register-ScheduledTask -TaskName $FundingTaskName -Action $FundingAction -Trigger @($FundingTrigger,$FundingLogon) -Principal $FundingPrincipal -Settings $FundingSettings -Description $FundingDescription -Force | Out-Null
$FundingInfo = Get-ScheduledTaskInfo -TaskName $FundingTaskName
[pscustomobject]@{TaskName=$FundingTaskName;State=(Get-ScheduledTask -TaskName $FundingTaskName).State.ToString();NextPoll=$FundingInfo.NextRunTime.ToString('o');ResearchSchedule='Monday and Thursday 08:00 America/New_York';RunsWhen='This user is signed in and the PC is awake; Codex app and ChatGPT window can be closed'} | ConvertTo-Json
