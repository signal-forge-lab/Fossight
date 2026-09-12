$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$builtExe = Join-Path $root "src-tauri\target\release\oss-update-watch-desktop.exe"
$builtSidecar = Join-Path $root "src-tauri\target\release\fossight-backend.exe"
if (-not (Test-Path $builtExe)) { throw "Release desktop executable not found: $builtExe" }
if (-not (Test-Path $builtSidecar)) { throw "Release sidecar not found: $builtSidecar" }

# Run from a directory that contains no source tree. This catches accidental
# CARGO_MANIFEST_DIR/source-checkout dependencies in the release launcher.
$appDir = Join-Path $root "build\release-smoke-app"
if (Test-Path $appDir) { Remove-Item -Recurse -Force $appDir }
New-Item -ItemType Directory -Force -Path $appDir | Out-Null
$exe = Join-Path $appDir "Fossight.exe"
$sidecar = Join-Path $appDir "fossight-backend.exe"
Copy-Item -Force $builtExe $exe
Copy-Item -Force $builtSidecar $sidecar

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()

$dataDir = Join-Path $root "build\release-smoke-data"
if (Test-Path $dataDir) { Remove-Item -Recurse -Force $dataDir }
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $exe
$startInfo.UseShellExecute = $false
$startInfo.Environment['FOSSIGHT_DATA_DIR'] = $dataDir
$startInfo.Environment['OSS_UPDATE_WATCH_DESKTOP_PORT'] = "$port"
# Deliberately exclude Python, Node, Rust/Cargo and Git from PATH. A release
# build must still launch its packaged backend. Git absence should be reported
# in-app as a prerequisite state rather than preventing startup.
$startInfo.Environment['PATH'] = "$env:SystemRoot\System32;$env:SystemRoot"

$process = $null
try {
    $process = [System.Diagnostics.Process]::Start($startInfo)
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($process.HasExited) { throw "Release desktop exited before becoming ready (exit $($process.ExitCode))." }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/" -TimeoutSec 2
            if ($response.StatusCode -eq 200 -and $response.Content -match '<title>Fossight</title>') {
                $ready = $true
                break
            }
        } catch { }
        Start-Sleep -Milliseconds 150
    }
    if (-not $ready) { throw "Release desktop backend did not become ready within 30 seconds." }

    $prereqs = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/prerequisites" -TimeoutSec 5
    if ($prereqs.git.available) {
        throw "Minimal PATH unexpectedly exposed Git; test cannot prove prerequisite handling."
    }
    if ($prereqs.remediation -notmatch 'Install Git for Windows') {
        throw "Missing-Git remediation was not returned."
    }
    Write-Host "PASS release desktop launches outside source tree with packaged sidecar and Python/Node/Rust/Git absent from PATH"
} finally {
    if ($process -and -not $process.HasExited) {
        & taskkill.exe /PID $process.Id /T /F 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
