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


if __name__ == "__main__":
    unittest.main()
