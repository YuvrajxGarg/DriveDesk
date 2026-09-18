"""Offline visual fixture. No cloud access or real transfers."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem
from PyQt6.QtGui import QFontDatabase
import app
from drive_backend import Entry

qt = QApplication([])
for font in ("segoeui.ttf", "seguisb.ttf"):
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
qt.setStyleSheet(app.STYLE)
settings = type("Settings", (), {"value": lambda s, k, d=None: d, "setValue": lambda *a: None})()
with patch.object(app, "QSettings", return_value=settings), \
     patch.object(app.MainWindow, "load_accounts"), patch.object(app.MainWindow, "load_local"):
    window = app.MainWindow()
    window.account_btn.setText("Studio Drive")
    window.remote = "preview"
    window.remote_type = "drive"
    window.update_buttons()
    window.account_btn.setText("Studio Drive")
    window.pc.location.setText("C:/Users/Studio/Projects")
    window.cloud.location.setText("My Drive / Projects")
    rows = [Entry("Brand assets", "Brand assets", True), Entry("Client deliverables", "Client deliverables", True),
            Entry("September campaign", "September campaign", True),
            Entry("Campaign film — final review.mov", "Campaign film — final review.mov", False, 1800000000, "2026-09-18"),
            Entry("Creative brief.pdf", "Creative brief.pdf", False, 3200000, "2026-09-17"),
            Entry("Reference photography.zip", "Reference photography.zip", False, 890000000, "2026-09-16")]
    window.pc.show_entries(rows)
    window.cloud.show_entries(rows[:3] + rows[4:])
    row = QTreeWidgetItem(["Upload", "Campaign film — final review.mov", "Studio Drive / Projects",
                          "Uploading", "684 MiB / 1.7 GiB", "", "10.8 MiB/s", "1m 39s", ""])
    window.transfers.addTopLevelItem(row)
    bar = window._new_bar()
    bar.setValue(40)
    window.transfers.setItemWidget(row, 5, bar)
    window.transfer_summary.setText("1 active transfer")
    window.set_status("Uploading to Studio Drive")
    window.show()
    qt.processEvents()
    window.grab().save("ui-preview.png")
    window.resize(1100, 740)
    qt.processEvents()
    window.grab().save("ui-preview-compact.png")
    window.close()
