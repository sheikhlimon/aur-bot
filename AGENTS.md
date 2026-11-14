# AGENTS.md

Operational guidelines for AI agents working in `aur-bot`.

## Git Conventions
- Follow Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `perf:` (e.g., `fix(goose-desktop-bin): bump pkgrel to 3`).
- NEVER sign off commits (`-s`). Global Git config already handles author identity and GPG/SSH signing.
- NEVER include commit bodies. Use a single concise subject line only.

## Architecture & Boundaries
- `scripts/updater.py`: Standalone Python CLI engine. Must strictly use the Python standard library with zero external dependencies (no `pip`, `requests`, or `pydantic`).
- `scripts/packages.json`: Package catalog schema. Each entry must define `name`, `upstream`, `type` (`bin` or `source`), and `aur_repo`. For `bin`, define required `assets`.
- `packages/<pkgname>/`: Canonical package source directory containing `PKGBUILD` and `.SRCINFO`.
- `.github/workflows/`:
  - `cron-update.yml`: Scheduled (6h) poll that discovers upstream releases, regenerates sums, and pushes updates to AUR and GitHub.
  - `deploy-on-push.yml`: GitOps push trigger on `packages/**` that validates `PKGBUILD` in Arch container and deploys manual patches to the AUR.

## Security & Implementation Invariants
- SemVer Validation: Always validate version strings against `^[0-9]+(\.[0-9]+)+$` before embedding in commands or filenames to block command/string injection.
- Subprocess Execution: Never pass `shell=True` to `subprocess.run()`. Always use argument arrays.
- Atomic Rollback: When editing `PKGBUILD` programmatically, maintain a `.bak` copy and restore it if `updpkgsums` or `makepkg` fails.
- Loop Prevention: The GitOps deploy workflow must ignore automated commits (`chore(auto):`).

## Commands & Verification
- Check upstream status without altering files:
  `python3 scripts/updater.py --check-only`
- Check single package:
  `python3 scripts/updater.py --package goose-desktop-bin --check-only`
- Run local update:
  `python3 scripts/updater.py`
- Validate package metadata in Arch:
  `cd packages/<pkgname> && makepkg --printsrcinfo > .SRCINFO`
- Test build locally:
  `cd packages/<pkgname> && makepkg -f --nodeps`

## Manual Package Patching Protocol
1. Edit `packages/<pkgname>/PKGBUILD` (add patches or dependencies) and increment `pkgrel`.
2. Regenerate metadata: `makepkg --printsrcinfo > .SRCINFO`.
3. Test build: `makepkg -f --nodeps`.
4. Commit and push: `git commit -am "fix(<pkgname>): description" && git push origin main`.
   GitHub Actions validates and publishes directly to the AUR.
