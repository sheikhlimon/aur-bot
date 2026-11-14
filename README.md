# aur-bot 🤖

Automated, security-hardened Arch User Repository (AUR) package updater bot.

Maintains and publishes updates for AUR packages whenever new upstream releases are detected.

---

## 📦 Managed Packages

| Package | Type | Upstream Repository | Description |
|---|---|---|---|
| [`goose-desktop-bin`](https://aur.archlinux.org/packages/goose-desktop-bin) | Binary (`.deb` + Vulkan CLI) | [aaif-goose/goose](https://github.com/aaif-goose/goose) | Prebuilt Goose Desktop & Vulkan CLI |
| [`goose-desktop`](https://aur.archlinux.org/packages/goose-desktop) | Source | [aaif-goose/goose](https://github.com/aaif-goose/goose) | Goose Desktop built from source |

---

## 🔒 Security Architecture

1. **Memory-Safe Deserialization (No `jq`):** Built with pure Python standard library (`json.loads`), completely avoiding `jq` expression injection and C parser CVEs.
2. **Strict SemVer Sanitization:** Upstream tags are validated with a strict regex (`^[0-9]+(\.[0-9]+)+$`) before touching any files or commands, preventing command injection.
3. **No Shell Invocations (`shell=False`):** All subprocess calls (`updpkgsums`, `makepkg`, `git`) use explicit argument lists without invoking shell interpreters.
4. **Asset Verification:** Binary packages verify that all expected release assets exist upstream on GitHub before attempting to update `PKGBUILD`.
5. **Atomic Rollback:** Backups of `PKGBUILD` are automatically restored if checksum generation or `.SRCINFO` creation fails.
6. **Hardened SSH Key Handling:** Deploy keys are scoped to the AUR, saved with `600` permissions, and use host-key verification to prevent MITM attacks.

---

## ⚙️ Configuration (`scripts/packages.json`)

To add a new package, simply add an entry to `scripts/packages.json`:

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

Then copy the initial `PKGBUILD` and `.SRCINFO` into `packages/my-package-bin/`.

---

## 🚀 Running Locally

```bash
# Check status of all packages without making changes
./scripts/updater.py --check-only

# Check a specific package
./scripts/updater.py --package goose-desktop-bin --check-only

# Apply updates locally (requires pacman-contrib installed)
./scripts/updater.py
```

---

## 🔑 GitHub Actions Setup

In your GitHub repository settings (**Settings → Secrets and variables → Actions**), add:

* **`AUR_SSH_PRIVATE_KEY`**: Your private SSH key (without passphrase) paired with the public key on your [AUR Account](https://aur.archlinux.org/account/).
