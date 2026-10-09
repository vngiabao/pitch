$ErrorActionPreference = 'Stop'
$ReportPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $ReportPython)) { $ReportPython = (Get-Command python -ErrorAction Stop).Source }
Write-Host 'Daily reports go only to gbao.n.vo@gmail.com.'
Write-Host 'Create a Google app password at https://myaccount.google.com/apppasswords (requires Google 2-Step Verification).'
Write-Host 'This is an email connection, not an OpenAI API key. Never enter your normal Google password.'
$ReportSecure = Read-Host 'Google app password' -AsSecureString
$ReportPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($ReportSecure)
try {
  $ReportPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ReportPointer)
  $ReportStart = New-Object System.Diagnostics.ProcessStartInfo
  $ReportStart.FileName = $ReportPython
  $ReportStart.Arguments = '"' + (Join-Path $PSScriptRoot 'tools\connect_report_mail.py') + '"'
  $ReportStart.UseShellExecute = $false
  $ReportStart.CreateNoWindow = $true
  $ReportStart.RedirectStandardInput = $true
  $ReportProcess = [System.Diagnostics.Process]::Start($ReportStart)
  $ReportProcess.StandardInput.Write($ReportPlain)
  $ReportProcess.StandardInput.Close()
  $ReportProcess.WaitForExit()
  if ($ReportProcess.ExitCode -ne 0) { throw 'Could not save the Gmail connection.' }
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ReportPointer)
  $ReportPlain = $null
}
