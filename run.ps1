$ErrorActionPreference = "Stop"
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
& python -m oss_update_watch @args
exit $LASTEXITCODE
