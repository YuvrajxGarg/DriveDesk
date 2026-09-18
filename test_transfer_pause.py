import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
import app
from drive_backend import Entry, RcloneError


class PauseTests(unittest.TestCase):
    def test_rclone_worker_suspends_and_resumes_same_process(self):
        worker = app.TransferWorker("unused", [])
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        worker.process = proc
        try:
            worker.set_paused(True)
            self.assertTrue(worker.paused)
            worker.set_paused(False)
            self.assertFalse(worker.paused)
            self.assertIsNone(proc.poll())
            worker.set_paused(True)
            worker.cancel()
            proc.wait(timeout=5)
            self.assertTrue(worker.cancelled.is_set())
        finally:
            if proc.poll() is None:
                app.psutil.Process(proc.pid).resume()
                proc.terminate()
                proc.wait(timeout=5)

    def test_api_pause_blocks_next_chunk_and_cancel_unblocks(self):
        worker = app.ApiTransferWorker(None, "test", Entry("a", "a", False), upload=True,
                                      parent_id="id", parent_key="", local_folder=Path.cwd(), replace=False)
        worker.set_paused(True)
        finished = threading.Event()
        errors = []
        def wait():
            try:
                worker.wait_if_paused()
            except RcloneError as exc:
                errors.append(str(exc))
            finally:
                finished.set()
        thread = threading.Thread(target=wait)
        thread.start()
        self.assertFalse(finished.wait(.05))
        worker.cancel()
        self.assertTrue(finished.wait(2))
        thread.join()
        self.assertEqual(errors, ["Cancelled"])


if __name__ == "__main__":
    unittest.main()
