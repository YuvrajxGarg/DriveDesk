import hashlib
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from drive_backend import Entry, RcloneError
from google_sync import execute_sync, plan_sync


class FakeApi:
    def __init__(self, rows):
        self.rows = rows
        self.operations = []

    def list_files(self, *, folder_id, prefix=""):
        return self.rows.get(folder_id, [])

    def wait_if_paused(self):
        pass

    def create_folder(self, name, parent):
        self.operations.append(("mkdir", name, parent))
        return "new-folder"

    def upload(self, path, parent, **_kwargs):
        self.operations.append(("upload", path.name, parent))

    def download(self, entry, path, **_kwargs):
        self.operations.append(("download", entry.name, str(path)))

    def trash(self, entry):
        self.operations.append(("trash", entry.name))

    def file_metadata(self, entry):
        return {"id": entry.id, "size": entry.size, "md5Checksum": entry.md5,
                "modifiedTime": entry.modified, "trashed": False}


class NativeSyncTests(unittest.TestCase):
    def test_mirror_previews_copy_before_recoverable_removal(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            root = Path(folder)
            (root / "new.txt").write_text("new")
            old = Entry("old.txt", "old.txt", False, 3, id="old-id", mime_type="text/plain")
            api = FakeApi({"root": [old]})
            plan = plan_sync(api, root, "root", to_cloud=True, mode="mirror")
            self.assertEqual([(action.kind, action.path) for action in plan.actions],
                             [("upload", "new.txt"), ("trash_cloud", "old.txt")])
            execute_sync(api, root, plan, Event(), lambda *_args: None)
            self.assertEqual(api.operations, [("upload", "new.txt", "root"), ("trash", "old.txt")])

    def test_equal_content_is_not_copied_again(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            root = Path(folder)
            (root / "same.txt").write_bytes(b"same")
            md5 = hashlib.md5(b"same").hexdigest()
            entry = Entry("same.txt", "same.txt", False, 4, id="file-id", mime_type="text/plain", md5=md5)
            plan = plan_sync(FakeApi({"root": [entry]}), root, "root", to_cloud=True, mode="copy")
            self.assertEqual(plan.actions, [])

    def test_destructive_sync_stops_for_unsupported_google_document(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            doc = Entry("Notes", "Notes", False, id="doc-id",
                        mime_type="application/vnd.google-apps.document")
            with self.assertRaisesRegex(RcloneError, "skipped"):
                plan_sync(FakeApi({"root": [doc]}), Path(folder), "root", to_cloud=True, mode="mirror")

    def test_duplicate_drive_names_abort_before_changes(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            files = [Entry("same", "same", False, id="one"), Entry("same", "same", False, id="two")]
            with self.assertRaisesRegex(RcloneError, "Duplicate Drive name"):
                plan_sync(FakeApi({"root": files}), Path(folder), "root", to_cloud=True, mode="copy")

    def test_move_uses_local_recycle_bin_after_upload(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            root = Path(folder)
            (root / "photo.jpg").write_bytes(b"photo")
            api = FakeApi({"root": []})
            plan = plan_sync(api, root, "root", to_cloud=True, mode="move")
            trashed = []
            with patch("google_sync.send2trash", side_effect=trashed.append):
                execute_sync(api, root, plan, Event(), lambda *_args: None)
            self.assertEqual(api.operations, [("upload", "photo.jpg", "root")])
            self.assertEqual(trashed, [str(root / "photo.jpg")])
