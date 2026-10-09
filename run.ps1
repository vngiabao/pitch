param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
$ErrorActionPreference = 'Stop'
$BundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$PythonCommand = if (Test-Path -LiteralPath $BundledPython) { $BundledPython } else { 'python' }
Push-Location $PSScriptRoot
try {
    if ($Arguments.Count -gt 0 -and $Arguments[0] -eq 'test') {
        & $PythonCommand -m unittest discover -s tests -v
    } else {
        & $PythonCommand -m founder_os @Arguments
    }
    $RunExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $RunExitCode
