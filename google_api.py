"""Google Drive API access for large Shared with me collections.

OAuth tokens remain in memory and are obtained from the user's existing rclone remote.
"""

from __future__ import annotations

import json
import hashlib
import mimetypes
import os
import socket
import time
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from threading import Event, Lock

from PyQt6.QtCore import QSettings

from drive_backend import Entry, Rclone, RcloneError, network_env


FOLDER = "application/vnd.google-apps.folder"
SHORTCUT = "application/vnd.google-apps.shortcut"
EXPORTS = {
    "application/vnd.google-apps.document": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "application/vnd.google-apps.spreadsheet": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "application/vnd.google-apps.presentation": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
    "application/vnd.google-apps.drawing": ("image/svg+xml", ".svg"),
}
FIELDS = "nextPageToken,files(id,name,mimeType,size,modifiedTime,resourceKey,owners(emailAddress,displayName),sharingUser(emailAddress,displayName),shortcutDetails(targetId,targetMimeType,targetResourceKey),capabilities(canDownload,canAddChildren))"


class GoogleDriveAPI:
    _preferred: dict[str, str] = {}
    _preference_lock = Lock()

    def __init__(self, rclone: Rclone, remote: str, *, use_preferred: bool = True):
        self.rclone = rclone
        self.remote = remote
        self.token = ""
        self._load_token()
        if use_preferred:
            with self._preference_lock:
                self._choose_custom_client()

    def _choose_custom_client(self):
        requested = self.remote
        if self.remote in self._preferred:
            preferred = self._preferred[self.remote]
            if preferred != self.remote:
                self.remote = preferred
                self._load_token()
            return
        try:
            config = json.loads(self.rclone.run("config", "dump", timeout=15))
            saved = QSettings("DriveDesk", "DriveDesk").value(f"preferred_shared_remote/{requested}", "")
            saved_fingerprint = QSettings("DriveDesk", "DriveDesk").value(
                f"preferred_shared_fingerprint/{requested}", "")
            if (saved and saved_fingerprint and saved in config and config[saved].get("type") == "drive" and config[saved].get("client_id")
                    and saved_fingerprint == self._mapping_fingerprint(config, requested, saved)):
                self.remote = saved
                self._load_token()
                self._preferred[requested] = saved
                return
            if config[self.remote].get("client_id"):
                self._preferred[self.remote] = self.remote
                return
            candidates = [name for name, values in config.items()
                          if name != self.remote and values.get("type") == "drive" and values.get("client_id")]
            if not candidates:
                self._preferred[self.remote] = self.remote
                return
            current_id = (self._json("https://www.googleapis.com/drive/v3/about?fields=user(permissionId)")
                          .get("user") or {}).get("permissionId")
            if current_id:
                for candidate in candidates:
                    other = GoogleDriveAPI(self.rclone, candidate, use_preferred=False)
                    other_id = (other._json("https://www.googleapis.com/drive/v3/about?fields=user(permissionId)")
                                .get("user") or {}).get("permissionId")
                    if other_id == current_id:
                        self.remote, self.token = other.remote, other.token
                        self._preferred[requested] = candidate
                        QSettings("DriveDesk", "DriveDesk").setValue(
                            f"preferred_shared_remote/{requested}", candidate)
                        QSettings("DriveDesk", "DriveDesk").setValue(
                            f"preferred_shared_fingerprint/{requested}",
                            self._mapping_fingerprint(config, requested, candidate))
                        return
        except (RcloneError, KeyError, ValueError, OSError):
            pass
        self._preferred[self.remote] = self.remote

    @staticmethod
    def _mapping_fingerprint(config: dict, source: str, target: str) -> str:
        def refresh(name: str) -> str:
            raw = config[name].get("token", "")
            token = json.loads(raw) if isinstance(raw, str) else raw
            return token.get("refresh_token", "")
        source_token, target_token = refresh(source), refresh(target)
        if not source_token or not target_token:
            return ""
        return hashlib.sha256(f"{source_token}\0{target_token}".encode()).hexdigest()

    def _load_token(self):
        config = json.loads(self.rclone.run("config", "dump", timeout=15))
        token = config[self.remote].get("token", "")
        data = json.loads(token) if isinstance(token, str) else token
        self.token = data["access_token"]
        expiry = data.get("expiry", "")
        if expiry:
            expires_at = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            if expires_at < datetime.now(timezone.utc):
                self._refresh_token()

    def _refresh_token(self):
        self.rclone.run("about", f"{self.remote}:", timeout=30)
        config = json.loads(self.rclone.run("config", "dump", timeout=15))
        token = config[self.remote].get("token", "")
        self.token = (json.loads(token) if isinstance(token, str) else token)["access_token"]

    def account_label(self) -> str:
        user = self._json("https://www.googleapis.com/drive/v3/about?fields=user(displayName,emailAddress)").get("user") or {}
        name, email = user.get("displayName", ""), user.get("emailAddress", "")
        return f"{name} ({email})" if name and email else (name or email or self.remote)

    def _open(self, url: str, *, method: str = "GET", data: bytes | None = None,
              headers: dict[str, str] | None = None, resource_id: str = "", resource_key: str = "",
              allow_incomplete: bool = False):
        additional = dict(headers or {})
        if resource_id and resource_key:
            additional["X-Goog-Drive-Resource-Keys"] = f"{resource_id}/{resource_key}"
        for attempt in range(2):
            request = urllib.request.Request(
                url, data=data, method=method,
                headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json", **additional},
            )
            try:
                # The dead localhost:9 proxy used by some hosted sessions must not reach urllib.
                proxies = urllib.request.getproxies()
                if any("127.0.0.1:9" in value for value in proxies.values()):
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                else:
                    opener = urllib.request.build_opener()
                return opener.open(request, timeout=30)
            except urllib.error.HTTPError as exc:
                if exc.code == 308 and allow_incomplete:
                    return exc
                detail = exc.read(500).decode("utf-8", "replace")
                if exc.code == 401 and attempt == 0:
                    self._refresh_token()
                    continue
                if exc.code in (403, 429) and ("rateLimitExceeded" in detail or "Quota exceeded" in detail):
                    raise RcloneError("Google Drive API request quota reached. More shared items will load after the quota resets.") from exc
                raise RcloneError(f"Google Drive API returned HTTP {exc.code}: {detail[:240]}") from exc
            except OSError as exc:
                raise RcloneError(f"Google Drive API connection failed: {exc}") from exc
        raise RcloneError("Google Drive authorization failed")

    def _json(self, url: str, **kwargs) -> dict:
        with self._open(url, **kwargs) as response:
            return json.load(response)

    @staticmethod
    def _entry(row: dict, prefix: str = "") -> Entry | None:
        name = row.get("name", "")
        if not name or "/" in name or "\\" in name or name in (".", ".."):
            return None
        mime = row.get("mimeType", "")
        item_id, resource_key = row.get("id", ""), row.get("resourceKey", "")
        if mime == SHORTCUT:
            target = row.get("shortcutDetails") or {}
            item_id = target.get("targetId", item_id)
            resource_key = target.get("targetResourceKey", resource_key)
            mime = target.get("targetMimeType", mime)
        person = row.get("sharingUser") or (row.get("owners") or [{}])[0]
        owner = person.get("displayName") or person.get("emailAddress") or "Unknown owner"
        return Entry(name, f"{prefix}/{name}".lstrip("/"), mime == FOLDER,
                     int(row.get("size") or -1), row.get("modifiedTime", ""), owner,
                     item_id, resource_key, mime)

    def list_files(self, *, folder_id: str = "", resource_key: str = "", prefix: str = "",
                   page_token: str = "", on_page=None) -> list[Entry]:
        query = (f"'{folder_id}' in parents and trashed = false" if folder_id else
                 "sharedWithMe = true and trashed = false")
        entries: list[Entry] = []
        while True:
            params = {"q": query, "fields": FIELDS, "pageSize": "1000", "supportsAllDrives": "true",
                      "includeItemsFromAllDrives": "true"}
            if page_token:
                params["pageToken"] = page_token
            url = "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params)
            try:
                data = self._json(url, resource_id=folder_id, resource_key=resource_key)
            except RcloneError as exc:
                if entries and "quota" in str(exc).lower():
                    return entries
                raise
            batch = []
            for row in data.get("files", []):
                entry = self._entry(row, prefix)
                if entry:
                    batch.append(entry)
            entries.extend(batch)
            page_token = data.get("nextPageToken", "")
            if on_page:
                on_page(batch, page_token)
            if not page_token:
                break
        return sorted(entries, key=lambda e: (e.owner.casefold() if not folder_id else "", not e.is_dir, e.name.casefold()))

    def folder_name(self, folder_id: str, resource_key: str = "") -> str:
        url = (f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(folder_id)}"
               "?fields=name&supportsAllDrives=true")
        data = self._json(url, resource_id=folder_id, resource_key=resource_key)
        return data.get("name", "") or "Shared folder"

    def create_folder(self, name: str, parent_id: str, parent_key: str = "") -> str:
        if not parent_id:
            raise RcloneError("Open a shared folder before creating a folder.")
        body = json.dumps({"name": name, "mimeType": FOLDER, "parents": [parent_id]}).encode()
        result = self._json("https://www.googleapis.com/drive/v3/files?fields=id", method="POST", data=body,
                            headers={"Content-Type": "application/json; charset=utf-8"},
                            resource_id=parent_id, resource_key=parent_key)
        return result["id"]

    def calculate_size(self, entry: Entry) -> tuple[int, int]:
        if not entry.is_dir:
            return max(0, entry.size), 1
        total = count = 0
        for child in self.list_files(folder_id=entry.id, resource_key=entry.resource_key):
            child_size, child_count = self.calculate_size(child)
            total += child_size
            count += child_count
        return total, count

    def rename(self, entry: Entry, name: str):
        url = f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(entry.id)}?fields=id"
        body = json.dumps({"name": name}).encode()
        self._json(url, method="PATCH", data=body,
                   headers={"Content-Type": "application/json; charset=utf-8"},
                   resource_id=entry.id, resource_key=entry.resource_key)

    def delete(self, entry: Entry):
        url = f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(entry.id)}"
        with self._open(url, method="DELETE", resource_id=entry.id, resource_key=entry.resource_key):
            pass

    def download(self, entry: Entry, local_path: Path, *, replace: bool, cancelled: Event,
                 progress) -> None:
        if entry.is_dir:
            local_path.mkdir(parents=True, exist_ok=True)
            for child in self.list_files(folder_id=entry.id, resource_key=entry.resource_key, prefix=entry.path):
                if cancelled.is_set():
                    raise RcloneError("Cancelled")
                self.download(child, local_path / child.name, replace=replace, cancelled=cancelled, progress=progress)
            return
        export = EXPORTS.get(entry.mime_type)
        if entry.mime_type.startswith("application/vnd.google-apps.") and not export:
            raise RcloneError(f"This Google file type cannot be exported: {entry.mime_type}")
        if export:
            local_path = local_path.with_name(local_path.name + export[1])
            url = (f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(entry.id)}/export?" +
                   urllib.parse.urlencode({"mimeType": export[0]}))
        else:
            url = f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(entry.id)}?alt=media"
        if local_path.exists() and not replace:
            return
        local_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = local_path.with_name(local_path.name + ".drivedesk-part")
        started = time.monotonic()
        done = temporary.stat().st_size if temporary.exists() else 0
        retries = 0
        try:
            while True:
                if cancelled.is_set():
                    raise RcloneError("Cancelled")
                headers = {"Range": f"bytes={done}-"} if done else None
                try:
                    with self._open(url, headers=headers, resource_id=entry.id,
                                    resource_key=entry.resource_key) as response:
                        # A server may ignore Range. Never append a full response to a
                        # partial file, or the resulting file will be corrupt.
                        resumed = done > 0 and getattr(response, "status", 200) == 206
                        if done and not resumed:
                            done = 0
                        content_range = response.headers.get("Content-Range", "")
                        total = int(response.headers.get("Content-Length") or entry.size or 0)
                        if resumed and "/" in content_range:
                            try:
                                total = int(content_range.rsplit("/", 1)[1])
                            except ValueError:
                                pass
                        mode = "ab" if resumed else "wb"
                        with temporary.open(mode) as target:
                            while True:
                                if cancelled.is_set():
                                    raise RcloneError("Cancelled")
                                chunk = response.read(1024 * 1024)
                                if not chunk:
                                    break
                                target.write(chunk)
                                done += len(chunk)
                                progress(done, total, started)
                    os.replace(temporary, local_path)
                    break
                except RcloneError as exc:
                    transient = any(word in str(exc).lower() for word in
                                    ("timed out", "timeout", "connection failed", "reset"))
                    if not transient or retries >= 4:
                        raise
                    retries += 1
                    time.sleep(min(2 ** retries, 8))
                except (OSError, socket.timeout, TimeoutError) as exc:
                    if cancelled.is_set() or retries >= 4:
                        raise RcloneError(f"Google Drive download interrupted: {exc}") from exc
                    retries += 1
                    time.sleep(min(2 ** retries, 8))
        finally:
            if temporary.exists():
                temporary.unlink()

    def upload(self, local_path: Path, parent_id: str, *, parent_key: str = "",
               replace: bool, cancelled: Event, progress) -> None:
        if not parent_id:
            raise RcloneError("Open a shared folder with edit access before uploading.")
        if local_path.is_dir():
            existing = self.list_files(folder_id=parent_id, resource_key=parent_key)
            folder = next((entry for entry in existing if entry.name == local_path.name and entry.is_dir), None)
            child_id = folder.id if folder else self.create_folder(local_path.name, parent_id, parent_key)
            for child in local_path.iterdir():
                if cancelled.is_set():
                    raise RcloneError("Cancelled")
                self.upload(child, child_id, parent_key="", replace=replace,
                            cancelled=cancelled, progress=progress)
            return
        existing = self.list_files(folder_id=parent_id, resource_key=parent_key)
        match = next((entry for entry in existing if entry.name == local_path.name), None)
        if match and not replace:
            return
        size = local_path.stat().st_size
        mime = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
        if match:
            url = f"https://www.googleapis.com/upload/drive/v3/files/{urllib.parse.quote(match.id)}?uploadType=resumable"
            method, metadata = "PATCH", {}
        else:
            url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable"
            method, metadata = "POST", {"name": local_path.name, "parents": [parent_id]}
        request_body = json.dumps(metadata).encode()
        with self._open(url, method=method, data=request_body,
                        headers={"Content-Type": "application/json; charset=utf-8",
                                 "X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(size)},
                        resource_id=parent_id, resource_key=parent_key) as response:
            session = response.headers["Location"]
        started = time.monotonic()
        sent = 0
        with local_path.open("rb") as source:
            while sent < size or (size == 0 and sent == 0):
                if cancelled.is_set():
                    raise RcloneError("Cancelled")
                chunk = source.read(8 * 1024 * 1024)
                end = sent + len(chunk) - 1
                with self._open(session, method="PUT", data=chunk,
                                headers={"Content-Type": mime,
                                         "Content-Range": f"bytes {sent}-{end}/{size}" if size else "bytes */0"},
                                allow_incomplete=True) as response:
                    status = response.status if hasattr(response, "status") else response.code
                sent += len(chunk)
                progress(sent, size, started)
                if status in (200, 201):
                    break
                if size == 0:
                    raise RcloneError("Empty upload did not complete")
