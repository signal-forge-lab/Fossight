$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$installer = Get-ChildItem (Join-Path $root "dist") -Filter "Fossight_*_x64-setup.exe" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $installer) { throw "Distribution installer not found." }
$checksumPath = "$($installer.FullName).sha256"
if (-not (Test-Path $checksumPath)) { throw "Checksum file missing: $checksumPath" }

$actualHash = (Get-FileHash -Algorithm SHA256 $installer.FullName).Hash.ToLowerInvariant()
$expectedHash = ((Get-Content $checksumPath -Raw).Trim() -split '\s+')[0].ToLowerInvariant()
if ($actualHash -ne $expectedHash) { throw "Installer SHA-256 mismatch." }

$pyproject = Get-Content (Join-Path $root "pyproject.toml") -Raw
$cargo = Get-Content (Join-Path $root "src-tauri\Cargo.toml") -Raw
$tauri = Get-Content (Join-Path $root "src-tauri\tauri.conf.json") -Raw | ConvertFrom-Json
$init = Get-Content (Join-Path $root "src\oss_update_watch\__init__.py") -Raw

$versions = @(
    ([regex]::Match($pyproject, '(?m)^version\s*=\s*"([^"]+)"')).Groups[1].Value,
    ([regex]::Match($cargo, '(?m)^version\s*=\s*"([^"]+)"')).Groups[1].Value,
    [string]$tauri.version,
    ([regex]::Match($init, '__version__\s*=\s*"([^"]+)"')).Groups[1].Value
)
if (($versions | Sort-Object -Unique).Count -ne 1) {
    throw "Version mismatch: $($versions -join ', ')"
}
if ($installer.Name -notmatch [regex]::Escape($versions[0])) {
    throw "Installer filename does not contain version $($versions[0])."
}

$artifacts = @(
    $installer.FullName,
    (Join-Path $root "src-tauri\target\release\oss-update-watch-desktop.exe"),
    (Join-Path $root "src-tauri\binaries\fossight-backend-x86_64-pc-windows-msvc.exe")
)
foreach ($artifact in $artifacts) {
    if (-not (Test-Path $artifact)) { throw "Artifact missing: $artifact" }
}

python (Join-Path $root "scripts\scan_release_artifacts.py") @artifacts
if ($LASTEXITCODE -ne 0) { throw "Release artifact forbidden-marker scan failed." }

$signature = Get-AuthenticodeSignature $installer.FullName
if ($signature.Status -notin @('Valid', 'NotSigned')) {
    throw "Unexpected installer signature state: $($signature.Status)"
}

Write-Host "PASS distribution artifacts: checksum, version consistency, forbidden-marker scan"
Write-Host "Installer signature status: $($signature.Status)"
