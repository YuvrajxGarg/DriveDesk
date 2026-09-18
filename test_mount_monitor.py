import io
import json
import unittest
from unittest.mock import patch
from mount_monitor import snapshot


class MountMonitorTests(unittest.TestCase):
    def read(self, cache, stats=None, queue=None):
        payloads = [stats or {}, {"diskCache": cache}, {"queue": queue or []}]
        class Opener:
            def open(self, request, timeout):
                self_test.assertEqual(request.get_method(), "POST")
                self_test.assertTrue(request.get_header("Authorization").startswith("Basic "))
                self_test.assertNotIn("short", request.full_url)
                return io.BytesIO(json.dumps(payloads.pop(0)).encode())
        self_test = self
        with patch("mount_monitor.urllib.request.build_opener", return_value=Opener()):
            return snapshot(1234, "test-password")

    def cache(self, **changes):
        return dict(uploadsQueued=0, uploadsInProgress=0, erroredFiles=0,
                    outOfSpace=False, **changes)

    def test_pending_queue_does_not_report_idle(self):
        result = self.read(self.cache(), queue=[{"name": "waiting.mov"}])
        self.assertIn("queued", result["state"])
        self.assertIn("waiting.mov", result["names"])

    def test_cache_error_does_not_report_complete(self):
        cache = self.cache()
        cache["erroredFiles"] = 1
        self.assertIn("Needs attention", self.read(cache)["state"])

    def test_missing_cache_is_unknown(self):
        with self.assertRaises(ValueError):
            self.read({})

    def test_current_speed_not_lifetime_average(self):
        result = self.read(self.cache(), {"speed": 999, "transferring": [
            {"name": "clip.mov", "speedAvg": 50}]})
        self.assertEqual(result["speed"], 50)
        self.assertEqual(result["state"], "Transferring")


if __name__ == "__main__":
    unittest.main()
