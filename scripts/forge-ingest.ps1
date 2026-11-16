# Windows preparation only. Set INGEST_PYTHON to select Python 3.11+.
param([string]$Source, [string]$Topic)
$ErrorActionPreference = 'Stop'
$runtime = $env:INGEST_PYTHON
if (-not $runtime) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $bundledPython) { $runtime = $bundledPython }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $runtime = 'python' }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $runtime = 'python3' }
    else { throw 'Python not found. Set INGEST_PYTHON to a Python 3.11+ executable.' }
}
$prepareArgs = @((Join-Path $PSScriptRoot 'ingest_prepare.py'))
if ($Source) { $prepareArgs += $Source }
if ($Topic) { $prepareArgs += @('--topic', $Topic) }
& $runtime @prepareArgs
exit $LASTEXITCODE
