#!/usr/bin/env python3
"""
aur-bot: Secure, automated AUR package updater engine.
Handles upstream version discovery, asset verification, integrity checks, and metadata generation.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Strict SemVer pattern (digits and dots only) to block string/command injection
VERSION_PATTERN = re.compile(r"^[0-9]+(\.[0-9]+)+$")


def fetch_latest_release(repo: str) -> dict:
    """Fetch latest release info from GitHub API safely."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {
        "User-Agent": "aur-bot/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"GitHub API returned HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error querying GitHub API: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Malformed JSON from GitHub API: {e}")


def sanitize_version(raw_tag: str) -> str:
    """Validate version string strictly against SemVer regex."""
    clean = raw_tag.lstrip("v").strip()
    if not VERSION_PATTERN.match(clean):
        raise ValueError(
            f"Security Alert: Version '{clean}' violates allowed pattern: {VERSION_PATTERN.pattern}"
        )
    return clean


def get_current_version(pkgbuild_path: Path) -> str:
    """Extract current pkgver from PKGBUILD."""
    content = pkgbuild_path.read_text(encoding="utf-8")
    match = re.search(r"^pkgver=([^\s#]+)", content, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find 'pkgver=' in {pkgbuild_path}")
    return match.group(1).strip()


def verify_assets(release_data: dict, version: str, asset_templates: list) -> bool:
    """Check that all required binary assets are published upstream."""
    expected = {tmpl.replace("{version}", version) for tmpl in asset_templates}
    available = {asset.get("name") for asset in release_data.get("assets", [])}

    missing = expected - available
    if missing:
        print(f"  [!] Missing expected release assets on GitHub:")
        for item in missing:
            print(f"      - {item}")
        return False
    return True


def update_pkgbuild(pkgbuild_path: Path, new_ver: str) -> None:
    """Safely update pkgver and reset pkgrel=1."""
    content = pkgbuild_path.read_text(encoding="utf-8")
    content = re.sub(r"^pkgver=.*$", f"pkgver={new_ver}", content, flags=re.MULTILINE)
    content = re.sub(r"^pkgrel=.*$", "pkgrel=1", content, flags=re.MULTILINE)
    pkgbuild_path.write_text(content, encoding="utf-8")


def run_pacman_tools(pkg_dir: Path) -> None:
    """Execute updpkgsums and makepkg --printsrcinfo safely."""
    print("  [*] Running updpkgsums...")
    subprocess.run(["updpkgsums"], cwd=pkg_dir, check=True, shell=False)

    print("  [*] Regenerating .SRCINFO...")
    srcinfo_path = pkg_dir / ".SRCINFO"
    with open(srcinfo_path, "w", encoding="utf-8") as f:
        subprocess.run(
            ["makepkg", "--printsrcinfo"],
            cwd=pkg_dir,
            stdout=f,
            check=True,
            shell=False,
        )


def process_package(pkg_config: dict, root_dir: Path, check_only: bool = False) -> bool:
    """
    Process a single package configuration.
    Returns True if an update was applied, False otherwise.
    """
    name = pkg_config["name"]
    upstream = pkg_config["upstream"]
    pkg_type = pkg_config.get("type", "bin")
    pkg_dir = root_dir / "packages" / name
    pkgbuild_path = pkg_dir / "PKGBUILD"

    print(f"\n==========================================")
    print(f"[*] Package: {name} (type: {pkg_type})")
    print(f"[*] Upstream: {upstream}")

    if not pkgbuild_path.is_file():
        print(f"[!] Error: PKGBUILD not found at {pkgbuild_path}")
        return False

    current_ver = get_current_version(pkgbuild_path)
    print(f"[*] Current AUR version : {current_ver}")

    try:
        release = fetch_latest_release(upstream)
        latest_ver = sanitize_version(release.get("tag_name", ""))
    except Exception as e:
        print(f"[!] Failed to check upstream: {e}")
        return False

    print(f"[*] Latest Upstream ver : {latest_ver}")

    if latest_ver == current_ver:
        print(f"[+] {name} is already up to date.")
        return False

    if pkg_type == "bin":
        asset_templates = pkg_config.get("assets", [])
        if asset_templates and not verify_assets(release, latest_ver, asset_templates):
            print(f"[!] Upstream assets not yet complete. Skipping {name} for now.")
            return False

    if check_only:
        print(f"[+] Update available for {name}: {current_ver} -> {latest_ver}")
        return True

    print(f"[*] Updating {name} from {current_ver} to {latest_ver}...")
    backup = pkgbuild_path.with_suffix(".bak")
    backup.write_text(pkgbuild_path.read_text(encoding="utf-8"), encoding="utf-8")

    try:
        update_pkgbuild(pkgbuild_path, latest_ver)
        run_pacman_tools(pkg_dir)
        backup.unlink(missing_ok=True)
        print(f"[+] Successfully updated {name} to {latest_ver}!")
        return True
    except Exception as e:
        print(f"[!] Failed to update {name}: {e}. Rolling back PKGBUILD...")
        if backup.is_file():
            pkgbuild_path.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
            backup.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(description="aur-bot: Automated AUR Package Updater")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("scripts/packages.json"),
        help="Path to packages.json configuration file",
    )
    parser.add_argument(
        "--package",
        help="Target a specific package name instead of all packages",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for updates without modifying files",
    )
    parser.add_argument(
        "--output-updated",
        type=Path,
        help="Write list of updated package names to a file (for CI/CD output)",
    )

    args = parser.parse_args()
    root_dir = Path(__file__).resolve().parent.parent
    config_path = root_dir / args.config

    if not config_path.is_file():
        print(f"[!] Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        packages = json.load(f)

    if args.package:
        packages = [p for p in packages if p["name"] == args.package]
        if not packages:
            print(f"[!] Package '{args.package}' not found in configuration.")
            sys.exit(1)

    updated_packages = []
    for pkg in packages:
        updated = process_package(pkg, root_dir, check_only=args.check_only)
        if updated:
            updated_packages.append(pkg["name"])

    print("\n==========================================")
    print(f"[*] Summary: {len(updated_packages)} package(s) updated: {updated_packages}")

    if args.output_updated:
        args.output_updated.write_text(" ".join(updated_packages), encoding="utf-8")


if __name__ == "__main__":
    main()
