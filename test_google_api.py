import io
import tempfile
import unittest
from pathlib import Path
from threading import Event

from drive_backend import Entry, RcloneError
from google_api import GoogleDriveAPI


class GoogleApiTests(unittest.TestCase):
    def api(self):
        api = GoogleDriveAPI.__new__(GoogleDriveAPI)
        api.remote = "test"
        api.token = "test-token"
        return api

    def test_shared_pages_and_owner_groups(self):
        api = self.api()
        calls = []
        pages = [
            {"files": [{"id": "folder-1", "name": "Projects", "mimeType": "application/vnd.google-apps.folder",
                        "sharingUser": {"displayName": "Alex"}}], "nextPageToken": "next"},
            {"files": [{"id": "file-1", "name": "Notes.pdf", "mimeType": "application/pdf", "size": "42",
                        "owners": [{"emailAddress": "sam@example.com"}]}]},
        ]
        api._json = lambda url, **kwargs: pages.pop(0)
        entries = api.list_files(on_page=lambda batch, token: calls.append((len(batch), token)))
        self.assertEqual(calls, [(1, "next"), (1, "")])
        self.assertEqual({entry.owner for entry in entries}, {"Alex", "sam@example.com"})
        self.assertEqual(entries[0].id, "folder-1")

    def test_rate_limit_keeps_loaded_shared_page(self):
        api = self.api()
        first = {"files": [{"id": "file-1", "name": "Shared.txt", "mimeType": "text/plain"}],
                 "nextPageToken": "next"}
        calls = 0
        def fetch(_url, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return first
            raise RcloneError("Google Drive API request quota reached")
        api._json = fetch
        pages = []
        entries = api.list_files(on_page=lambda batch, token: pages.append((len(batch), token)))
        self.assertEqual(len(entries), 1)
        self.assertEqual(pages, [(1, "next")])

    def test_verified_mapping_fingerprint_changes_with_credentials(self):
        config = {"one": {"token": '{"refresh_token":"a"}'},
                  "two": {"token": '{"refresh_token":"b"}'}}
        first = GoogleDriveAPI._mapping_fingerprint(config, "one", "two")
        config["one"]["token"] = '{"refresh_token":"c"}'
        self.assertNotEqual(first, GoogleDriveAPI._mapping_fingerprint(config, "one", "two"))

    def test_folder_name_reads_metadata(self):
        api = self.api()
        api._json = lambda url, **kwargs: {"name": "UAE Eid Videos"}
        self.assertEqual(api.folder_name("folder-1", "key-1"), "UAE Eid Videos")

    def test_download_writes_file_and_reports_progress(self):
        api = self.api()
        class Response(io.BytesIO):
            headers = {"Content-Length": "5"}
        api._open = lambda *_args, **_kwargs: Response(b"hello")
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            target = Path(folder) / "file.txt"
            progress = []
            api.download(Entry("file.txt", "file.txt", False, 5, id="id-1"), target,
                         replace=False, cancelled=Event(), progress=lambda done, total, _start: progress.append((done, total)))
            self.assertEqual(target.read_bytes(), b"hello")
            self.assertEqual(progress, [(5, 5)])

    def test_upload_uses_resumable_session(self):
        api = self.api()
        api.list_files = lambda **_kwargs: []
        calls = []
        class Response:
            def __init__(self, status=200, location=""):
                self.status = status
                self.headers = {"Location": location}
            def __enter__(self): return self
            def __exit__(self, *_args): pass
        def fake_open(url, **kwargs):
            calls.append((url, kwargs))
            return Response(200, "https://upload.example/session")
        api._open = fake_open
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            source = Path(folder) / "file.txt"
            source.write_bytes(b"hello")
            progress = []
            api.upload(source, "parent-1", replace=False, cancelled=Event(),
                       progress=lambda done, total, _start: progress.append((done, total)))
        self.assertEqual(calls[0][1]["method"], "POST")
        self.assertEqual(calls[1][1]["method"], "PUT")
        self.assertEqual(calls[1][1]["headers"]["Content-Range"], "bytes 0-4/5")
        self.assertEqual(progress, [(5, 5)])

    def test_upload_timeout_queries_offset_before_resending(self):
        api = self.api()
        api.list_files = lambda **kwargs: []
        calls = []
        class Response:
            def __init__(self, status, headers):
                self.status, self.headers = status, headers
            def __enter__(self): return self
            def __exit__(self, *args): pass
        replies = [Response(200, {"Location": "https://upload.example/session"}),
                   TimeoutError("read timed out"), Response(308, {"Range": "bytes=0-1"}),
                   Response(200, {})]
        def opened(url, **kwargs):
            calls.append(kwargs)
            reply = replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply
        api._open = opened
        class Cancellation:
            def is_set(self): return False
            def wait(self, seconds): return False
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "clip.mov"
            source.write_bytes(b"hello")
            api.upload(source, "parent", replace=False, cancelled=Cancellation(), progress=lambda *args: None)
        self.assertEqual(calls[2]["data"], b"")
        self.assertEqual(calls[2]["headers"]["Content-Range"], "bytes */5")
        self.assertEqual(calls[3]["headers"]["Content-Range"], "bytes 2-4/5")
        self.assertEqual(calls[3]["data"], b"llo")

    def test_upload_lost_final_response_does_not_duplicate_file(self):
        api = self.api()
        api.list_files = lambda **kwargs: []
        calls = []
        class Response:
            status = 200
            headers = {"Location": "https://upload.example/session"}
            def __enter__(self): return self
            def __exit__(self, *args): pass
        def opened(url, **kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                raise TimeoutError("lost response")
            return Response()
        api._open = opened
        class Cancellation:
            def is_set(self): return False
            def wait(self, seconds): return False
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "clip.mov"
            source.write_bytes(b"hello")
            api.upload(source, "parent", replace=False, cancelled=Cancellation(), progress=lambda *args: None)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[2]["data"], b"")


if __name__ == "__main__":
    unittest.main()
