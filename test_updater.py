import unittest
from unittest.mock import patch

import updater


class UpdaterTests(unittest.TestCase):
    def test_version_comparison_accepts_v_prefix(self):
        self.assertTrue(updater.is_newer("v1.2.0", "1.1.9"))
        self.assertFalse(updater.is_newer("v1.1.9", "1.2.0"))

    def test_check_returns_only_new_release(self):
        with patch.object(updater, "fetch_latest_release", return_value={"tag": "v2.0.0"}):
            self.assertEqual(updater.check_for_update("owner/repo", "1.0.0")["tag"], "v2.0.0")
        with patch.object(updater, "fetch_latest_release", return_value={"tag": "v1.0.0"}):
            self.assertIsNone(updater.check_for_update("owner/repo", "1.0.0"))

    def test_picks_platform_asset(self):
        assets = [
            {"name": "DriveDesk-Setup-1.0.1.exe", "browser_download_url": "windows"},
            {"name": "DriveDesk-Setup-1.0.1-macos-arm64.dmg", "browser_download_url": "arm"},
            {"name": "DriveDesk-Setup-1.0.1-macos-x64.dmg", "browser_download_url": "intel"},
        ]
        self.assertEqual(updater._pick_asset(assets, "win32"), "windows")
        with patch.object(updater.platform_info, "machine", return_value="arm64"):
            self.assertEqual(updater._pick_asset(assets, "darwin"), "arm")
        with patch.object(updater.platform_info, "machine", return_value="x86_64"):
            self.assertEqual(updater._pick_asset(assets, "darwin"), "intel")


if __name__ == "__main__":
    unittest.main()
