param([ValidateSet('gbao.n.vo@gmail.com','bao@astoryapp.com')][string]$Account)
$ErrorActionPreference = 'Stop'
$InboxPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $InboxPython)) { $InboxPython = (Get-Command python -ErrorAction Stop).Source }
if (-not $Account) {
  Write-Host '1) gbao.n.vo@gmail.com   2) bao@astoryapp.com'
  $Choice = Read-Host 'Which inbox'
  $Account = @{ '1' = 'gbao.n.vo@gmail.com'; '2' = 'bao@astoryapp.com' }[$Choice]
  if (-not $Account) { throw 'Choose 1 or 2.' }
}
Write-Host "Connecting $Account for the read-only inbox tracker."
Write-Host 'Founder OS only reads application emails here. It never sends, deletes, moves or marks mail as read.'
Write-Host 'Create a Google app password at https://myaccount.google.com/apppasswords while signed in as this account (needs 2-Step Verification).'
Write-Host 'Never enter your normal Google password.'
$InboxSecure = Read-Host 'Google app password' -AsSecureString
$InboxPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($InboxSecure)
try {
  $InboxPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($InboxPointer)
  $InboxStart = New-Object System.Diagnostics.ProcessStartInfo
  $InboxStart.FileName = $InboxPython
  $InboxStart.Arguments = '"' + (Join-Path $PSScriptRoot 'tools\connect_inbox_mail.py') + '" ' + $Account
  $InboxStart.UseShellExecute = $false
  $InboxStart.RedirectStandardInput = $true
  $InboxProcess = [System.Diagnostics.Process]::Start($InboxStart)
  $InboxProcess.StandardInput.Write($InboxPlain)
  $InboxProcess.StandardInput.Close()
  $InboxProcess.WaitForExit()
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($InboxPointer)
  $InboxPlain = $null
}
Read-Host 'Press Enter to close'
