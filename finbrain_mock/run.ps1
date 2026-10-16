param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)
$ErrorActionPreference = 'Stop'
$runtimePath = $null
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand -and $pythonCommand.Source -notlike '*WindowsApps*') {
    $runtimePath = $pythonCommand.Source
}
if (-not $runtimePath) {
    $bundledPath = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPath) { $runtimePath = $bundledPath }
}
if (-not $runtimePath) { throw 'Python 3.10+ is required. Install Python or run the .py files using an existing Python interpreter.' }
if (-not $CommandArgs -or $CommandArgs.Count -eq 0) {
    $CommandArgs = @('demo.py', 'compare')
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & $runtimePath @CommandArgs
    if ($LASTEXITCODE -ne 0) { throw "Python exited with code $LASTEXITCODE" }
} finally {
    Pop-Location
}
