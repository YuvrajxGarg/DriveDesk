"""Small, testable rclone adapter. Never prints configuration contents."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event
from urllib.parse import parse_qs, urlsplit


@dataclass(frozen=True)
class Entry:
    name: str
    path: str
    is_dir: bool
    size: int = -1
    modified: str = ""
    owner: str = ""
    id: str = ""
    resource_key: str = ""
    mime_type: str = ""


def network_env() -> dict[str, str]:
    """Ignore the disconnected loopback proxy injected into some Codex sessions."""
    env = os.environ.copy()
    for key in list(env):
        if "proxy" not in key.lower():
            continue
        url = urlsplit(env[key])
        if url.hostname in ("127.0.0.1", "localhost") and url.port == 9:
            del env[key]
    return env


def find_rclone(saved: str = "") -> str | None:
    candidates = [saved, shutil.which("rclone")]
    home = Path.home()
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        candidates += [str(executable_dir / "rclone"), str(executable_dir / "rclone.exe")]
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates += [str(Path(meipass) / "rclone"), str(Path(meipass) / "rclone.exe")]
    candidates += [
        str(home / "scoop/apps/rclone/current/rclone.exe"),
        str(home / "AppData/Local/Programs/rclone/rclone.exe"),
        r"C:\Program Files\rclone\rclone.exe",
        r"C:\ProgramData\chocolatey\bin\rclone.exe",
        str(home / ".local/bin/rclone"),
        "/opt/homebrew/bin/rclone",
        "/usr/local/bin/rclone",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    downloads = home / "Downloads"
    if downloads.is_dir():
        for pattern in ("rclone*/**/rclone.exe", "rclone*/**/rclone"):
            for candidate in downloads.glob(pattern):
                if candidate.is_file():
                    return str(candidate.resolve())
    return None


class RcloneError(RuntimeError):
    pass


def parse_transfer_stats(line: str) -> dict[str, str | int] | None:
    """Extract byte progress from rclone's one-line human-readable stats."""
    match = re.search(
        r"Transferred:\s*([^,/]+?)\s*/\s*([^,]+),\s*(\d{1,3})%"
        r"(?:,\s*([^,]+?/[sS]))?(?:,\s*ETA\s+([^,]+))?",
        line,
    )
    if not match:
        return None
    return {
        "done": match.group(1).strip(),
        "total": match.group(2).strip(),
        "percent": min(100, int(match.group(3))),
        "speed": (match.group(4) or "—").strip(),
        "eta": (match.group(5) or "—").strip(),
    }


def transfer_event(obj: dict) -> dict | None:
    """Normalise one rclone ``--use-json-log`` line into a transfer UI event.

    Returns a ``stats`` event (overall totals plus the files currently moving),
    a ``file_done`` event when rclone finishes an individual object, or ``None``
    for log lines the transfer view does not care about.
    """
    if not isinstance(obj, dict):
        return None
    stats = obj.get("stats")
    if isinstance(stats, dict):
        transferring = []
        for item in stats.get("transferring") or []:
            if not isinstance(item, dict):
                continue
            total = int(item.get("size") or 0)
            done = int(item.get("bytes") or 0)
            percent = item.get("percentage")
            if percent is None:
                percent = int(done * 100 / total) if total > 0 else 0
            transferring.append({
                "name": item.get("name", ""),
                "done": done,
                "total": total,
                "percent": max(0, min(100, int(percent))),
                "speed": float(item.get("speedAvg") or item.get("speed") or 0),
                "eta": item.get("eta"),
            })
        total_bytes = int(stats.get("totalBytes") or 0)
        done_bytes = int(stats.get("bytes") or 0)
        return {
            "kind": "stats",
            "overall": {
                "done": done_bytes,
                "total": total_bytes,
                "percent": int(done_bytes * 100 / total_bytes) if total_bytes > 0 else 0,
                "speed": float(stats.get("speed") or 0),
                "eta": stats.get("eta"),
                "files_done": int(stats.get("transfers") or 0),
                "files_total": int(stats.get("totalTransfers") or 0),
            },
            "transferring": transferring,
        }
    name = obj.get("object")
    message = obj.get("msg", "")
    if name and obj.get("level") == "info" and any(
            key in message for key in ("Copied", "Updated", "Multi-thread", "Deleted")):
        return {"kind": "file_done", "name": name}
    return None


def parse_drive_folder_url(value: str) -> tuple[str, str]:
    """Return (folder ID, optional resource key) from a Google Drive folder link."""
    url = urlsplit(value.strip())
    if url.scheme != "https" or (url.hostname or "").lower() != "drive.google.com":
        raise ValueError("Paste an https://drive.google.com folder link.")
    match = re.fullmatch(r"/drive(?:/u/\d+)?/folders/([A-Za-z0-9_-]+)(?:/)?", url.path)
    query = parse_qs(url.query)
    folder_id = match.group(1) if match else (query.get("id", [""])[0] if url.path == "/open" else "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,}", folder_id):
        raise ValueError("This link does not contain a Google Drive folder ID.")
    resource_key = query.get("resourcekey", [""])[0]
    if resource_key and not re.fullmatch(r"[A-Za-z0-9_-]+", resource_key):
        raise ValueError("This link has an invalid resource key.")
    return folder_id, resource_key


# Backends exposed in the "Add remote" wizard. OAuth backends open a browser to
# authorize; the rest are configured from typed fields. Each field is
# (key, human label, default, is_secret).
OAUTH_BACKENDS = {"drive", "dropbox", "onedrive", "box", "pcloud", "googlephotos", "yandex"}

BACKENDS: dict[str, dict] = {
    "drive": {"label": "Google Drive", "fields": []},
    "dropbox": {"label": "Dropbox", "fields": []},
    "onedrive": {"label": "Microsoft OneDrive", "fields": []},
    "box": {"label": "Box", "fields": []},
    "pcloud": {"label": "pCloud", "fields": []},
    "googlephotos": {"label": "Google Photos", "fields": []},
    "s3": {"label": "Amazon S3 / compatible", "fields": [
        ("provider", "Provider (AWS, Wasabi, Minio, Other)", "AWS", False),
        ("access_key_id", "Access Key ID", "", False),
        ("secret_access_key", "Secret Access Key", "", True),
        ("region", "Region (e.g. us-east-1)", "", False),
        ("endpoint", "Endpoint (blank for AWS)", "", False)]},
    "b2": {"label": "Backblaze B2", "fields": [
        ("account", "Account / Key ID", "", False),
        ("key", "Application Key", "", True)]},
    "sftp": {"label": "SFTP server", "fields": [
        ("host", "Host", "", False),
        ("user", "Username", "", False),
        ("port", "Port", "22", False),
        ("pass", "Password", "", True)]},
    "mega": {"label": "MEGA", "fields": [
        ("user", "Email", "", False),
        ("pass", "Password", "", True)]},
    "webdav": {"label": "WebDAV", "fields": [
        ("url", "Server URL", "", False),
        ("vendor", "Vendor (nextcloud, owncloud, other)", "other", False),
        ("user", "Username", "", False),
        ("pass", "Password", "", True)]},
}


class Rclone:
    def __init__(self, executable: str):
        self.executable = executable

    def run(self, *args: str, timeout: int = 90) -> str:
        try:
            result = subprocess.run(
                [self.executable, *args], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=timeout,
                env=network_env(),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as exc:
            raise RcloneError(f"rclone did not respond within {timeout} seconds. Check your internet connection and try Refresh.") from exc
        except OSError as exc:
            raise RcloneError(str(exc)) from exc
        if result.returncode:
            raise RcloneError((result.stderr or result.stdout).strip() or f"rclone exited with {result.returncode}")
        return result.stdout

    def drives(self) -> list[str]:
        # config dump stays entirely in memory. We only retain names and types.
        try:
            config = json.loads(self.run("config", "dump"))
            return sorted((name for name, values in config.items() if values.get("type") == "drive"),
                          key=lambda name: (not bool(config[name].get("client_id")), name.casefold()))
        except (ValueError, RcloneError):
            # Some encrypted configurations require a password supplied in the environment.
            raise RcloneError("Could not read the rclone configuration. Unlock it in rclone first, or set RCLONE_CONFIG_PASS.")

    def remotes(self) -> list[tuple[str, str]]:
        """Every configured remote as (name, backend type), Drive accounts first."""
        try:
            config = json.loads(self.run("config", "dump"))
        except (ValueError, RcloneError):
            raise RcloneError("Could not read the rclone configuration. Unlock it in rclone first, or set RCLONE_CONFIG_PASS.")
        pairs = [(name, values.get("type", "")) for name, values in config.items()]
        return sorted(pairs, key=lambda pair: (pair[1] != "drive", pair[0].casefold()))

    def _config_oauth(self, args: list[str], name: str, cancelled: Event, timeout: int) -> None:
        """Run an rclone config-create that opens a browser, cleaning up a failed remote."""
        try:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding="utf-8", errors="replace",
                                    env=network_env(),
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            raise RcloneError(str(exc)) from exc
        deadline = time.monotonic() + timeout
        try:
            while True:
                if cancelled.is_set():
                    raise RcloneError("Sign-in was cancelled.")
                if time.monotonic() >= deadline:
                    raise RcloneError("Sign-in timed out. Try adding the remote again.")
                try:
                    _out, err = proc.communicate(timeout=0.5)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if proc.returncode:
                last_error = (err or "").strip().splitlines()[-1:] or ["Sign-in did not complete."]
                raise RcloneError(last_error[0][:250])
        except RcloneError:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
            try:
                self.run("config", "delete", name, timeout=15)
            except RcloneError:
                pass
            raise

    def create_remote(self, name: str, backend: str, params: dict[str, str],
                      cancelled: Event, timeout: int = 300) -> None:
        """Create any supported remote. OAuth backends open a browser; others use typed fields."""
        self._valid_remote_name(name)
        if backend not in BACKENDS:
            raise RcloneError(f"Unsupported backend: {backend}")
        flat: list[str] = []
        has_secret = False
        for key, value in params.items():
            if not re.fullmatch(r"[A-Za-z0-9_]+", key):
                raise RcloneError(f"Invalid setting: {key}")
            if str(value) == "":
                continue
            flat += [key, str(value)]
            if key in ("pass", "key", "secret_access_key"):
                has_secret = True
        if backend in OAUTH_BACKENDS:
            args = [self.executable, "config", "create", name, backend, *flat,
                    "config_is_local", "true"]
            if backend == "drive":
                args += ["config_shared_client_id", "true"]
            self._config_oauth(args, name, cancelled, timeout)
        else:
            run_args = ["config", "create", name, backend, *flat]
            if has_secret:
                run_args.append("--obscure")
            self.run(*run_args, timeout=120)

    def create_drive(self, name: str, cancelled: Event, timeout: int = 300) -> None:
        """Start rclone's browser OAuth flow without its interactive CLI wizard."""
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,40}", name):
            raise RcloneError("Invalid account identifier")
        args = [self.executable, "config", "create", name, "drive", "scope", "drive",
                "config_shared_client_id", "true", "config_is_local", "true"]
        try:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding="utf-8", errors="replace",
                                    env=network_env(),
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            raise RcloneError(str(exc)) from exc
        deadline = time.monotonic() + timeout
        try:
            while True:
                if cancelled.is_set():
                    raise RcloneError("Google sign-in was cancelled.")
                if time.monotonic() >= deadline:
                    raise RcloneError("Google sign-in timed out. Try adding the account again.")
                try:
                    _out, err = proc.communicate(timeout=0.5)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if proc.returncode:
                last_error = (err or "").strip().splitlines()[-1:] or ["Google sign-in did not complete."]
                raise RcloneError(last_error[0][:250])
        except RcloneError:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
            # The name was generated for this attempt; remove any partial remote.
            try:
                self.run("config", "delete", name, timeout=15)
            except RcloneError:
                pass
            raise

    def user_label(self, name: str) -> str:
        try:
            info = json.loads(self.run("config", "userinfo", f"{name}:", "--json", timeout=20))
            if isinstance(info, dict):
                for key in ("email", "Email", "user", "User", "username", "Username"):
                    value = info.get(key)
                    if isinstance(value, str) and value:
                        return value
        except (RcloneError, ValueError):
            pass
        return name

    @staticmethod
    def _valid_remote_name(name: str) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,40}", name):
            raise RcloneError("Invalid account identifier")

    def delete_remote(self, name: str) -> None:
        """Remove a remote from the rclone configuration (cloud data is untouched)."""
        self._valid_remote_name(name)
        self.run("config", "delete", name, timeout=30)

    def reconnect_drive(self, name: str, cancelled: Event, timeout: int = 300) -> None:
        """Re-run the browser OAuth flow for an existing remote without deleting it."""
        self._valid_remote_name(name)
        args = [self.executable, "config", "reconnect", f"{name}:", "--auto-confirm"]
        try:
            proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                                    env=network_env(),
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            raise RcloneError(str(exc)) from exc
        deadline = time.monotonic() + timeout
        while True:
            if cancelled.is_set():
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.communicate()
                raise RcloneError("Reconnect was cancelled.")
            if time.monotonic() >= deadline:
                if proc.poll() is None:
                    proc.terminate()
                raise RcloneError("Reconnect timed out. Try again.")
            try:
                _out, err = proc.communicate(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                continue
        if proc.returncode:
            last_error = (err or "").strip().splitlines()[-1:] or ["Reconnect did not complete."]
            raise RcloneError(last_error[0][:250])

    def list(self, remote: str, path: str = "", shared: bool = False, metadata: bool = False,
             folder_id: str = "", resource_key: str = "") -> list[Entry]:
        if not remote or any(char in remote for char in ":/\\"):
            raise RcloneError("Invalid remote name")
        if path.startswith("/") or "\\" in path or any(part in (".", "..") for part in path.split("/")):
            raise RcloneError("Invalid remote path")
        args = ["lsjson", f"{remote}:{path}", "--max-depth", "1"]
        if metadata:
            args.append("--metadata")
        if shared:
            args.append("--drive-shared-with-me")
        if folder_id:
            args.extend(["--drive-root-folder-id", folder_id])
            if resource_key:
                args.extend(["--drive-resource-key", resource_key])
        try:
            rows = json.loads(self.run(*args, timeout=60))
        except ValueError as exc:
            raise RcloneError("rclone returned an invalid file listing") from exc
        entries = []
        for row in rows:
            name = row.get("Name", "")
            if not name or name in (".", "..") or "/" in name or "\\" in name:
                continue
            metadata = row.get("Metadata") or {}
            entries.append(Entry(
                name=name,
                path=f"{path.rstrip('/')}/{name}".lstrip("/"),
                is_dir=bool(row.get("IsDir")),
                size=row.get("Size", -1),
                modified=row.get("ModTime", ""),
                owner=metadata.get("owner", "") or "",
                id=row.get("ID", "") or "",
            ))
        return sorted(entries, key=lambda e: (not e.is_dir, e.name.casefold()))

    def search_files(self, remote: str, path: str, term: str, *, limit: int = 800) -> list[Entry]:
        """Recursively find items under a remote path whose name contains ``term``."""
        if not remote or any(char in remote for char in ":/\\"):
            raise RcloneError("Invalid remote name")
        if path.startswith("/") or "\\" in path or any(part in (".", "..") for part in path.split("/")):
            raise RcloneError("Invalid remote path")
        term_l = term.casefold()
        try:
            rows = json.loads(self.run("lsjson", f"{remote}:{path}", "-R", "--no-modtime", timeout=180))
        except ValueError as exc:
            raise RcloneError("rclone returned an invalid file listing") from exc
        prefix = path.rstrip("/")
        matches = []
        for row in rows:
            name = row.get("Name", "")
            if not name or term_l not in name.casefold():
                continue
            rel = (row.get("Path") or name).replace("\\", "/")
            matches.append(Entry(
                name=name,
                path=f"{prefix}/{rel}".lstrip("/") if prefix else rel,
                is_dir=bool(row.get("IsDir")),
                size=row.get("Size", -1),
                modified=row.get("ModTime", ""),
                id=row.get("ID", "") or "",
            ))
            if len(matches) >= limit:
                break
        return sorted(matches, key=lambda e: (not e.is_dir, e.name.casefold()))

    def size(self, remote: str, path: str, *, shared: bool = False,
             folder_id: str = "", resource_key: str = "") -> tuple[int, int]:
        args = ["size", f"{remote}:{path}", "--json"]
        if shared:
            args.append("--drive-shared-with-me")
        if folder_id:
            args += ["--drive-root-folder-id", folder_id]
            if resource_key:
                args += ["--drive-resource-key", resource_key]
        data = json.loads(self.run(*args, timeout=300))
        return int(data.get("bytes", 0)), int(data.get("count", 0))

    def mutate(self, operation: str, remote: str, path: str, *, destination: str = "",
               folder_id: str = "", resource_key: str = "") -> None:
        if operation not in ("mkdir", "moveto", "deletefile", "purge"):
            raise RcloneError("Unsupported file operation")
        args = [operation, f"{remote}:{path}"]
        if operation == "moveto":
            args.append(f"{remote}:{destination}")
        if folder_id:
            args += ["--drive-root-folder-id", folder_id]
            if resource_key:
                args += ["--drive-resource-key", resource_key]
        self.run(*args, timeout=300)


def local_entries(folder: Path) -> list[Entry]:
    entries = []
    try:
        children = list(folder.iterdir())
    except OSError as exc:
        raise RcloneError(str(exc)) from exc
    for child in children:
        try:
            stat = child.stat()
            entries.append(Entry(child.name, str(child), child.is_dir(), stat.st_size if child.is_file() else -1,
                                 datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")))
        except OSError:
            continue
    return sorted(entries, key=lambda e: (not e.is_dir, e.name.casefold()))


SYNC_COMMANDS = {"mirror": "sync", "copy": "copy", "move": "move", "bisync": "bisync"}


def sync_args(source: str, destination: str, mode: str, *, dry_run: bool = False,
              extra: list[str] | None = None) -> list[str]:
    """Build an rclone sync/copy/move/bisync command with structured progress logging."""
    if mode not in SYNC_COMMANDS:
        raise RcloneError(f"Unknown sync mode: {mode}")
    if not source or not destination:
        raise RcloneError("Both a source and destination are required.")
    args = [SYNC_COMMANDS[mode], source, destination,
            "--use-json-log", "--verbose", "--stats", "1s"]
    if mode == "bisync":
        # bisync needs a baseline on first run; --resync establishes it safely.
        args.append("--resync")
    if dry_run:
        args.append("--dry-run")
    if extra:
        args += list(extra)
    return args


def mount_args(remote: str, path: str, drive: str, *, shared: bool = False,
               folder_id: str = "", resource_key: str = "",
               extra: list[str] | None = None) -> list[str]:
    """Build an rclone mount command exposing a remote as a Windows drive letter."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,40}", remote):
        raise RcloneError("Invalid remote name")
    if not re.fullmatch(r"[A-Za-z]:", drive):
        raise RcloneError("Choose a drive letter such as X:")
    target = f"{remote}:{path}" if path else f"{remote}:"
    args = ["mount", target, drive, "--vfs-cache-mode", "full",
            "--volname", f"DriveDesk-{remote}"]
    if shared:
        args.append("--drive-shared-with-me")
    if folder_id:
        args.extend(["--drive-root-folder-id", folder_id])
        if resource_key:
            args.extend(["--drive-resource-key", resource_key])
    if extra:
        args += list(extra)
    return args


def transfer_args(source: Entry, remote: str, remote_folder: str, local_folder: Path,
                  *, upload: bool, shared: bool, replace: bool,
                  folder_id: str = "", resource_key: str = "") -> list[str]:
    """Return argv without a shell. Source paths come from a listing, never hand-built UI text."""
    remote_folder = remote_folder.strip("/")
    remote_path = f"{remote}:{remote_folder}"
    if upload:
        source_path = source.path
        target = f"{remote_path.rstrip('/')}/{source.name}"
    else:
        source_path = f"{remote}:{source.path}"
        target = str(local_folder / source.name)
    args = ["copy" if source.is_dir else "copyto", source_path, target,
            "--stats", "1s", "--use-json-log", "--verbose"]
    if not replace:
        args.append("--ignore-existing")
    if shared and not upload:
        args.append("--drive-shared-with-me")
    if folder_id:
        args.extend(["--drive-root-folder-id", folder_id])
        if resource_key:
            args.extend(["--drive-resource-key", resource_key])
    return args
