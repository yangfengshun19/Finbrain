param([switch]$Test)
$ErrorActionPreference = 'Stop'
$pythonPath = $null
$installed = Get-Command python -ErrorAction SilentlyContinue
if ($installed -and $installed.Source -notlike '*WindowsApps*') { $pythonPath = $installed.Source }
if (-not $pythonPath) {
    $bundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundled) { $pythonPath = $bundled }
}
if (-not $pythonPath) { throw 'Python 3.11+ is required.' }
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($Test) { & $pythonPath test.py } else { & $pythonPath run.py }
    if ($LASTEXITCODE -ne 0) { throw "FinBrain exited with code $LASTEXITCODE" }
} finally { Pop-Location }
