$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$python = if (Get-Command python.exe -ErrorAction SilentlyContinue) { "python.exe" } else { "python" }
$pyinstaller = & $python -m PyInstaller --version 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is required to build the Fossight backend sidecar. Install it on the build machine only."
}

$hostLine = (& rustc -vV | Select-String '^host:').Line
if (-not $hostLine) { throw "Unable to determine Rust host target." }
$target = ($hostLine -replace '^host:\s*', '').Trim()
if (-not $target.EndsWith('windows-msvc')) {
    throw "The current distribution plan supports Windows MSVC targets only (found $target)."
}

$buildRoot = Join-Path $root "build\sidecar"
$dist = Join-Path $buildRoot "dist"
$work = Join-Path $buildRoot "work"
$spec = Join-Path $buildRoot "spec"
$binaryDir = Join-Path $root "src-tauri\binaries"
New-Item -ItemType Directory -Force -Path $dist, $work, $spec, $binaryDir | Out-Null

$catalog = Join-Path $root "docs\oss-summary-catalog.md"
$uiDir = Join-Path $root "src\oss_update_watch\ui"
$entry = Join-Path $root "scripts\fossight_backend_entry.py"

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name fossight-backend `
    --paths (Join-Path $root "src") `
    --add-data "$uiDir;oss_update_watch/ui" `
    --add-data "$catalog;docs" `
    --distpath $dist `
    --workpath $work `
    --specpath $spec `
    $entry
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$built = Join-Path $dist "fossight-backend.exe"
if (-not (Test-Path $built)) { throw "PyInstaller did not produce $built" }
$targetBinary = Join-Path $binaryDir "fossight-backend-$target.exe"
Copy-Item -Force $built $targetBinary
Write-Host "Fossight sidecar: $targetBinary"
