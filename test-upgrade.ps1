$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$oldInstaller = Join-Path $root "dist\Fossight_0.9.1_x64-setup.exe"
$newInstaller = Join-Path $root "dist\Fossight_1.0.0_x64-setup.exe"
if (-not (Test-Path $oldInstaller)) { throw "0.9.1 installer not found: $oldInstaller" }
if (-not (Test-Path $newInstaller)) { throw "1.0.0 installer not found: $newInstaller" }

$installDir = Join-Path $env:LOCALAPPDATA "Fossight"
if (Test-Path (Join-Path $installDir "oss-update-watch-desktop.exe")) {
    throw "A Fossight current-user installation already exists at $installDir; refusing to overwrite it during upgrade E2E."
}

$sandbox = Join-Path $root "build\upgrade-e2e"
if (Test-Path $sandbox) { Remove-Item -Recurse -Force $sandbox }
$dataDir = Join-Path $sandbox "User Data"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

$registry = @{
    schema_version = 1
    items = @(
        @{
            repo = "example/upgrade-e2e"
            tracking = @{ mode = "auto" }
            priority = "normal"
            usages = @(@{ project = "upgrade-e2e"; relation = "direct"; local_path = "C:\\Example Repo" })
            enabled = $false
        }
    )
} | ConvertTo-Json -Depth 20
Set-Content -Encoding utf8 (Join-Path $dataDir "registry.json") $registry

$state = @{
    schema_version = 1
    items = @{
        "example/upgrade-e2e" = @{
            observed = @{ mode = "release"; value = "v0.9.1-marker" }
            acknowledged = @{ mode = "release"; value = "v0.9.1-marker" }
        }
    }
} | ConvertTo-Json -Depth 20
$statePath = Join-Path $dataDir "state.json"
Set-Content -Encoding utf8 $statePath $state

function Install-Silent([string]$installer) {
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $installer
    $psi.UseShellExecute = $false
    [void]$psi.ArgumentList.Add('/S')
    $process = [System.Diagnostics.Process]::Start($psi)
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "Installer failed: $installer (exit $($process.ExitCode))" }
}

function New-FreePort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    $listener.Stop()
    return $port
}

function Start-Fossight([string]$exe, [int]$port) {
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $exe
    $psi.UseShellExecute = $false
    $psi.Environment['FOSSIGHT_DATA_DIR'] = $dataDir
    $psi.Environment['OSS_UPDATE_WATCH_DESKTOP_PORT'] = "$port"
    $psi.Environment['PATH'] = "$env:SystemRoot\System32;$env:SystemRoot"
    return [System.Diagnostics.Process]::Start($psi)
}

function Wait-Fossight([System.Diagnostics.Process]$process, [int]$port) {
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($process.HasExited) { throw "Fossight exited before ready (exit $($process.ExitCode))." }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/" -TimeoutSec 2
            if ($response.StatusCode -eq 200 -and $response.Content -match '<title>Fossight</title>') { return }
        } catch { }
        Start-Sleep -Milliseconds 150
    }
    throw "Fossight did not become ready within 30 seconds."
}

function Stop-Tree([System.Diagnostics.Process]$process) {
    if ($process -and -not $process.HasExited) {
        & taskkill.exe /PID $process.Id /T /F 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
    }
}

function Installed-App {
    $app = Get-ChildItem $installDir -Filter "*.exe" -File |
        Where-Object { $_.Name -notmatch 'uninstall|unins|fossight-backend' } |
        Select-Object -First 1
    if (-not $app) { throw "Installed Fossight desktop executable not found in $installDir" }
    return $app.FullName
}

function Verify-UserState([string]$appExe, [string]$stage) {
    $port = New-FreePort
    $process = $null
    try {
        $process = Start-Fossight $appExe $port
        Wait-Fossight $process $port
        $registryPayload = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/registry" -TimeoutSec 5
        if ($registryPayload.summary.registered -ne 1) { throw "${stage}: registry count changed" }
        if ($registryPayload.summary.disabled -ne 1) { throw "${stage}: enabled/disabled state changed" }
        if ($registryPayload.items[0].repo -ne 'example/upgrade-e2e') { throw "${stage}: registry repo changed" }

        $settings = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/settings" -TimeoutSec 5
        if ($stage -eq '0.9.1') {
            $settings.config.onboarding_complete = $true
            $settings.config.scan_roots = @(@{ path = 'C:\\Example Root'; mode = 'quick'; enabled = $true })
            $body = @{ config = $settings.config } | ConvertTo-Json -Depth 20
            Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$port/api/settings" -ContentType 'application/json' -Body $body -TimeoutSec 5 | Out-Null
        } else {
            if (-not $settings.config.onboarding_complete) { throw "${stage}: onboarding setting was lost" }
            if ($settings.config.scan_roots.Count -ne 1) { throw "${stage}: scan roots were lost" }
        }
    } finally {
        Stop-Tree $process
    }
}

Install-Silent $oldInstaller
Verify-UserState (Installed-App) '0.9.1'
$stateBefore = (Get-FileHash -Algorithm SHA256 $statePath).Hash

# Install the 1.0.0 current-user NSIS package over the existing 0.9.1 install.
Install-Silent $newInstaller
Verify-UserState (Installed-App) '1.0.0'
$stateAfter = (Get-FileHash -Algorithm SHA256 $statePath).Hash
if ($stateBefore -ne $stateAfter) { throw "state.json changed during upgrade" }

$marker = Join-Path $dataDir "preserve-after-upgrade-uninstall.txt"
Set-Content -Encoding utf8 $marker "preserve"
$uninstaller = Get-ChildItem $installDir -Filter "*.exe" -File |
    Where-Object { $_.Name -match 'uninstall|unins' } |
    Select-Object -First 1
if (-not $uninstaller) { throw "NSIS uninstaller not found after upgrade" }
$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $uninstaller.FullName
$psi.UseShellExecute = $false
[void]$psi.ArgumentList.Add('/S')
$uninstall = [System.Diagnostics.Process]::Start($psi)
$uninstall.WaitForExit()
if ($uninstall.ExitCode -ne 0) { throw "Uninstall after upgrade failed (exit $($uninstall.ExitCode))" }
Start-Sleep -Milliseconds 500
if (-not (Test-Path $marker)) { throw "User data was removed after upgraded uninstall" }

Write-Host "PASS 0.9.1 -> 1.0.0 upgrade preserves registry, settings, state, and uninstall-retained user data"
