$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$hostLine = (& rustc -vV | Select-String '^host:').Line
if (-not $hostLine) { throw "Unable to determine Rust host target." }
$target = ($hostLine -replace '^host:\s*', '').Trim()
$binary = Join-Path $root "src-tauri\binaries\fossight-backend-$target.exe"
if (-not (Test-Path $binary)) { throw "Sidecar not built: $binary" }

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()

$dataDir = Join-Path $root "build\sidecar-smoke-data"
if (Test-Path $dataDir) { Remove-Item -Recurse -Force $dataDir }
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

$process = $null
try {
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $binary
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    foreach ($argument in @('--data-dir', $dataDir, 'ui', '--no-open', '--port', "$port")) {
        [void]$startInfo.ArgumentList.Add($argument)
    }
    $process = [System.Diagnostics.Process]::Start($startInfo)

    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($process.HasExited) { throw "Sidecar exited before becoming ready (exit $($process.ExitCode))." }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/" -TimeoutSec 2
            if ($response.StatusCode -eq 200 -and $response.Content -match '<title>Fossight</title>') {
                $ready = $true
                break
            }
        } catch { }
        Start-Sleep -Milliseconds 150
    }
    if (-not $ready) { throw "Sidecar did not become ready within 30 seconds." }

    $prereqs = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/prerequisites" -TimeoutSec 5
    if ($null -eq $prereqs.git.available) { throw "Prerequisite API response is incomplete." }
    Write-Host "PASS sidecar standalone HTTP/UI smoke test on port $port"
} finally {
    if ($process -and -not $process.HasExited) {
        # PyInstaller one-file uses a bootloader parent/child pair. Kill the
        # whole tree so automated smoke runs do not leak the extracted child.
        & taskkill.exe /PID $process.Id /T /F 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
