$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$sep = [char]0x1f
$env:CARGO_ENCODED_RUSTFLAGS = (@(
    "--remap-path-prefix=$([Environment]::GetFolderPath('UserProfile'))=<USER_HOME>",
    "--remap-path-prefix=$root=<SOURCE_ROOT>"
) -join $sep)
& (Join-Path $PSScriptRoot "build-sidecar.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
cargo build --release --manifest-path (Join-Path $PSScriptRoot "src-tauri\Cargo.toml")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$hostLine = (& rustc -vV | Select-String '^host:').Line
$target = ($hostLine -replace '^host:\s*', '').Trim()
$sidecar = Join-Path $PSScriptRoot "src-tauri\binaries\fossight-backend-$target.exe"
$releaseDir = Join-Path $PSScriptRoot "src-tauri\target\release"
Copy-Item -Force $sidecar (Join-Path $releaseDir "fossight-backend.exe")
exit $LASTEXITCODE
