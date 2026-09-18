"""Previewable native Google Drive folder synchronization."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event

from send2trash import send2trash

from drive_backend import Entry, RcloneError
from google_api import GoogleDriveAPI


@dataclass(frozen=True)
class SyncAction:
    kind: str
    path: str


@dataclass
class SyncPlan:
    actions: list[SyncAction]
    cloud: dict[str, Entry]
    folder_ids: dict[str, str]
    skipped: list[str]
    local_stats: dict[str, tuple[int, int]]


def _checksum(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _included(path: str, excludes: tuple[str, ...], includes: tuple[str, ...]) -> bool:
    name = path.rsplit("/", 1)[-1]
    if _excluded(path, excludes):
        return False
    return not includes or any(fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(name, pattern)
                               for pattern in includes)


def _excluded(path: str, excludes: tuple[str, ...]) -> bool:
    name = path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(name, pattern) for pattern in excludes)


def _local_tree(root: Path, excludes: tuple[str, ...], includes: tuple[str, ...],
                cancelled: Event | None) -> tuple[dict[str, Path], set[str]]:
    result: dict[str, Path] = {}
    directories: set[str] = set()
    for folder, dirs, files in os.walk(root, followlinks=False):
        if cancelled and cancelled.is_set():
            raise RcloneError("Cancelled")
        current = Path(folder)
        dirs[:] = [name for name in dirs if not (current / name).is_symlink() and
                   not _excluded((current / name).relative_to(root).as_posix(), excludes)]
        directories.update((current / name).relative_to(root).as_posix() for name in dirs)
        for name in files:
            path = current / name
            if path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            if _included(relative, excludes, includes):
                result[relative] = path
    return result, directories


def _cloud_tree(api: GoogleDriveAPI, folder_id: str, excludes: tuple[str, ...],
                includes: tuple[str, ...], cancelled: Event | None) -> tuple[dict[str, Entry], dict[str, str], list[str]]:
    files: dict[str, Entry] = {}
    folders = {"": folder_id}
    skipped: list[str] = []
    visited: set[str] = set()

    def visit(parent_id: str, prefix: str):
        if cancelled and cancelled.is_set():
            raise RcloneError("Cancelled")
        if parent_id in visited:
            return
        visited.add(parent_id)
        names: set[str] = set()
        for entry in api.list_files(folder_id=parent_id, prefix=prefix):
            if entry.name.casefold() in names:
                raise RcloneError(f"Duplicate Drive name in {prefix or 'root'}: {entry.name}. Resolve it before syncing.")
            names.add(entry.name.casefold())
            relative = entry.path
            if _excluded(relative, excludes):
                continue
            if entry.is_shortcut:
                skipped.append(relative + " (shortcut)")
            elif entry.is_dir:
                if entry.id in visited:
                    skipped.append(relative + " (folder shortcut loop)")
                    continue
                folders[relative] = entry.id
                visit(entry.id, relative)
            elif entry.mime_type.startswith("application/vnd.google-apps."):
                skipped.append(relative + " (Google document export)")
            elif _included(relative, excludes, includes):
                files[relative] = entry

    visit(folder_id, "")
    return files, folders, skipped


def _same(local: Path, cloud: Entry) -> bool:
    if cloud.size != local.stat().st_size:
        return False
    if cloud.md5:
        return _checksum(local).lower() == cloud.md5.lower()
    if cloud.modified:
        try:
            modified = datetime.fromisoformat(cloud.modified.replace("Z", "+00:00"))
            return abs(local.stat().st_mtime - modified.timestamp()) <= 2
        except ValueError:
            pass
    return False


def _cloud_newer(local: Path, cloud: Entry) -> bool | None:
    if not cloud.modified:
        return None
    try:
        modified = datetime.fromisoformat(cloud.modified.replace("Z", "+00:00"))
    except ValueError:
        return None
    difference = modified.timestamp() - local.stat().st_mtime
    return True if difference > 2 else False if difference < -2 else None


def plan_sync(api: GoogleDriveAPI, local_root: Path, cloud_folder_id: str, *,
              to_cloud: bool, mode: str, excludes: tuple[str, ...] = (),
              includes: tuple[str, ...] = (), cancelled: Event | None = None) -> SyncPlan:
    if mode not in {"copy", "mirror", "move", "bisync"}:
        raise RcloneError("Unsupported sync mode.")
    if not local_root.is_dir() or local_root.is_symlink():
        raise RcloneError("Choose an existing, ordinary local folder for sync.")
    local, local_dirs = _local_tree(local_root, excludes, includes, cancelled)
    cloud, folders, skipped = _cloud_tree(api, cloud_folder_id, excludes, includes, cancelled)
    if skipped and mode in {"mirror", "move"}:
        raise RcloneError("Mirror and move need every Drive item to be supported. "
                          f"{len(skipped)} Google document(s) or shortcut(s) were skipped; use Copy instead.")
    for path in set(local) & set(folders):
        raise RcloneError(f"File/folder name conflict at {path}.")
    for path in set(cloud) & local_dirs:
        raise RcloneError(f"File/folder name conflict at {path}.")

    uploads: list[str] = []
    downloads: list[str] = []
    conflicts: list[str] = []
    paths = sorted(set(local) | set(cloud))
    for path in paths:
        if cancelled and cancelled.is_set():
            raise RcloneError("Cancelled")
        left, right = local.get(path), cloud.get(path)
        if left and right and _same(left, right):
            continue
        if mode == "bisync":
            if left and not right:
                uploads.append(path)
            elif right and not left:
                downloads.append(path)
            elif left and right:
                newer = _cloud_newer(left, right)
                if newer is None:
                    conflicts.append(path)
                elif newer:
                    downloads.append(path)
                else:
                    uploads.append(path)
        elif to_cloud and left:
            uploads.append(path)
        elif not to_cloud and right:
            downloads.append(path)
    if conflicts:
        raise RcloneError(f"{len(conflicts)} two-way conflict(s); resolve them before syncing: " +
                          ", ".join(conflicts[:3]))

    actions: list[SyncAction] = []
    needed_cloud_dirs = {path.rpartition("/")[0] for path in uploads}
    if to_cloud or mode == "bisync":
        needed_cloud_dirs.update(local_dirs)
    missing_cloud_dirs: set[str] = set()
    for path in needed_cloud_dirs:
        while path and path not in folders:
            missing_cloud_dirs.add(path)
            path = path.rpartition("/")[0]
    actions.extend(SyncAction("mkdir_cloud", path) for path in sorted(missing_cloud_dirs, key=lambda p: (p.count("/"), p)))
    if not to_cloud or mode == "bisync":
        missing_local_dirs = set(folders) - local_dirs - {""}
        actions.extend(SyncAction("mkdir_local", path) for path in sorted(missing_local_dirs, key=lambda p: (p.count("/"), p)))
    for path in uploads:
        actions.append(SyncAction("upload", path))
    for path in downloads:
        actions.append(SyncAction("download", path))

    if mode == "move":
        source_paths = [path for path in paths if (path in local if to_cloud else path in cloud)]
        actions.extend(SyncAction("trash_local" if to_cloud else "trash_cloud", path) for path in source_paths)
        if not excludes and not includes:
            source_dirs = local_dirs if to_cloud else set(folders) - {""}
            actions.extend(SyncAction("trash_local_dir" if to_cloud else "trash_cloud_dir", path)
                           for path in sorted(source_dirs, key=lambda p: (-p.count("/"), p)))
    elif mode == "mirror":
        if to_cloud:
            extras = [path for path in cloud if path not in local]
            actions.extend(SyncAction("trash_cloud", path) for path in extras)
            if not excludes and not includes:
                actions.extend(SyncAction("trash_cloud_dir", path)
                               for path in sorted(set(folders) - local_dirs - {""}, key=lambda p: (-p.count("/"), p)))
        else:
            extras = [path for path in local if path not in cloud]
            actions.extend(SyncAction("trash_local", path) for path in extras)
            if not excludes and not includes:
                actions.extend(SyncAction("trash_local_dir", path)
                               for path in sorted(local_dirs - set(folders), key=lambda p: (-p.count("/"), p)))
    signatures = {path: (local_path.stat().st_size, local_path.stat().st_mtime_ns)
                  for path, local_path in local.items()}
    return SyncPlan(actions, cloud, folders, skipped, signatures)


def execute_sync(api: GoogleDriveAPI, local_root: Path, plan: SyncPlan, cancelled: Event,
                 progress) -> None:
    folders = dict(plan.folder_ids)
    for index, action in enumerate(plan.actions, 1):
        api.wait_if_paused()
        if cancelled.is_set():
            raise RcloneError("Cancelled")
        path = action.path
        local_path = local_root.joinpath(*path.split("/"))
        if action.kind in {"upload", "trash_local"} or (action.kind == "download" and path in plan.local_stats):
            expected = plan.local_stats.get(path)
            if expected:
                try:
                    current = local_path.stat()
                except OSError as exc:
                    raise RcloneError(f"Local file changed after preview: {path}") from exc
                if (current.st_size, current.st_mtime_ns) != expected:
                    raise RcloneError(f"Local file changed after preview: {path}")
        if action.kind == "download" and path not in plan.local_stats and local_path.exists():
            raise RcloneError(f"A new local file appeared after preview: {path}")
        if action.kind in {"upload", "download", "trash_cloud"} and path in plan.cloud:
            original = plan.cloud[path]
            current = api.file_metadata(original)
            if (current.get("trashed") or str(current.get("size", -1)) != str(original.size) or
                    current.get("md5Checksum", "") != original.md5 or
                    current.get("modifiedTime", "") != original.modified):
                raise RcloneError(f"Drive file changed after preview: {path}")
        if action.kind == "mkdir_cloud":
            parent = path.rpartition("/")[0]
            folders[path] = api.create_folder(local_path.name, folders[parent])
        elif action.kind == "mkdir_local":
            local_path.mkdir(parents=True, exist_ok=True)
        elif action.kind == "upload":
            parent = path.rpartition("/")[0]
            api.upload(local_path, folders[parent], replace=True, cancelled=cancelled,
                       progress=lambda *_args: None)
        elif action.kind == "download":
            api.download(plan.cloud[path], local_path, replace=True, cancelled=cancelled,
                         progress=lambda *_args: None)
        elif action.kind == "trash_cloud":
            api.trash(plan.cloud[path])
        elif action.kind == "trash_cloud_dir":
            if api.list_files(folder_id=folders[path]):
                raise RcloneError(f"Drive folder changed after preview: {path}")
            api.trash(Entry(local_path.name, path, True, id=folders[path]))
        elif action.kind == "trash_local":
            send2trash(str(local_path))
        elif action.kind == "trash_local_dir":
            if any(local_path.iterdir()):
                raise RcloneError(f"Local folder changed after preview: {path}")
            send2trash(str(local_path))
        else:
            raise RcloneError(f"Unknown sync action: {action.kind}")
        progress(index, len(plan.actions), action)
