# Git Workflow and Public/Private Separation

[English](GIT_WORKFLOW.md) | [Japanese](GIT_WORKFLOW.ja.md)

Fossight uses Git branches for **development stages**, not for separating secrets from public code.

## Branch model

```text
main
  ^
develop
  ^
feature/*
```

- `main`: stable, public-ready code only.
- `develop`: integration branch for work that is still under development but is safe to publish.
- `feature/*`: short-lived feature branches created from `develop` and merged back through review.
- A release is promoted from `develop` to `main` after tests and the public-safety review pass.

`hotfix/*` may branch from `main` when an urgent released-version fix is necessary.

## Public and private data are not branch concerns

Never use a branch in this public repository as a place to store secrets, machine-local settings, private source code, or internal-only history.

Use the appropriate boundary instead:

| Concern | Boundary |
| --- | --- |
| Stable vs. development code | Git branch |
| Feature A vs. feature B | Git branch |
| API keys / tokens / private keys | External secret store such as SOPS; never commit |
| Machine-specific settings | Ignored local config |
| Internal-only source code or documents | Separate private repository |
| Generated build artifacts | `.gitignore` / release artifacts |

If a private repository is introduced later, it may be added as a separate `private` remote. It must be a genuinely separate private GitHub repository; private material must never be committed to a branch that can be pushed to the public `origin`.

## Local-only files

Examples of files that must remain outside public history:

```text
.env
.env.*
secrets/
local/
*.key
*.pem
*.p12
*.pfx
local-config.json
config.local.json
*.local.json
```

Public templates are allowed, for example:

```text
.env.example
config.example.json
```

## Public documentation convention

- The canonical public filename is English, for example `README.md`.
- The Japanese counterpart uses `.ja.md`, for example `README.ja.md`.
- Internal orchestration logs, local execution evidence, and developer-machine-specific notes are not public documentation.

## Before pushing to `origin`

At minimum:

1. Confirm the intended branch and remote.
2. Review `git status` and the staged diff.
3. Confirm no real user name, absolute workstation path, account identifier, token, key, or private registry data is staged.
4. Run relevant tests and `git diff --check`.
5. Push the intended branch explicitly. Avoid `git push --all` on the public remote.

## Recommended flow

```text
git switch develop
git switch -c feature/example
# implement + test
git push -u origin feature/example
# review / merge into develop
# release review / merge develop into main
```

The public `origin` may contain `main`, `develop`, and publish-safe `feature/*` branches. Anything that would not be acceptable if publicly visible does not belong anywhere in this repository's public branch graph.
