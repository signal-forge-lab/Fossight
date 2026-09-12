$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "run.ps1") @args check
$code = $LASTEXITCODE

# Local updates, upstream changes, or local attention are normal scheduler outcomes, not task failures.
if ($code -eq 0 -or $code -eq 1) {
    exit 0
}
exit $code
