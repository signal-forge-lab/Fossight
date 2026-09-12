# Fossight Security and Privacy

**English** | [Japanese](FOSSIGHT_SECURITY_PRIVACY.ja.md)

## Local-first model

Fossight's UI/backend binds only to `127.0.0.1` and is not exposed to the LAN. Registry, state, reports, metadata cache, and logs are stored in `%LOCALAPPDATA%\FossightData`.

## Network access

Network requests are primarily used for GitHub repository metadata and update checks. Repository discovery itself inspects local Git checkouts and their configured remote URLs.

## GitHub credentials

Fossight can use `GITHUB_TOKEN`, `GH_TOKEN`, or GitHub CLI authentication. Token values are not written to `config.json`, the registry, status APIs, logs by design, or release artifacts. The UI reports only the authentication source/state such as `anonymous` or `gh_cli`.

## Repository mutation policy

Scanner operations and local status comparisons do not mutate working trees. Quick Scan and Deep Scan inspect repository metadata only; they do not run checkout, merge, pull, push, or reset. Registry mutation happens only after preview when the user selects **Add selected**.

## API boundary

- bind address: `127.0.0.1` only
- bounded JSON request body size
- malformed, oversized, and non-JSON requests are rejected
- CSP, `nosniff`, no-referrer, and no-store style security headers are applied
- the packaged backend chooses an available localhost port dynamically

## Packaged artifacts

Release QA scans the installer, desktop executable, and sidecar at the byte level for developer-specific absolute paths and representative credential markers. Rust release builds use path remapping so build-user Cargo registry paths are not embedded in the shipped desktop executable.

## User-data retention

Application files under `%LOCALAPPDATA%\Fossight` are separate from mutable data under `%LOCALAPPDATA%\FossightData`. Uninstallation intentionally preserves user data. Full deletion is an explicit user action.

## Metadata cache

Descriptions derived from GitHub descriptions or README content are stored in a local metadata cache. Previously cached metadata can be displayed while offline. No LLM service is required at runtime.

## Code signing

The Fossight 1.0.0 distribution candidate was validated as an unsigned installer. Authenticode signing requires an external code-signing certificate/secret and is deliberately not stored in this repository.
