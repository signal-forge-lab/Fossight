# Fossight Windows Packaging

## Runtime architecture

The Windows distribution uses two executables:

```text
Fossight desktop (Tauri/WebView2)
        |
        +-- fossight-backend.exe (PyInstaller one-file sidecar)
                |
                +-- Python stdlib HTTP backend
                +-- Fossight HTML/CSS/JS assets
                +-- curated OSS summary catalog
```

The sidecar is the selected P5 packaging approach because the existing backend
is stdlib-only Python and PyInstaller can make it self-contained without
changing the backend architecture. Python is a **build-time dependency only**.

Release builds do not search for or launch system Python. Debug builds retain
the source-tree/system-Python path for practical local development.

## Build prerequisites

Build machine only:

- Windows x64 with Rust/MSVC toolchain;
- Python 3.11+;
- PyInstaller 6.x;
- WebView2/Tauri build prerequisites;
- Git for source/build operations.

End users do not need Python, Rust/Cargo, Node.js, or the Fossight source tree.
Git remains a Fossight functional prerequisite for repository inspection and
is detected at runtime with an actionable in-app message when absent.

On Windows, Tauri's current-user NSIS installer places application binaries in
`%LOCALAPPDATA%\Fossight`. Mutable Fossight data therefore lives separately in
`%LOCALAPPDATA%\FossightData`. Fossight 0.9.1+ can copy known data files from
the earlier `%LOCALAPPDATA%\Fossight` data layout without copying installed
executables or uninstallers.

## Sidecar build

```powershell
./build-sidecar.ps1
./test-sidecar.ps1
```

`build-sidecar.ps1` creates a target-triple binary under
`src-tauri/binaries/` for the Tauri bundler. Generated executables are ignored
by Git.

## Developer release build

```powershell
./desktop-build.ps1
./test-release-desktop.ps1
```

`desktop-build.ps1` builds the sidecar, builds the optimized Tauri executable,
and places `fossight-backend.exe` beside the raw release executable.

`test-release-desktop.ps1` copies only those two executables to an isolated
directory and launches them with a minimal PATH that excludes Python, Node,
Rust/Cargo, and Git. It verifies that Fossight starts and that missing Git is
reported as a prerequisite rather than a startup failure.

## NSIS installer build

```powershell
./build-installer.ps1
./test-installer.ps1
```

`build-installer.ps1` builds the sidecar, invokes the Tauri NSIS bundler, copies
the installer to `dist/`, and writes a matching `.sha256` file.

Release Rust builds set `--remap-path-prefix` for the source checkout and build
user profile. This prevents Cargo dependency panic/source metadata from leaking
developer absolute paths into the desktop executable.

`test-installer.ps1` exercises the actual current-user installer end to end:

```text
silent install
-> launch with packaged sidecar
-> persist settings
-> close and relaunch
-> silent uninstall
-> verify user data survives
```

The test launches Fossight with a minimal PATH that excludes Python, Node,
Rust/Cargo, and Git. The install itself uses the normal Tauri current-user
location and the test data directory is isolated from the developer's profile.

Final artifact checks:

```powershell
./test-distribution-artifacts.ps1
```

This verifies checksum/version consistency and scans the installer, desktop
EXE, and sidecar for forbidden developer-path / credential markers. It also
reports Authenticode status; unsigned release candidates report `NotSigned`.

## Startup diagnostics

The release launcher reports a specific error when the packaged backend is
missing or cannot start. `FOSSIGHT_BACKEND_EXE` is available as an explicit
developer/test override. `FOSSIGHT_DATA_DIR` remains the supported user-data
location override.

## Security and privacy

- The sidecar binds the UI/API to `127.0.0.1` only.
- User registry/state/cache/report data are not bundled.
- GitHub token values are never written into package artifacts or status APIs.
- The curated catalog is read-only package data; arbitrary-repository metadata
  is cached under the user data directory.
- Mutable Windows data defaults to `%LOCALAPPDATA%\FossightData`; the installer
  directory `%LOCALAPPDATA%\Fossight` contains application files only.
