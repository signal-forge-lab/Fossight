$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$sidecarBuild = Join-Path $root "build-sidecar.ps1"
$bundleDir = Join-Path $root "src-tauri\target\release\bundle\nsis"
$artifactsDir = Join-Path $root "dist"
$sep = [char]0x1f
$env:CARGO_ENCODED_RUSTFLAGS = (@(
    "--remap-path-prefix=$([Environment]::GetFolderPath('UserProfile'))=<USER_HOME>",
    "--remap-path-prefix=$root=<SOURCE_ROOT>"
) -join $sep)

& $sidecarBuild
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location $root
try {
    cargo tauri build --bundles nsis
} finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$installer = Get-ChildItem -Path $bundleDir -Filter "*.exe" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $installer) { throw "NSIS installer was not produced in $bundleDir" }

New-Item -ItemType Directory -Force -Path $artifactsDir | Out-Null
$dest = Join-Path $artifactsDir $installer.Name
Copy-Item -Force $installer.FullName $dest
$hash = (Get-FileHash -Algorithm SHA256 $dest).Hash.ToLowerInvariant()
$checksum = "$hash *$($installer.Name)`n"
Set-Content -Encoding ascii -NoNewline -Path "$dest.sha256" -Value $checksum

Write-Host "Installer: $dest"
Write-Host "SHA256:    $hash"
