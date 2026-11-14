# aur-bot

Automated package updater for the Arch User Repository (AUR). Tracks upstream releases, updates PKGBUILDs and integrity checksums, and publishes releases on a schedule.

## Managed Packages

| Package | Type | Upstream | Description |
|---|---|---|---|
| [`goose-desktop-bin`](https://aur.archlinux.org/packages/goose-desktop-bin) | Binary (`.deb` + Vulkan CLI) | [aaif-goose/goose](https://github.com/aaif-goose/goose) | Prebuilt Goose Desktop & Vulkan CLI |
| [`goose-desktop`](https://aur.archlinux.org/packages/goose-desktop) | Source | [aaif-goose/goose](https://github.com/aaif-goose/goose) | Goose Desktop compiled from source |

## How It Works

The update engine (`scripts/updater.py`) runs periodically via GitHub Actions:

1. Queries the GitHub Releases API for new upstream versions.
2. Validates release tags and verifies required binary assets exist before modifying files.
3. Updates `pkgver`, resets `pkgrel=1`, and recalculates source hashes using `updpkgsums`.
4. Regenerates `.SRCINFO` metadata via `makepkg --printsrcinfo`.
5. Pushes verified changes to the corresponding AUR repositories over SSH.

## Configuration

Package targets are defined in `scripts/packages.json`:

```json
{
  "name": "my-package-bin",
  "upstream": "owner/repo",
  "type": "bin",
  "assets": [
    "app_{version}_amd64.deb"
  ],
  "aur_repo": "ssh://aur@aur.archlinux.org/my-package-bin.git"
}
```

To track a new package, add its entry to `packages.json` and place its initial `PKGBUILD` and `.SRCINFO` in `packages/<name>/`.

## Local Usage

```bash
# Check status without applying changes
./scripts/updater.py --check-only

# Check a single package
./scripts/updater.py --package goose-desktop-bin --check-only

# Apply updates locally (requires pacman-contrib)
./scripts/updater.py
```

## Manual Patches & GitOps

To fix or patch a package manually:
1. Edit `packages/<name>/PKGBUILD` and bump `pkgrel`.
2. Commit and push to `main`:
   ```bash
   git commit -am "fix(<name>): apply packaging patch"
   git push origin main
   ```
GitHub Actions will automatically validate the `PKGBUILD`, regenerate `.SRCINFO`, and publish the release directly to the AUR.

## Setup

Configure the following secret in your repository (**Settings → Secrets and variables → Actions**):

* `AUR_SSH_PRIVATE_KEY`: Private SSH key registered with your [AUR account](https://aur.archlinux.org/account/).
