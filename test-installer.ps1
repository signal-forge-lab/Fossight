$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$installer = Get-ChildItem (Join-Path $root "dist") -Filter "Fossight_*_x64-setup.exe" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $installer) { throw "Fossight NSIS installer not found." }

$sandbox = Join-Path $root "build\installer-e2e"
$installDir = Join-Path $env:LOCALAPPDATA "Fossight"
$dataDir = Join-Path $sandbox "User Data"
if (Test-Path $sandbox) { Remove-Item -Recurse -Force $sandbox }
$mediaDir = Join-Path $sandbox "Clean Media"
New-Item -ItemType Directory -Force -Path $dataDir,$mediaDir | Out-Null
$mediaInstaller = Join-Path $mediaDir $installer.Name
Copy-Item -Force $installer.FullName $mediaInstaller
if (Test-Path (Join-Path $installDir "oss-update-watch-desktop.exe")) {
    throw "A Fossight current-user installation already exists at $installDir; refusing to overwrite it during E2E."
}

function Start-CleanFossight([string]$exe, [int]$port) {
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $exe
    $psi.UseShellExecute = $false
    $psi.Environment['FOSSIGHT_DATA_DIR'] = $dataDir
    $psi.Environment['OSS_UPDATE_WATCH_DESKTOP_PORT'] = "$port"
    $psi.Environment['PATH'] = "$env:SystemRoot\System32;$env:SystemRoot"
    return [System.Diagnostics.Process]::Start($psi)
}

function New-FreePort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    $listener.Stop()
    return $port
}

function Wait-Fossight([System.Diagnostics.Process]$process, [int]$port) {
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($process.HasExited) { throw "Installed Fossight exited before ready (exit $($process.ExitCode))." }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/" -TimeoutSec 2
            if ($response.StatusCode -eq 200 -and $response.Content -match '<title>Fossight</title>') { return }
        } catch { }
        Start-Sleep -Milliseconds 150
    }
    throw "Installed Fossight did not become ready within 30 seconds."
}

function Stop-Tree([System.Diagnostics.Process]$process) {
    if ($process -and -not $process.HasExited) {
        & taskkill.exe /PID $process.Id /T /F 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
    }
}

# Tauri currentUser NSIS installs under %LOCALAPPDATA%\Fossight. User data is
# intentionally separate (%LOCALAPPDATA%\FossightData), so install/uninstall
# cannot erase the user's registry/config/state.
$installPsi = [System.Diagnostics.ProcessStartInfo]::new()
$installPsi.FileName = $mediaInstaller
$installPsi.UseShellExecute = $false
$installPsi.Environment['PATH'] = "$env:SystemRoot\System32;$env:SystemRoot"
[void]$installPsi.ArgumentList.Add('/S')
$install = [System.Diagnostics.Process]::Start($installPsi)
$install.WaitForExit()
if ($install.ExitCode -ne 0) { throw "Installer failed with exit code $($install.ExitCode)." }

$appExe = Get-ChildItem $installDir -Filter "*.exe" -File |
    Where-Object { $_.Name -notmatch 'uninstall|unins|fossight-backend' } |
    Select-Object -First 1
$sidecar = Get-ChildItem $installDir -Filter "fossight-backend*.exe" -File | Select-Object -First 1
if (-not $appExe) { throw "Installed desktop executable not found in $installDir" }
if (-not $sidecar) { throw "Installed sidecar executable not found in $installDir" }

$port = New-FreePort
$process = $null
try {
    $process = Start-CleanFossight $appExe.FullName $port
    Wait-Fossight $process $port
    $prereqs = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/prerequisites" -TimeoutSec 5
    if ($prereqs.git.available) { throw "Minimal PATH unexpectedly exposed Git." }
    if ($prereqs.remediation -notmatch 'Install Git for Windows') { throw "Missing-Git remediation absent." }

    $config = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/settings" -TimeoutSec 5
    $config.config.onboarding_complete = $true
    $body = @{ config = $config.config } | ConvertTo-Json -Depth 20
    Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$port/api/settings" -ContentType 'application/json' -Body $body -TimeoutSec 5 | Out-Null
} finally {
    Stop-Tree $process
}

# Relaunch with the same isolated user-data directory to prove persistence.
$port2 = New-FreePort
$process2 = $null
try {
    $process2 = Start-CleanFossight $appExe.FullName $port2
    Wait-Fossight $process2 $port2
    $config2 = Invoke-RestMethod -Uri "http://127.0.0.1:$port2/api/settings" -TimeoutSec 5
    if (-not $config2.config.onboarding_complete) { throw "Settings did not persist across restart." }
} finally {
    Stop-Tree $process2
}

$marker = Join-Path $dataDir "preserve-after-uninstall.txt"
Set-Content -Encoding utf8 $marker "user data must survive uninstall"
$uninstaller = Get-ChildItem $installDir -Filter "*.exe" -File |
    Where-Object { $_.Name -match 'uninstall|unins' } |
    Select-Object -First 1
if (-not $uninstaller) { throw "NSIS uninstaller not found in $installDir" }

$uninstallPsi = [System.Diagnostics.ProcessStartInfo]::new()
$uninstallPsi.FileName = $uninstaller.FullName
$uninstallPsi.UseShellExecute = $false
[void]$uninstallPsi.ArgumentList.Add('/S')
$uninstall = [System.Diagnostics.Process]::Start($uninstallPsi)
$uninstall.WaitForExit()
if ($uninstall.ExitCode -ne 0) { throw "Uninstaller failed with exit code $($uninstall.ExitCode)." }
Start-Sleep -Milliseconds 500

if (-not (Test-Path $marker)) { throw "User data was removed by uninstall." }
if (Test-Path $appExe.FullName) { throw "Installed desktop executable still exists after uninstall." }

Write-Host "PASS NSIS install -> launch -> persistence -> uninstall; isolated user data preserved"
