import json
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from drive_backend import (Entry, Rclone, mount_args, parse_drive_folder_url, parse_transfer_stats,
                           sync_args, transfer_args, transfer_event)


class RcloneAdapterTests(unittest.TestCase):
    def test_transfer_stats_include_speed_and_eta(self):
        stats = parse_transfer_stats(
            "Transferred: 1.234 GiB / 2.345 GiB, 52%, 10.123 MiB/s, ETA 1m23s"
        )
        self.assertEqual(stats, {
            "done": "1.234 GiB", "total": "2.345 GiB", "percent": 52,
            "speed": "10.123 MiB/s", "eta": "1m23s",
        })
        self.assertIsNone(parse_transfer_stats("Checks: 3 / 3, 100%"))

    def test_json_stats_event_reports_overall_and_per_file(self):
        event = transfer_event({"level": "info", "stats": {
            "bytes": 100, "totalBytes": 200, "speed": 50.0, "eta": 4,
            "transfers": 1, "totalTransfers": 3,
            "transferring": [{"name": "Card/clip.mp4", "size": 80, "bytes": 40,
                              "percentage": 50, "speedAvg": 20.0, "eta": 2}]}})
        self.assertEqual(event["kind"], "stats")
        self.assertEqual(event["overall"]["percent"], 50)
        self.assertEqual(event["overall"]["files_done"], 1)
        self.assertEqual(event["overall"]["files_total"], 3)
        self.assertEqual(event["transferring"][0]["name"], "Card/clip.mp4")
        self.assertEqual(event["transferring"][0]["percent"], 50)
        self.assertEqual(event["transferring"][0]["done"], 40)

    def test_json_file_completion_and_noise(self):
        self.assertEqual(transfer_event({"level": "info", "msg": "Copied (new)", "object": "Card/clip.mp4"}),
                         {"kind": "file_done", "name": "Card/clip.mp4"})
        self.assertIsNone(transfer_event({"level": "info", "msg": "Checking files"}))
        self.assertIsNone(transfer_event({"level": "debug", "msg": "irrelevant"}))

    def test_transfer_args_stream_structured_progress(self):
        args = transfer_args(Entry("Photos", "C:/Photos", True), "drive", "Backup", Path("C:/Downloads"),
                             upload=True, shared=False, replace=True)
        self.assertIn("--use-json-log", args)
        self.assertIn("--verbose", args)
        self.assertIn("--stats", args)

    def test_sync_args_cover_modes_and_dry_run(self):
        mirror = sync_args("C:/x", "drive:y", "mirror")
        self.assertEqual(mirror[:3], ["sync", "C:/x", "drive:y"])
        self.assertIn("--use-json-log", mirror)
        self.assertNotIn("--dry-run", mirror)
        self.assertIn("--dry-run", sync_args("a", "b", "copy", dry_run=True))
        bisync = sync_args("a", "b", "bisync")
        self.assertEqual(bisync[0], "bisync")
        self.assertIn("--resync", bisync)
        self.assertIn("--bwlimit", sync_args("a", "b", "copy", extra=["--bwlimit", "1M"]))
        with self.assertRaises(Exception):
            sync_args("a", "b", "nope")

    def test_mount_args_build_target_and_validate_drive(self):
        self.assertEqual(mount_args("gdrive", "Photos", "X:")[:3], ["mount", "gdrive:Photos", "X:"])
        self.assertEqual(mount_args("gdrive", "", "Z:")[1], "gdrive:")
        with self.assertRaises(Exception):
            mount_args("gdrive", "p", "XY")

    def test_search_files_filters_and_keeps_full_path(self):
        rclone = Rclone("rclone")
        rclone.run = lambda *args, **_kwargs: json.dumps([
            {"Name": "Clip.mp4", "Path": "Card/Clip.mp4", "IsDir": False, "Size": 100},
            {"Name": "notes.txt", "Path": "notes.txt", "IsDir": False, "Size": 5},
            {"Name": "Card", "Path": "Card", "IsDir": True}])
        results = rclone.search_files("drive", "Trip", "clip")
        self.assertEqual([entry.name for entry in results], ["Clip.mp4"])
        self.assertEqual(results[0].path, "Trip/Card/Clip.mp4")

    def test_new_account_uses_browser_oauth_without_cli_wizard(self):
        class FinishedProcess:
            returncode = 0
            def communicate(self, timeout=None):
                return "", ""
        with patch("drive_backend.subprocess.Popen", return_value=FinishedProcess()) as start:
            Rclone("rclone.exe").create_drive("gdrive_1234", Event())
        args = start.call_args.args[0]
        self.assertEqual(args[:5], ["rclone.exe", "config", "create", "gdrive_1234", "drive"])
        self.assertIn("config_is_local", args)
        self.assertIn("true", args)
        self.assertNotIn("--non-interactive", args)

    def test_reconnect_reruns_oauth_without_deleting_remote(self):
        class FinishedProcess:
            returncode = 0
            def communicate(self, timeout=None):
                return "", ""
            def poll(self):
                return 0
        rclone = Rclone("rclone.exe")
        run_calls = []
        rclone.run = lambda *args, **_kwargs: run_calls.append(args)
        with patch("drive_backend.subprocess.Popen", return_value=FinishedProcess()) as start:
            rclone.reconnect_drive("gdrive_1234", Event())
        args = start.call_args.args[0]
        self.assertEqual(args[:4], ["rclone.exe", "config", "reconnect", "gdrive_1234:"])
        self.assertEqual(run_calls, [])  # reconnect must never delete the existing remote

    def test_create_remote_key_backend_obscures_and_lists_all_remotes(self):
        rclone = Rclone("rclone")
        calls = []
        rclone.run = lambda *args, **_kwargs: calls.append(args) or "{}"
        rclone.create_remote("b2_1234", "b2", {"account": "keyid", "key": "secret"}, Event())
        self.assertEqual(calls[0][:5], ("config", "create", "b2_1234", "b2", "account"))
        self.assertIn("--obscure", calls[0])
        with self.assertRaises(Exception):
            rclone.create_remote("s3_1", "not-a-backend", {}, Event())

    def test_remotes_lists_every_backend_drive_first(self):
        rclone = Rclone("rclone")
        rclone.run = lambda *args, **_kwargs: json.dumps({
            "box1": {"type": "box"}, "gdrive": {"type": "drive"}, "s3x": {"type": "s3"}})
        self.assertEqual(rclone.remotes(), [("gdrive", "drive"), ("box1", "box"), ("s3x", "s3")])

    def test_delete_remote_calls_config_delete_and_validates_name(self):
        rclone = Rclone("rclone")
        calls = []
        rclone.run = lambda *args, **_kwargs: calls.append(args)
        rclone.delete_remote("gdrive_1234")
        self.assertEqual(calls[0][:3], ("config", "delete", "gdrive_1234"))
        with self.assertRaises(Exception):
            rclone.delete_remote("bad name!")

    def test_shared_listing_keeps_owner_and_folder_path(self):
        rclone = Rclone("rclone")
        calls = []
        def fake_run(*args, **_kwargs):
            calls.append(args)
            return json.dumps([
                {"Name": "Report.pdf", "IsDir": False, "Size": 123, "Metadata": {"owner": "alex@example.com"}},
                {"Name": "Projects", "IsDir": True, "ID": "folder-123", "Metadata": {"owner": "alex@example.com"}},
            ])
        rclone.run = fake_run
        rows = rclone.list("drive", "Folder", shared=True, metadata=True)
        self.assertEqual([row.name for row in rows], ["Projects", "Report.pdf"])
        self.assertEqual(rows[0].path, "Folder/Projects")
        self.assertEqual(rows[0].id, "folder-123")
        self.assertEqual(rows[1].owner, "alex@example.com")
        self.assertIn("--drive-shared-with-me", calls[0])
        self.assertIn("--metadata", calls[0])

    def test_remote_size_and_folder_operations_keep_link_context(self):
        rclone = Rclone("rclone")
        calls = []
        rclone.run = lambda *args, **_kwargs: calls.append(args) or '{"bytes": 4096, "count": 2}'
        self.assertEqual(rclone.size("drive", "Projects", shared=True), (4096, 2))
        self.assertIn("--drive-shared-with-me", calls[0])
        rclone.mutate("mkdir", "drive", "New", folder_id="folder-123")
        self.assertEqual(calls[1][:3], ("mkdir", "drive:New", "--drive-root-folder-id"))

    def test_transfer_commands_are_directional_and_skip_existing(self):
        file = Entry("Report.pdf", "Folder/Report.pdf", False)
        download = transfer_args(file, "drive", "Folder", Path("C:/Downloads"),
                                 upload=False, shared=True, replace=False)
        self.assertEqual(download[:3], ["copyto", "drive:Folder/Report.pdf", str(Path("C:/Downloads") / "Report.pdf")])
        self.assertIn("--ignore-existing", download)
        self.assertIn("--drive-shared-with-me", download)
        folder = Entry("Photos", "C:/Photos", True)
        upload = transfer_args(folder, "drive", "Backup", Path("C:/Downloads"),
                               upload=True, shared=False, replace=True)
        self.assertEqual(upload[:3], ["copy", "C:/Photos", "drive:Backup/Photos"])
        self.assertNotIn("--ignore-existing", upload)

    def test_folder_link_keeps_resource_key_for_browse_and_download(self):
        folder_id, key = parse_drive_folder_url(
            "https://drive.google.com/drive/folders/1AbCdEfGhIjK?resourcekey=0-abc_DEF&usp=sharing"
        )
        self.assertEqual((folder_id, key), ("1AbCdEfGhIjK", "0-abc_DEF"))
        rclone = Rclone("rclone")
        calls = []
        rclone.run = lambda *args, **_kwargs: calls.append(args) or "[]"
        rclone.list("drive", folder_id=folder_id, resource_key=key)
        self.assertEqual(calls[0][-4:], ("--drive-root-folder-id", folder_id, "--drive-resource-key", key))
        args = transfer_args(Entry("file.txt", "file.txt", False), "drive", "", Path("C:/Downloads"),
                             upload=False, shared=False, replace=False, folder_id=folder_id, resource_key=key)
        self.assertEqual(args[-4:], ["--drive-root-folder-id", folder_id, "--drive-resource-key", key])
        upload = transfer_args(Entry("file.txt", "C:/Upload/file.txt", False), "drive", "Subfolder", Path("C:/Downloads"),
                               upload=True, shared=False, replace=False, folder_id=folder_id, resource_key=key)
        self.assertEqual(upload[:3], ["copyto", "C:/Upload/file.txt", "drive:Subfolder/file.txt"])
        self.assertEqual(upload[-4:], ["--drive-root-folder-id", folder_id, "--drive-resource-key", key])
        with self.assertRaises(ValueError):
            parse_drive_folder_url("https://drive.google.com/file/d/1AbCdEfGhIjK/view")


if __name__ == "__main__":
    unittest.main()
