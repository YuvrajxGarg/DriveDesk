"""Lightweight GitHub-releases update check.

Compares the running APP_VERSION against the latest published release and, when a
newer one exists, returns its download link. Pure/network helpers only — the UI
lives in app.py.
"""

from __future__ import annotations

import json
import os
import platform as platform_info
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

APP_VERSION = "1.2.1"
GITHUB_REPO = "YuvrajxGarg/DriveDesk"


class UpdaterError(RuntimeError):
    """A user-facing update service error."""


def parse_version(tag: str) -> tuple[int, ...]:
    """Turn a tag like 'v1.2.3' into (1, 2, 3); non-numeric parts become 0."""
    cleaned = (tag or "").strip().lstrip("vV")
    parts = []
    for chunk in cleaned.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


def is_newer(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def _pick_asset(assets: list, platform: str | None = None) -> str:
    platform = platform or sys.platform
    endings = ((".exe",) if platform == "win32" else
               ((".dmg", ".zip") if platform == "darwin" else (".AppImage", ".tar.gz", ".zip")))
    preferred_arch = ""
    if platform == "darwin":
        preferred_arch = "arm64" if platform_info.machine().lower() in ("arm64", "aarch64") else "x64"
    for ending in endings:
        matching = [asset for asset in assets or []
                    if (asset.get("name") or "").lower().endswith(ending.lower())]
        if preferred_arch:
            for asset in matching:
                if preferred_arch in (asset.get("name") or "").lower():
                    return asset.get("browser_download_url", "")
        if matching:
            return matching[0].get("browser_download_url", "")
    return ""


def fetch_latest_release(repo: str, *, timeout: int = 12) -> dict:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": "DriveDesk-Updater"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdaterError("No published DriveDesk release was found on GitHub yet.") from exc
        raise UpdaterError(f"GitHub returned HTTP {exc.code} while checking for updates.") from exc
    except urllib.error.URLError as exc:
        raise UpdaterError(f"Could not reach GitHub: {exc.reason}") from exc
    return {
        "tag": data.get("tag_name", ""),
        "url": data.get("html_url", ""),
        "asset": _pick_asset(data.get("assets") or []),
        "notes": (data.get("body") or "").strip(),
    }


def check_for_update(repo: str, current: str) -> dict | None:
    """Return release info when a newer version exists, else None."""
    info = fetch_latest_release(repo)
    if info["tag"] and is_newer(info["tag"], current):
        return info
    return None


def download_update(info: dict, *, progress: Callable[[int, int], None] | None = None,
                    destination: str | os.PathLike[str] | None = None,
                    timeout: int = 60) -> str:
    """Download a release installer and return its local path.

    The release API deliberately supplies the asset URL; the app never executes
    an arbitrary URL or downloads anything unless the user clicks Download.
    """
    asset_url = info.get("asset", "")
    if not asset_url:
        raise ValueError("This release does not contain an installer for your operating system.")
    filename = Path(urllib.request.url2pathname(asset_url.split("?")[0])).name
    if not filename.lower().endswith((".exe", ".dmg", ".zip", ".appimage", ".tar.gz")):
        filename = "DriveDesk-update.exe" if sys.platform == "win32" else "DriveDesk-update.dmg"
    target_dir = Path(destination) if destination else Path(tempfile.gettempdir()) / "DriveDesk-updates"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    request = urllib.request.Request(
        asset_url,
        headers={"Accept": "application/octet-stream", "User-Agent": "DriveDesk-Updater"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response, target.open("wb") as output:
        total = int(response.headers.get("Content-Length") or 0)
        received = 0
        while True:
            chunk = response.read(1024 * 128)
            if not chunk:
                break
            output.write(chunk)
            received += len(chunk)
            if progress:
                progress(received, total)
    return str(target)
