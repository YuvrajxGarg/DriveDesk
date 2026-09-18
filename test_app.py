import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import app
from PyQt6.QtCore import QMimeData, QObject, QThreadPool, QUrl, pyqtSignal
from PyQt6.QtWidgets import QApplication
from drive_backend import Entry, RcloneError


def state_bar_value(window, item):
    return window.transfers.itemWidget(item, 5).value()


class FakeRclone:
    names = ["test-drive"]

    def __init__(self, _executable):
        pass

    def drives(self):
        return list(self.names)

    def remotes(self):
        return [(name, "drive") for name in self.names]

    def create_drive(self, name, _cancelled):
        self.names.append(name)

    def user_label(self, _name):
        return "new@example.com"

    def list(self, _remote, _path="", shared=False, metadata=False, folder_id="", resource_key=""):
        if metadata:
            raise RcloneError("Owner metadata unavailable")
        return [Entry("Shared folder", "Shared folder", True)] if shared else []


class FakeGoogleAPI:
    def __init__(self, _rclone, _remote, *, use_preferred=True, auth=None):
        pass

    def account_label(self):
        return "Alex (new@example.com)"

    def list_files(self, *, folder_id="", resource_key="", prefix="", page_token="", on_page=None):
        entries = ([Entry("Shared folder", "Shared folder", True, owner="alex@example.com", id="folder-1")]
                   if not folder_id else [Entry("Document.pdf", f"{prefix}/Document.pdf", False, 123, id="file-1")])
        if on_page:
            on_page(entries, "")
        return entries

    def list_my_drive(self, path="", *, known_folder_id=""):
        if path:
            return [Entry("Document.pdf", f"{path}/Document.pdf", False, 123, id="file-1")]
        return [Entry("Projects", "Projects", True, id="folder-1")]


class SharedViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication([])
        cls.real_google_api = app.GoogleDriveAPI
        app.GoogleDriveAPI = FakeGoogleAPI

    @classmethod
    def tearDownClass(cls):
        app.GoogleDriveAPI = cls.real_google_api

    def tearDown(self):
        QThreadPool.globalInstance().waitForDone(2000)
        self.qt.processEvents()

    def test_my_drive_uses_native_listing_and_remembers_folder_id(self):
        real_find, real_rclone = app.find_rclone, app.Rclone
        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = FakeRclone
        try:
            window = app.MainWindow()
            window.remote = "test-drive"
            window.remote_type = "drive"
            window.shared = False
            window.load_remote()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not window.cloud.entries:
                self.qt.processEvents()
                time.sleep(0.01)
            self.assertEqual(window.cloud.entries[0].name, "Projects")
            window.remote_open(0, 0)
            self.assertEqual(window.drive_folder_ids[("test-drive", "Projects")], "folder-1")
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not window.cloud.entries:
                self.qt.processEvents()
                time.sleep(0.01)
            self.assertEqual(window.cloud.entries[0].name, "Document.pdf")
            window.close()
        finally:
            app.find_rclone, app.Rclone = real_find, real_rclone

    def test_shared_items_from_api_are_browsable_by_owner(self):
        real_find, real_rclone = app.find_rclone, app.Rclone
        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = FakeRclone
        try:
            window = app.MainWindow()
            window.set_view(True)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and "alex@example.com" not in [
                entry.name for entry in window.cloud.entries]:
                self.qt.processEvents()
                time.sleep(0.01)
            self.assertEqual(window.cloud.entries[0].name, "alex@example.com")
            window.remote_open(0, 0)
            self.assertEqual(window.cloud.entries[0].name, "Shared folder")
            window.remote_open(0, 0)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not window.cloud.entries:
                self.qt.processEvents()
                time.sleep(0.01)
            self.assertEqual(window.cloud.entries[0].name, "Document.pdf")
            window.close()
        finally:
            app.find_rclone, app.Rclone = real_find, real_rclone

    def test_linked_folder_allows_upload(self):
        real_find, real_rclone = app.find_rclone, app.Rclone
        real_input = app.QInputDialog.getText
        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = FakeRclone
        app.QInputDialog.getText = lambda *_args: ("https://drive.google.com/drive/folders/1AbCdEfGhIjK", True)
        try:
            window = app.MainWindow()
            window.remote = "test-drive"
            window.open_link()
            self.assertEqual(window.link_folder_id, "1AbCdEfGhIjK")
            self.assertEqual(window.shared_folder_id, "1AbCdEfGhIjK")
            window.close()
        finally:
            app.find_rclone, app.Rclone = real_find, real_rclone
            app.QInputDialog.getText = real_input

    def test_drop_routes_files_to_target_folder(self):
        real_find, real_rclone = app.find_rclone, app.Rclone
        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = FakeRclone
        try:
            window = app.MainWindow()
            window.remote = "test-drive"
            calls = []
            window.start_transfer = lambda upload, **kwargs: calls.append((upload, kwargs))
            file = Entry("a.txt", "C:/a.txt", False)
            window.cloud_drop("pc", [file], Entry("Target", "Target", True))
            self.assertEqual(calls[0][0], True)
            self.assertEqual(calls[0][1]["remote_folder"], "Target")
            window.pc_drop("cloud", [Entry("b.txt", "b.txt", False)], Entry("Downloads", "C:/Downloads", True))
            self.assertEqual(calls[1][0], False)
            self.assertEqual(str(calls[1][1]["local_folder"]), str(app.Path("C:/Downloads")))
            window.close()
        finally:
            app.find_rclone, app.Rclone = real_find, real_rclone

    def test_folder_transfer_shows_aggregate_and_per_file_rows(self):
        real_find, real_rclone, real_worker = app.find_rclone, app.Rclone, app.TransferWorker
        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = FakeRclone

        class FakeSignals(QObject):
            progress = pyqtSignal(object)
            done = pyqtSignal(bool, str)

        class FakeWorker:
            def __init__(self, *_args, **_kwargs):
                self.signals = FakeSignals()
                self.cancelled = False

            def cancel(self):
                self.cancelled = True

        app.TransferWorker = FakeWorker
        try:
            window = app.MainWindow()
            window.remote = "test-drive"
            window.pool = type("Pool", (), {"start": lambda self, worker: None})()
            window.start_transfer(True, entries=[Entry("Photos", "C:/Photos", True)])
            self.assertEqual(window.transfers.topLevelItemCount(), 1)
            worker = next(iter(window.transfer_items))
            window.transfer_progress(worker, {"kind": "stats", "overall": {
                "done": 100, "total": 200, "percent": 50, "speed": 50.0, "eta": 4,
                "files_done": 1, "files_total": 3}, "transferring": [
                {"name": "a.jpg", "done": 40, "total": 80, "percent": 50, "speed": 20.0, "eta": 2}]})
            item = window.transfers.topLevelItem(0)
            self.assertEqual(item.childCount(), 1)
            self.assertTrue(item.text(3).startswith("Transferring"))
            self.assertEqual(item.child(0).text(1), "a.jpg")
            self.assertEqual(state_bar_value(window, item), 50)
            window.transfer_progress(worker, {"kind": "file_done", "name": "a.jpg"})
            self.assertEqual(item.child(0).text(3), "Done")
            window.transfer_done(worker, "Uploading Photos", True, "Complete")
            self.assertEqual(item.text(3), "Complete")
            self.assertEqual(state_bar_value(window, item), 100)
            self.assertNotIn(worker, window.transfer_items)
            window.close()
        finally:
            app.find_rclone, app.Rclone, app.TransferWorker = real_find, real_rclone, real_worker

    def test_non_drive_remote_disables_drive_only_actions(self):
        real_find, real_rclone = app.find_rclone, app.Rclone

        class MultiRclone(FakeRclone):
            def remotes(self):
                return [("gdrive", "drive"), ("dropbox_1", "dropbox")]

        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = MultiRclone
        try:
            window = app.MainWindow()
            window.remote_types = {"gdrive": "drive", "dropbox_1": "dropbox"}
            window.remote = "dropbox_1"
            window.remote_type = "dropbox"
            window.update_buttons()
            self.assertFalse(window.view_shared.isEnabled())
            self.assertFalse(window.open_shared_link.isEnabled())
            window.remote = "gdrive"
            window.remote_type = "drive"
            window.update_buttons()
            self.assertTrue(window.view_shared.isEnabled())
            self.assertTrue(window.open_shared_link.isEnabled())
            window.close()
        finally:
            app.find_rclone, app.Rclone = real_find, real_rclone

    def test_transfer_options_become_rclone_flags(self):
        real_find, real_rclone = app.find_rclone, app.Rclone
        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = FakeRclone
        try:
            window = app.MainWindow()
            window.transfer_opts = {"bwlimit": "10M", "transfers": "4", "checkers": "",
                                    "excludes": "*.tmp, .DS_Store", "includes": ""}
            flags = window._extra_transfer_flags()
            self.assertEqual(flags[flags.index("--bwlimit") + 1], "10M")
            self.assertEqual(flags[flags.index("--transfers") + 1], "4")
            self.assertNotIn("--checkers", flags)
            self.assertEqual(flags.count("--exclude"), 2)
            window.close()
        finally:
            app.find_rclone, app.Rclone = real_find, real_rclone

    def test_conflict_detection_for_upload_and_download(self):
        real_find, real_rclone = app.find_rclone, app.Rclone
        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = FakeRclone
        try:
            window = app.MainWindow()
            window.remote = "test-drive"
            window.remote_path = ""
            window.cloud.entries = [Entry("Mimi", "Mimi", True), Entry("keep.txt", "keep.txt", False)]
            up = window._find_conflicts([Entry("Mimi", "C:/Mimi", True), Entry("new", "C:/new", True)],
                                        True, "", app.Path("C:/x"))
            self.assertEqual(up, ["Mimi"])
            import tempfile, os as _os
            with tempfile.TemporaryDirectory() as folder:
                open(_os.path.join(folder, "here.txt"), "w").close()
                down = window._find_conflicts([Entry("here.txt", "here.txt", False),
                                               Entry("gone.txt", "gone.txt", False)],
                                              False, "", app.Path(folder))
            self.assertEqual(down, ["here.txt"])
            window.close()
        finally:
            app.find_rclone, app.Rclone = real_find, real_rclone

    def test_clear_finished_keeps_active_rows(self):
        real_find, real_rclone, real_worker = app.find_rclone, app.Rclone, app.TransferWorker

        class FakeSignals(QObject):
            progress = pyqtSignal(object)
            done = pyqtSignal(bool, str)

        class FakeWorker:
            def __init__(self, *_args, **_kwargs):
                self.signals = FakeSignals()

            def cancel(self):
                pass

        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = FakeRclone
        app.TransferWorker = FakeWorker
        try:
            window = app.MainWindow()
            window.remote = "test-drive"
            window.pool = type("Pool", (), {"start": lambda self, worker: None})()
            window.start_transfer(True, entries=[Entry("A.txt", "C:/A.txt", False),
                                                 Entry("B.txt", "C:/B.txt", False)])
            self.assertEqual(window.transfers.topLevelItemCount(), 2)
            workers = list(window.transfer_items)
            window.transfer_done(workers[0], "Uploading A.txt", True, "Complete")
            window.clear_finished_transfers()
            self.assertEqual(window.transfers.topLevelItemCount(), 1)
            with patch.object(app.QMessageBox, "question", return_value=app.QMessageBox.StandardButton.Yes):
                window.close()
        finally:
            app.find_rclone, app.Rclone, app.TransferWorker = real_find, real_rclone, real_worker

    def test_shared_sidebar_groups_people_and_folders(self):
        real_find, real_rclone = app.find_rclone, app.Rclone
        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = FakeRclone
        try:
            window = app.MainWindow()
            window.populate_shared_tree([
                Entry("Album", "Album", True, owner="alex@example.com"),
                Entry("Report.pdf", "Report.pdf", False, owner="alex@example.com"),
                Entry("Photos", "Photos", True, owner="sam@example.com"),
            ])
            tree = window.cloud.tree
            self.assertEqual(tree.topLevelItemCount(), 3)  # My Drive, Shared with me, Opened links
            self.assertEqual(window.shared_tree_root.childCount(), 2)
            person = window.shared_tree_root.child(0)
            self.assertEqual(person.text(0), "alex@example.com")
            self.assertEqual(person.child(0).text(0), "Album")
            window.close()
        finally:
            app.find_rclone, app.Rclone = real_find, real_rclone

    def test_cloud_accepts_explorer_files_and_cross_pane_drags(self):
        cloud = app.FileTable("cloud")
        pc = app.FileTable("pc")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile("C:/example.txt")])
        event = type("Event", (), {"mimeData": lambda self: mime})()
        self.assertTrue(cloud._accepts(event))
        self.assertFalse(pc._accepts(event))
        app.FileTable.active_source = pc
        try:
            self.assertTrue(cloud._accepts(event))
            self.assertFalse(pc._accepts(event))
        finally:
            app.FileTable.active_source = None

    def test_add_account_completes_in_app(self):
        real_find, real_rclone, real_settings = app.find_rclone, app.Rclone, app.QSettings
        class FakeSettings:
            values = {}
            def __init__(self, *_args):
                pass
            def value(self, key, default=None):
                return self.values.get(key, default)
            def setValue(self, key, value):
                self.values[key] = value
            def remove(self, key):
                self.values.pop(key, None)
        app.find_rclone = lambda _saved="": "fake-rclone"
        app.Rclone = FakeRclone
        app.QSettings = FakeSettings
        FakeRclone.names = ["test-drive"]
        try:
            window = app.MainWindow()
            connected = []
            window.native_auth.connect = lambda _cancelled: connected.append({
                "id": "native:test", "name": "Alex", "email": "new@example.com", "client_id": "test-client"}) or "native:test"
            window.native_auth.accounts = lambda: list(connected)
            window.add_google_account()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not connected:
                self.qt.processEvents()
                time.sleep(0.01)
            def has_label():
                return any("new@example.com" in window.accounts.item(i).text()
                           for i in range(window.accounts.count()))
            while time.monotonic() < deadline and (window.accounts.count() < 2 or not has_label()):
                self.qt.processEvents()
                time.sleep(0.01)
            self.assertEqual(window.accounts.count(), 2)
            self.assertTrue(has_label())
            window.settings.remove("account_label/native:test")
            window.close()
        finally:
            app.find_rclone, app.Rclone, app.QSettings = real_find, real_rclone, real_settings
            FakeRclone.names = ["test-drive"]


if __name__ == "__main__":
    unittest.main()
