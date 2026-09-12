$ErrorActionPreference = "Stop"
$manifest = Join-Path $PSScriptRoot "src-tauri\Cargo.toml"
$exe = Join-Path $PSScriptRoot "src-tauri\target\release\oss-update-watch-desktop.exe"
$sidecar = Join-Path $PSScriptRoot "src-tauri\target\release\fossight-backend.exe"

if (-not (Test-Path $exe) -or -not (Test-Path $sidecar)) {
    & (Join-Path $PSScriptRoot "desktop-build.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Start-Process -FilePath $exe -WorkingDirectory $PSScriptRoot
