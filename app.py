from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from threading import Event

from PyQt6.QtCore import QMimeData, QObject, QRunnable, QSettings, QSize, Qt, QThreadPool, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QDrag, QIcon
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QInputDialog, QProgressDialog, QStyle,
    QWidget, QAbstractItemView, QHeaderView, QProgressBar, QTreeWidget, QTreeWidgetItem,
)

import icons
from drive_backend import BACKENDS, OAUTH_BACKENDS, SYNC_COMMANDS, Entry, Rclone, RcloneError, find_rclone, local_entries, mount_args, network_env, parse_drive_folder_url, sync_args, transfer_args, transfer_event
from google_api import GoogleDriveAPI
from updater import APP_VERSION, GITHUB_REPO, check_for_update, download_update


STYLE = """
* { font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QWidget { background: #1c1d20; color: #dfe1e5; }
QToolTip { background: #2a2c30; color: #e6e8ec; border: 1px solid #3a3c42; }
QLabel#brand { font-size: 16px; font-weight: 700; color: #f2f3f5; }
QFrame#brandmark { background: transparent; }
QLabel#muted { color: #7f828b; }
QLabel#statusdot { color: #55C98A; font-size: 11px; }
QLabel#statvalue { color: #D9DDE5; font-weight: 600; }
QLabel#downstat { color: #8BB7FF; font-weight: 600; }
QLabel#upstat { color: #C5A4FF; font-weight: 600; }
QLabel#heading { font-size: 13px; font-weight: 650; color: #e7e9ec; }
QLabel#panetab { font-size: 13px; font-weight: 650; color: #eef0f3; }

QFrame#topbar { background: #202124; border-bottom: 1px solid #34363c; }
QFrame#statusbar { background: transparent; border-top: 1px solid #303238; }
QFrame#toolsep { background: #34363c; max-width: 1px; }

QFrame#panel { background: #25262a; border: 1px solid #34363c; border-radius: 9px; }
QFrame#panel QLabel { background: transparent; }
QFrame#panehead { background: #2a2c30; border: 1px solid #34363c; border-top-left-radius: 8px; border-top-right-radius: 8px; }

QFrame#sidebar { background: #171819; border-right: 1px solid #2b2d31; }
QFrame#sidebar QLabel { color: #d3d6dc; background: transparent; }
QFrame#sidebar QLabel#muted { color: #6b6e77; letter-spacing: 1px; }

QPushButton { background: #2a2c31; border: 1px solid #3a3c42; border-radius: 6px; padding: 6px 12px; color: #d7dae0; }
QPushButton:hover { background: #33363c; border-color: #4a4d55; }
QPushButton:disabled { color: #61646c; background: #232428; border-color: #2f3136; }
QPushButton#primary { background: #2f6df0; border-color: #2f6df0; color: white; font-weight: 600; }
QPushButton#primary:hover { background: #3f79f3; }
QPushButton#primary:disabled { background: #26426f; border-color: #26426f; color: #9fb4d8; }
QPushButton#toolbtn { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 7px 12px; color: #c7cad1; }
QPushButton#toolbtn:hover { background: #2e3037; }
QPushButton#toolbtn:checked { background: #24365a; color: #ffffff; border-color: #345085; }
QPushButton#paneicon { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 5px 9px; color: #c7cad1; }
QPushButton#paneicon:hover { background: #34363d; }
QFrame#addressbar { background: #202226; border: 1px solid #34363c; border-radius: 8px; }
QFrame#addressbar QLineEdit#addressline { background: transparent; border: 0; padding: 6px 6px; }
QPushButton#navbtn { background: #2b2d32; border: 1px solid #3a3c42; border-radius: 7px; }
QPushButton#navbtn:hover { background: #363940; border-color: #4c505a; }
QPushButton#navbtn:pressed { background: #2f323a; }
QPushButton#navbtn:disabled { background: #232428; border-color: #2f3136; }
QFrame#sidebar QPushButton { background: #23252a; color: #d7dae0; border-color: #33353b; }
QFrame#sidebar QPushButton:hover { background: #2c2f35; }
QFrame#sidebar QPushButton#primary { background: #2f6df0; border-color: #2f6df0; color: #fff; }

QLineEdit { background: #1f2125; border: 1px solid #34363c; border-radius: 6px; padding: 7px 9px; color: #dfe1e5; selection-background-color: #2f6df0; }
QLineEdit:focus { border: 1px solid #4a86e8; }
QLineEdit[readOnly="true"] { background: #1a1b1e; color: #b6bac2; }

QListWidget, QTableWidget, QTreeWidget { background: transparent; border: 0; outline: 0; gridline-color: #2a2b2f; }
QListWidget::item { padding: 8px 10px; border-radius: 6px; margin: 2px 3px; color: #cbced4; }
QFrame#sidebar QListWidget::item { color: #c9cdd4; }
QListWidget::item:selected { background: #24365a; color: #ffffff; }
QFrame#sidebar QListWidget::item:selected { background: #283b60; color: #ffffff; }
QTableWidget { alternate-background-color: #222327; }
QTableWidget[dragOver="true"] { border: 2px dashed #4a86e8; border-radius: 8px; background: #22304a; }
QTableWidget::item { padding: 3px 6px; border-bottom: 1px solid #282a2e; color: #d5d8de; }
QTableWidget::item:selected { background: #2b3f63; color: #ffffff; }
QTreeWidget { color: #d5d8de; }
QTreeWidget::item { color: #d5d8de; }
QTreeWidget::item:selected { background: #2b3f63; color: #ffffff; }
QTreeWidget::branch { background: transparent; }
QTreeWidget#transfers::item { padding: 4px 4px; border-bottom: 1px solid #26272b; }
QHeaderView::section { background: #202124; color: #7f828b; border: 0; border-bottom: 1px solid #303136; padding: 8px 8px; font-weight: 600; }
QScrollBar:vertical { background: transparent; width: 11px; margin: 0; }
QScrollBar::handle:vertical { background: #3b3d44; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #4a4d55; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 0; }
QScrollBar::handle:horizontal { background: #3b3d44; border-radius: 5px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QCheckBox { color: #aeb2ba; spacing: 7px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #4a4d55; border-radius: 4px; background: #26282c; }
QCheckBox::indicator:checked { background: #2f6df0; border-color: #2f6df0; }
QMenu { background: #26272b; color: #dcdee3; border: 1px solid #3a3c42; padding: 4px; }
QMenu::item { padding: 6px 22px 6px 14px; border-radius: 5px; }
QMenu::item:selected { background: #2b3f63; }
QMenu::separator { height: 1px; background: #34363c; margin: 4px 6px; }
QSplitter::handle { background: #26272b; }
QSplitter::handle:hover { background: #34363c; }
QProgressBar { background: #303136; border: 0; border-radius: 5px; min-height: 15px; max-height: 18px; text-align: center; color: #e4e6ea; font-size: 11px; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a86e8, stop:1 #2f6df0); border-radius: 5px; }
QProgressBar[state="done"]::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #37b06a, stop:1 #2f9e5f); }
QProgressBar[state="failed"]::chunk { background: #d75b60; }
QProgressBar#total { min-height: 11px; max-height: 13px; }
QProgressBar#total::chunk { background: #37b06a; border-radius: 5px; }
QPushButton#linkbtn { background: transparent; border: 0; color: #8b8f97; padding: 4px 8px; }
QPushButton#linkbtn:hover { color: #4a86e8; }
QPushButton#tinycancel { background: #3a2626; border: 1px solid #5a3737; color: #e79a9d; border-radius: 6px; padding: 3px 12px; }
QPushButton#tinycancel:hover { background: #472d2d; }
QPushButton#accounttab { background: #2f3238; border: 1px solid #3d4046; border-radius: 7px; padding: 6px 12px; color: #eef0f3; font-weight: 650; }
QPushButton#accounttab:hover { background: #383b42; border-color: #4c5058; }
QPushButton#accounttab::menu-indicator { image: none; width: 0; }
QLineEdit#search { background: #26282c; border: 1px solid #3a3c42; border-radius: 15px; padding: 6px 12px; }
QLineEdit#search:focus { border-color: #4a86e8; background: #202226; }
QComboBox { background: #26282c; border: 1px solid #3a3c42; border-radius: 6px; padding: 6px 10px; color: #dfe1e5; }
QComboBox:hover { border-color: #4a4d55; }
QComboBox:focus { border-color: #4a86e8; }
QComboBox::drop-down { border: 0; width: 22px; }
QComboBox::down-arrow { image: none; width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #9aa0aa; margin-right: 9px; }
QComboBox QAbstractItemView { background: #26272b; border: 1px solid #3a3c42; outline: 0; color: #dcdee3; selection-background-color: #2b3f63; selection-color: #ffffff; padding: 3px; }
QDialog { background: #1f2023; }
QDialog QLabel { color: #dfe1e5; background: transparent; }
QDialog QListWidget { background: #1a1b1e; border: 1px solid #34363c; border-radius: 7px; }
QDialog QListWidget::item { padding: 8px 10px; border-radius: 5px; margin: 1px 3px; color: #d5d8de; }
QDialog QListWidget::item:selected { background: #2b3f63; color: #ffffff; }
QMessageBox, QInputDialog, QProgressDialog { background: #1f2023; }
QMessageBox QLabel, QInputDialog QLabel, QProgressDialog QLabel { color: #dfe1e5; background: transparent; }
QProgressDialog QProgressBar { min-height: 8px; max-height: 10px; }
"""

ALL_SHARED = "@all-shared"


def size_text(size: int) -> str:
    if size < 0:
        return "—"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return "—"


def speed_text(bytes_per_second: float) -> str:
    if bytes_per_second <= 0:
        return "—"
    return f"{size_text(int(bytes_per_second))}/s"


def eta_text(seconds) -> str:
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return "—"
    if total < 0:
        return "—"
    if total >= 3600:
        return f"{total // 3600}h {total % 3600 // 60}m"
    if total >= 60:
        return f"{total // 60}m {total % 60:02d}s"
    return f"{total}s"


class WorkerSignals(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(object)


class Worker(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.setAutoDelete(False)
        self.fn = fn
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.result.emit(self.fn())
        except Exception as exc:
            self.signals.error.emit(str(exc))


class TransferSignals(QObject):
    progress = pyqtSignal(object)
    done = pyqtSignal(bool, str)


class TransferWorker(QRunnable):
    def __init__(self, executable: str, args: list[str]):
        super().__init__()
        self.setAutoDelete(False)
        self.executable, self.args = executable, args
        self.signals = TransferSignals()
        self.cancelled = Event()
        self.process = None

    def cancel(self):
        self.cancelled.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def run(self):
        try:
            proc = subprocess.Popen(
                [self.executable, *self.args], stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                env=network_env(),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self.process = proc
            if self.cancelled.is_set():
                proc.terminate()
            last_error = ""
            assert proc.stderr is not None
            # With --use-json-log rclone emits one JSON object per line: periodic
            # stats blocks and per-object completion messages.
            for raw in proc.stderr:
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if obj.get("level") in ("error", "critical", "fatal"):
                    last_error = obj.get("msg", last_error)
                event = transfer_event(obj)
                if event:
                    self.signals.progress.emit(event)
            code = proc.wait()
            self.signals.done.emit(code == 0 and not self.cancelled.is_set(),
                                   "Cancelled" if self.cancelled.is_set() else
                                   ("Complete" if code == 0 else (last_error or f"rclone exited with {code}")))
        except OSError as exc:
            self.signals.done.emit(False, str(exc))


class ApiTransferWorker(QRunnable):
    def __init__(self, rclone: Rclone, remote: str, entry: Entry, *, upload: bool,
                 parent_id: str, parent_key: str, local_folder: Path, replace: bool):
        super().__init__()
        self.setAutoDelete(False)
        self.rclone, self.remote, self.entry = rclone, remote, entry
        self.upload, self.parent_id, self.parent_key = upload, parent_id, parent_key
        self.local_folder, self.replace = local_folder, replace
        self.cancelled = Event()
        self.signals = TransferSignals()

    def cancel(self):
        self.cancelled.set()

    def _estimate_total(self, api: GoogleDriveAPI) -> int:
        """Best-effort byte total for the whole transfer so the bar and ETA mean something."""
        try:
            if self.upload:
                path = Path(self.entry.path)
                if path.is_file():
                    return path.stat().st_size
                total = 0
                for folder, _dirs, files in os.walk(path):
                    for name in files:
                        try:
                            total += (Path(folder) / name).stat().st_size
                        except OSError:
                            continue
                return total
            if not self.entry.is_dir:
                return max(0, self.entry.size)
            return api.calculate_size(self.entry)[0]
        except Exception:
            return 0

    def run(self):
        try:
            api = GoogleDriveAPI(self.rclone, self.remote)
            grand_total = self._estimate_total(api)
            started_at = time.monotonic()
            state = {"completed": 0, "files_done": 0, "current": None, "last_total": 0}
            def progress(done, total, started):
                # The API reports bytes for one file at a time; stitch them into a
                # single whole-folder figure by watching the per-file start marker.
                if state["current"] is None:
                    state["current"] = started
                elif started != state["current"]:
                    state["completed"] += state["last_total"]
                    state["files_done"] += 1
                    state["current"] = started
                state["last_total"] = total
                cumulative = state["completed"] + done
                elapsed = max(0.1, time.monotonic() - started_at)
                speed = cumulative / elapsed
                percent = int(cumulative * 100 / grand_total) if grand_total > 0 else 0
                remaining = grand_total - cumulative
                eta = int(remaining / speed) if speed > 0 and grand_total and remaining > 0 else None
                self.signals.progress.emit({
                    "kind": "stats",
                    "overall": {"done": cumulative, "total": grand_total, "percent": percent,
                                "speed": speed, "eta": eta,
                                "files_done": state["files_done"], "files_total": 0},
                    "transferring": [],
                })
            if self.upload:
                api.upload(Path(self.entry.path), self.parent_id, parent_key=self.parent_key,
                           replace=self.replace, cancelled=self.cancelled, progress=progress)
            else:
                api.download(self.entry, self.local_folder / self.entry.name,
                             replace=self.replace, cancelled=self.cancelled, progress=progress)
            self.signals.done.emit(True, "Complete")
        except Exception as exc:
            self.signals.done.emit(False, "Cancelled" if self.cancelled.is_set() else str(exc))


class FileTable(QTableWidget):
    """Copy-only drag and drop between panes, plus Explorer drops onto Drive."""

    filesDropped = pyqtSignal(str, object, object)
    active_source = None

    def __init__(self, side: str):
        super().__init__(0, 3)
        self.side = side
        self.entries: list[Entry] = []
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def selected_entries(self) -> list[Entry]:
        rows = sorted({item.row() for item in self.selectedItems()})
        return [self.entries[row] for row in rows if row < len(self.entries)]

    def startDrag(self, _supported_actions):
        if not self.selected_entries():
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-drivedesk-copy", b"1")
        drag.setMimeData(mime)
        FileTable.active_source = self
        try:
            drag.exec(Qt.DropAction.CopyAction)
        finally:
            FileTable.active_source = None

    def _accepts(self, event) -> bool:
        source = FileTable.active_source
        if source is not None and source is not self:
            return source.side != self.side
        return self.side == "cloud" and event.mimeData().hasUrls() and any(
            url.isLocalFile() for url in event.mimeData().urls())

    def dragEnterEvent(self, event):
        if self._accepts(event):
            self.setProperty("dragOver", True)
            self.style().unpolish(self)
            self.style().polish(self)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._accepts(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        event.accept()

    def dropEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        if not self._accepts(event):
            event.ignore()
            return
        row = self.rowAt(int(event.position().y()))
        target = self.entries[row] if 0 <= row < len(self.entries) and self.entries[row].is_dir else None
        source = FileTable.active_source
        if source is not None:
            entries = source.selected_entries()
            side = source.side
        else:
            paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
            entries = [Entry(path.name, str(path), path.is_dir()) for path in paths if path.exists()]
            side = "explorer"
        if entries:
            self.filesDropped.emit(side, entries, target)
            event.acceptProposedAction()


class FilePane(QFrame):
    def __init__(self, title: str, *, local: bool):
        super().__init__()
        self.setObjectName("panel")
        self.entries: list[Entry] = []
        self.local = local
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 9)
        layout.setSpacing(7)
        top = QHBoxLayout()
        top.setSpacing(5)
        self.top_row = top
        self.title = QLabel(("🖥  " if local else "☁  ") + title)
        self.title.setObjectName("panetab")
        top.addWidget(self.title)
        top.addStretch()
        layout.addLayout(top)
        # Address bar: navigation icons + path, like a browser location row.
        addr = QFrame()
        addr.setObjectName("addressbar")
        arow = QHBoxLayout(addr)
        arow.setContentsMargins(5, 3, 5, 3)
        arow.setSpacing(4)
        self.up = self._navbtn(icons.up_icon(), "Up one folder")
        self.refresh = self._navbtn(icons.refresh_icon(), "Refresh")
        arow.addWidget(self.up)
        arow.addWidget(self.refresh)
        self.location = QLineEdit()
        self.location.setObjectName("addressline")
        self.location.setReadOnly(not local)
        self.location.setPlaceholderText("Folder path")
        arow.addWidget(self.location, 1)
        self.browse = self._navbtn(icons.browse_icon(), "Browse for a folder") if local else None
        if self.browse:
            arow.addWidget(self.browse)
        layout.addWidget(addr)
        self.notice = QLabel("")
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet("color: #e6b566; background: #33291a; border: 1px solid #4a3a22; border-radius: 6px; padding: 7px 9px;")
        self.notice.hide()
        layout.addWidget(self.notice)
        self.table = FileTable("pc" if local else "cloud")
        self.table.setHorizontalHeaderLabels(["Name", "Size", "Modified"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(56)
        header.setSectionsMovable(True)
        self.table.setColumnWidth(0, 320)
        self.table.setColumnWidth(1, 100)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setIconSize(QSize(20, 20))
        # Draggable row heights via the (hidden) vertical header.
        vheader = self.table.verticalHeader()
        vheader.setDefaultSectionSize(30)
        vheader.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        if local:
            layout.addWidget(self.table, 1)
            self.tree = None
        else:
            browser = QSplitter()
            self.tree = QTreeWidget()
            self.tree.setHeaderHidden(True)
            self.tree.setMinimumWidth(150)
            self.tree.setIconSize(QSize(18, 18))
            self.tree.hide()
            browser.addWidget(self.tree)
            browser.addWidget(self.table)
            browser.setSizes([190, 490])
            layout.addWidget(browser, 1)
        self.count = QLabel("0 items")
        self.count.setObjectName("muted")
        layout.addWidget(self.count)

    @staticmethod
    def _navbtn(icon: QIcon, tip: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName("navbtn")
        button.setIcon(icon)
        button.setIconSize(QSize(17, 17))
        button.setFixedSize(30, 30)
        button.setToolTip(tip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def show_entries(self, entries: list[Entry], *, group: bool = False):
        self.entries = entries
        self.table.entries = entries
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [entry.name, "" if group or entry.is_dir else size_text(entry.size),
                      "" if group else entry.modified[:10]]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setIcon(icons.entry_icon(entry.path, entry.is_dir, local=self.local))
                item.setData(Qt.ItemDataRole.UserRole, row)
                if col > 0:
                    item.setForeground(QColor("#73829a"))
                self.table.setItem(row, col, item)
        self.count.setText(f"{len(entries)} item{'s' if len(entries) != 1 else ''}")

    def selected(self) -> list[Entry]:
        return self.table.selected_entries()

    def show_notice(self, message: str):
        self.notice.setText(message)
        self.notice.setVisible(bool(message))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DriveDesk")
        self.setWindowIcon(icons.app_logo())
        self.resize(1380, 820)
        self.settings = QSettings("DriveDesk", "DriveDesk")
        self.rclone_path = find_rclone(self.settings.value("rclone_path", ""))
        self.rclone = Rclone(self.rclone_path) if self.rclone_path else None
        self.pool = QThreadPool.globalInstance()
        self.remote = ""
        self.remote_type = ""
        self.remote_types: dict[str, str] = {}
        self.remote_path = ""
        self.shared = False
        self.link_folder_id = ""
        self.link_resource_key = ""
        self.shared_folder_id = ""
        self.shared_folder_key = ""
        self.folder_history = []
        self.owner_filter: str | None = None
        self.shared_root: list[Entry] = []
        self.shared_loading = False
        self.shared_next_token = ""
        self.local_path = Path(self.settings.value("local_path", str(Path.home() / "Downloads")))
        if not self.local_path.is_dir():
            self.local_path = Path.home()
        self.remote_request = 0
        self.transfer_workers = []
        self.workers = set()
        self.transfer_items = {}
        self.mounts: dict[str, subprocess.Popen] = {}
        self.transfer_opts = {
            "bwlimit": self.settings.value("opt/bwlimit", "") or "",
            "transfers": self.settings.value("opt/transfers", "") or "",
            "checkers": self.settings.value("opt/checkers", "") or "",
            "excludes": self.settings.value("opt/excludes", "") or "",
            "includes": self.settings.value("opt/includes", "") or "",
        }
        self.closed = False
        self.local_request = 0
        self.build_ui()
        self.load_local()
        self.load_accounts()

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        rootcol = QVBoxLayout(root)
        rootcol.setContentsMargins(0, 0, 0, 0)
        rootcol.setSpacing(0)

        # ----- top toolbar: brand · workspace · drive tools · utilities -----
        topbar = QFrame()
        topbar.setObjectName("topbar")
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(16, 8, 16, 8)
        tb.setSpacing(3)
        brand = QFrame()
        brand.setObjectName("brandmark")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 12, 0)
        brand_layout.setSpacing(8)
        logo = QLabel()
        logo.setPixmap(icons.app_logo_pixmap(30))
        logo.setFixedSize(30, 30)
        brand_layout.addWidget(logo)
        brand_text = QLabel("DriveDesk")
        brand_text.setObjectName("brand")
        brand_layout.addWidget(brand_text)
        tb.addWidget(brand)
        tb.addWidget(self._toolsep())
        tb.addSpacing(8)
        self.accounts_btn = self._toolbtn("Accounts")
        self.accounts_btn.setIcon(icons.people_icon())
        self.accounts_btn.clicked.connect(self.account_manager_dialog)
        tb.addWidget(self.accounts_btn)
        tb.addWidget(self._toolsep())
        self.sync_btn = self._toolbtn("Synchronize")
        self.sync_btn.setIcon(icons.refresh_icon())
        self.sync_btn.clicked.connect(self.sync_dialog)
        tb.addWidget(self.sync_btn)
        self.mount_btn = self._toolbtn("Mount")
        self.mount_btn.setIcon(icons.mount_icon())
        self.mount_btn.clicked.connect(self.mount_dialog)
        if sys.platform == "win32":
            tb.addWidget(self.mount_btn)
        self.options_btn = self._toolbtn("Options")
        self.options_btn.setIcon(icons.settings_icon())
        self.options_btn.clicked.connect(self.transfer_options_dialog)
        tb.addWidget(self.options_btn)
        tb.addWidget(self._toolsep())
        self.tools_btn = self._toolbtn("Tools")
        self.tools_btn.setIcon(icons.toolbox_icon())
        self.tools_btn.clicked.connect(self.show_tools_menu)
        tb.addWidget(self.tools_btn)
        tb.addStretch()
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("search")
        self.search_edit.setPlaceholderText("🔍  Search current remote…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(250)
        self.search_edit.returnPressed.connect(self.run_search)
        tb.addWidget(self.search_edit)
        rootcol.addWidget(topbar)

        # Hidden accounts model — the single source of selection truth. Account
        # switching happens via the pane tab menu and the Accounts dialog.
        self.accounts = QListWidget()
        self.accounts.hide()
        self.accounts.currentItemChanged.connect(self.account_selected)
        self.accounts_menu = QMenu(self)
        self.binary_label = QLabel("")  # rclone status, surfaced in the Accounts dialog

        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(12, 10, 12, 8)
        ml.setSpacing(9)
        panes = QSplitter()
        self.pc = FilePane("This PC", local=True)
        self.cloud = FilePane("Google Drive", local=False)
        panes.addWidget(self.pc)
        panes.addWidget(self.cloud)
        panes.setSizes([520, 520])
        ml.addWidget(panes, 1)

        # Cloud pane tab: current account + Drive view switches live with the Drive pane.
        self.account_btn = QPushButton("Select account   ▼")
        self.account_btn.setObjectName("accounttab")
        self.account_btn.setIconSize(QSize(18, 18))
        self.account_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.account_btn.clicked.connect(self.show_accounts_menu)
        self.view_drive = self._toolbtn("My Drive", checkable=True)
        self.view_shared = self._toolbtn("Shared", checkable=True)
        self.open_shared_link = self._toolbtn("🔗")
        self.open_shared_link.setToolTip("Open a shared folder link")
        self.view_drive.clicked.connect(lambda: self.set_view(False))
        self.view_shared.clicked.connect(lambda: self.set_view(True))
        self.open_shared_link.clicked.connect(self.open_link)
        self.cloud.title.hide()
        self.cloud.top_row.insertWidget(0, self.account_btn)
        self.cloud.top_row.insertWidget(1, self.view_drive)
        self.cloud.top_row.insertWidget(2, self.view_shared)
        self.cloud.top_row.insertWidget(3, self.open_shared_link)

        self.pc.location.returnPressed.connect(self.local_address)
        self.pc.up.clicked.connect(self.local_up)
        self.pc.refresh.clicked.connect(self.load_local)
        self.pc.browse.clicked.connect(self.browse_local)
        self.pc.table.cellDoubleClicked.connect(self.local_open)
        self.pc.table.filesDropped.connect(self.pc_drop)
        self.pc.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pc.table.customContextMenuRequested.connect(lambda point: self.file_menu(self.pc, point))
        self.cloud.up.clicked.connect(self.remote_up)
        self.cloud.refresh.clicked.connect(self.load_remote)
        self.cloud.table.cellDoubleClicked.connect(self.remote_open)
        self.cloud.table.filesDropped.connect(self.cloud_drop)
        self.cloud.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cloud.table.customContextMenuRequested.connect(lambda point: self.file_menu(self.cloud, point))
        self.cloud.tree.itemClicked.connect(self.shared_tree_clicked)
        self.cloud.tree.itemExpanded.connect(self.shared_tree_expanded)
        self.cloud.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cloud.tree.customContextMenuRequested.connect(self.shared_tree_menu)

        transfer_panel = QFrame()
        transfer_panel.setObjectName("panel")
        tp = QVBoxLayout(transfer_panel)
        tp.setContentsMargins(12, 10, 12, 10)
        tp.setSpacing(7)
        transfer_heading = QHBoxLayout()
        title = QLabel("Transfers")
        title.setObjectName("heading")
        transfer_heading.addWidget(title)
        transfer_heading.addStretch()
        self.transfer_summary = QLabel("No transfers yet")
        self.transfer_summary.setObjectName("muted")
        transfer_heading.addWidget(self.transfer_summary)
        self.clear_finished = QPushButton("Clear finished")
        self.clear_finished.setObjectName("linkbtn")
        self.clear_finished.clicked.connect(self.clear_finished_transfers)
        transfer_heading.addWidget(self.clear_finished)
        tp.addLayout(transfer_heading)
        self.transfers = QTreeWidget()
        self.transfers.setObjectName("transfers")
        self.transfers.setColumnCount(9)
        self.transfers.setHeaderLabels(
            ["Operation", "Source", "Destination", "Status", "Size", "Progress", "Speed", "ETA / elapsed", ""])
        self.transfers.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.transfers.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.transfers.setRootIsDecorated(True)
        self.transfers.setUniformRowHeights(True)
        self.transfers.setAlternatingRowColors(False)
        self.transfers.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.transfers.customContextMenuRequested.connect(self.transfer_menu)
        self.transfers.setIconSize(QSize(18, 18))
        self.transfers.setMaximumHeight(232)
        self.transfers.setMinimumHeight(120)
        header = self.transfers.header()
        header.setStretchLastSection(False)
        for column in (0, 3, 4, 6, 7, 8):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        for column in (1, 2):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.transfers.setColumnWidth(5, 132)
        tp.addWidget(self.transfers)
        ml.addWidget(transfer_panel)
        rootcol.addWidget(main, 1)

        # ----- bottom status bar -----
        statusbar = QFrame()
        statusbar.setObjectName("statusbar")
        sb = QHBoxLayout(statusbar)
        sb.setContentsMargins(16, 7, 16, 7)
        sb.setSpacing(9)
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusdot")
        sb.addWidget(self.status_dot)
        self.status = QLabel("Ready")
        self.status.setObjectName("muted")
        sb.addWidget(self.status, 1)
        self.total_label = QLabel("")
        self.total_label.setObjectName("statvalue")
        sb.addWidget(self.total_label)
        self.total_bar = QProgressBar()
        self.total_bar.setObjectName("total")
        self.total_bar.setFixedWidth(210)
        self.total_bar.setRange(0, 100)
        self.total_bar.setValue(0)
        self.total_bar.setTextVisible(False)
        self.total_bar.hide()
        sb.addWidget(self.total_bar)
        sb.addWidget(self._toolsep())
        self.download_label = QLabel("↓ —")
        self.download_label.setObjectName("downstat")
        sb.addWidget(self.download_label)
        self.upload_label = QLabel("↑ —")
        self.upload_label.setObjectName("upstat")
        sb.addWidget(self.upload_label)
        rootcol.addWidget(statusbar)

        self.transfer_timer = QTimer(self)
        self.transfer_timer.timeout.connect(self.refresh_transfer_times)
        self.transfer_timer.start(1000)
        self.update_buttons()

    def set_status(self, message: str):
        self.status.setText(message)

    def _toolbtn(self, text: str, *, checkable: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("toolbtn")
        button.setIconSize(QSize(18, 18))
        button.setCheckable(checkable)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    @staticmethod
    def _toolsep() -> QFrame:
        sep = QFrame()
        sep.setObjectName("toolsep")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        return sep

    def toolbar_new_folder(self):
        pane = self.pc if self.pc.table.hasFocus() else (self.cloud if self.remote else self.pc)
        self.new_folder(pane, None)

    def refresh_all_panes(self):
        self.load_local()
        if self.remote:
            self.load_remote()

    def show_tools_menu(self):
        menu = QMenu(self)
        menu.addAction("Transfer options…", self.transfer_options_dialog)
        menu.addAction("Synchronize folders…", self.sync_dialog)
        if sys.platform == "win32":
            menu.addAction("Mount remote as drive…", self.mount_dialog)
        if self.mounts:
            submenu = menu.addMenu("Unmount drive")
            for drive in sorted(self.mounts):
                submenu.addAction(drive, lambda _=False, letter=drive: self.unmount(letter))
        menu.addSeparator()
        menu.addAction("Refresh accounts", self.load_accounts)
        menu.addAction("Choose rclone executable…", self.choose_rclone)
        menu.addAction("rclone version", self.show_rclone_version)
        menu.addAction("Show rclone config location", self.show_config_location)
        menu.addSeparator()
        menu.addAction("Check for updates…", self.check_for_updates)
        menu.exec(self.tools_btn.mapToGlobal(self.tools_btn.rect().bottomLeft()))

    def check_for_updates(self):
        """Check GitHub Releases without blocking the UI."""
        self.set_status("Checking for updates…")
        def available(info):
            self.set_status(f"Update available: {info['tag']}")
            self._show_update_prompt(info)
        def current(_=None):
            self.set_status("DriveDesk is up to date.")
            QMessageBox.information(self, "No updates", f"DriveDesk {APP_VERSION} is the latest release.")
        def failed(message):
            self.set_status("Update check failed")
            QMessageBox.warning(self, "Could not check for updates", message)
        self.run_async(lambda: check_for_update(GITHUB_REPO, APP_VERSION),
                       lambda info: available(info) if info else current(),
                       context="Update check", on_error=failed)

    def _show_update_prompt(self, info: dict):
        notes = info.get("notes") or "A newer version of DriveDesk is available."
        box = QMessageBox(self)
        box.setWindowTitle(f"DriveDesk {info['tag']} available")
        box.setText(f"DriveDesk {info['tag']} is available (you have {APP_VERSION}).")
        box.setInformativeText(notes[:1200])
        download_button = box.addButton("Download update", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("View release", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        if box.clickedButton() is download_button:
            self._download_update(info)
        elif box.clickedButton() and box.clickedButton().text() == "View release":
            QDesktopServices.openUrl(QUrl(info.get("url", "")))

    def _download_update(self, info: dict):
        progress = QProgressDialog("Downloading DriveDesk update…", "Cancel", 0, 100, self)
        progress.setWindowTitle("DriveDesk update")
        progress.setAutoClose(False)
        progress.setMinimumDuration(0)
        progress.show()
        def on_progress(value):
            received, total = value
            progress.setRange(0, 100 if total else 0)
            if total:
                progress.setValue(min(100, int(received * 100 / total)))
        def done(path):
            progress.close()
            answer = QMessageBox.question(
                self, "Update downloaded", "The update is ready. Restart DriveDesk and run the installer now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                try:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
                    self.close()
                except OSError as exc:
                    QMessageBox.warning(self, "Could not launch installer", str(exc))
        def failed(message):
            progress.close()
            QMessageBox.warning(self, "Update download failed", message)
        self.run_async_progress(
            lambda emit: download_update(info, progress=lambda received, total: emit((received, total))),
            on_progress, done, context="Update download", on_error=failed,
        )

    # ---- Search ----
    def run_search(self):
        term = self.search_edit.text().strip()
        if not term:
            self.load_remote()
            return
        if not self.rclone or not self.remote:
            self.set_status("Select a remote to search.")
            return
        if self.shared or self.link_folder_id:
            self.set_status("Search works in My Drive and other remotes; switch off Shared view to search.")
            return
        remote, path, request = self.remote, self.remote_path, self.remote_request + 1
        self.remote_request = request
        self.cloud.show_notice(f"Searching for “{term}”…")
        self.set_status(f"Searching {self.account_display_name()} for “{term}”…")
        def done(entries):
            if request != self.remote_request:
                return
            self.cloud.show_notice("")
            self.cloud.show_entries(entries)
            self.cloud.location.setText(f"Search “{term}” · {len(entries)} results")
            self.set_status(f"{len(entries)} match{'es' if len(entries) != 1 else ''} for “{term}” (Refresh to exit search)")
        def failed(message):
            if request != self.remote_request:
                return
            self.cloud.show_notice(f"Search failed: {message}")
            self.set_status(f"Search: {message}")
        self.run_async(lambda: self.rclone.search_files(remote, path, term), done,
                       context="Search", on_error=failed)

    # ---- Transfer options ----
    def transfer_options_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Transfer options")
        form = QFormLayout(dialog)
        form.addRow(QLabel("These apply to uploads, downloads and syncs on regular remotes."))
        bwlimit = QLineEdit(self.transfer_opts["bwlimit"])
        bwlimit.setPlaceholderText("e.g. 10M, 500k, or blank for unlimited")
        transfers = QLineEdit(str(self.transfer_opts["transfers"]))
        transfers.setPlaceholderText("parallel files, e.g. 4")
        checkers = QLineEdit(str(self.transfer_opts["checkers"]))
        checkers.setPlaceholderText("parallel checks, e.g. 8")
        excludes = QLineEdit(self.transfer_opts["excludes"])
        excludes.setPlaceholderText("*.tmp, .DS_Store  (comma or newline separated)")
        includes = QLineEdit(self.transfer_opts["includes"])
        includes.setPlaceholderText("*.mp4, *.mov  (leave blank for everything)")
        form.addRow("Bandwidth limit", bwlimit)
        form.addRow("Parallel transfers", transfers)
        form.addRow("Parallel checkers", checkers)
        form.addRow("Exclude patterns", excludes)
        form.addRow("Include patterns", includes)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.transfer_opts = {
            "bwlimit": bwlimit.text().strip(), "transfers": transfers.text().strip(),
            "checkers": checkers.text().strip(), "excludes": excludes.text().strip(),
            "includes": includes.text().strip()}
        for key, value in self.transfer_opts.items():
            self.settings.setValue(f"opt/{key}", value)
        self.set_status("Transfer options saved")

    # ---- Synchronize ----
    def sync_dialog(self):
        if not self.rclone or not self.remote:
            self.set_status("Select a remote before synchronizing.")
            return
        if self.shared or self.link_folder_id:
            self.set_status("Synchronize works with My Drive and other remotes, not the Shared view.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Synchronize folders")
        form = QFormLayout(dialog)
        pc_edit = QLineEdit(str(self.local_path))
        cloud_edit = QLineEdit(f"{self.remote}:{self.remote_path}")
        direction = QComboBox()
        direction.addItems([f"PC  →  {self.account_display_name()}",
                            f"{self.account_display_name()}  →  PC"])
        mode = QComboBox()
        mode.addItems(["Mirror (make destination identical — deletes extra files)",
                       "Copy (add new/changed, never delete)",
                       "Move (copy then remove from source)",
                       "Two-way sync (bisync, resync baseline)"])
        dry_run = QCheckBox("Dry run first (preview changes, transfer nothing)")
        dry_run.setChecked(True)
        form.addRow("PC folder", pc_edit)
        form.addRow("Cloud folder", cloud_edit)
        form.addRow("Direction", direction)
        form.addRow("Mode", mode)
        form.addRow("", dry_run)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Run")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        pc_side = pc_edit.text().strip()
        cloud_side = cloud_edit.text().strip()
        if not pc_side or not cloud_side:
            self.set_status("Both a PC folder and a cloud folder are required.")
            return
        modes = ["mirror", "copy", "move", "bisync"]
        chosen = modes[mode.currentIndex()]
        to_cloud = direction.currentIndex() == 0
        source, dest = (pc_side, cloud_side) if to_cloud else (cloud_side, pc_side)
        try:
            args = sync_args(source, dest, chosen, dry_run=dry_run.isChecked(),
                             extra=self._extra_transfer_flags())
        except RcloneError as exc:
            QMessageBox.warning(self, "Synchronize", str(exc))
            return
        worker = TransferWorker(self.rclone_path, args)
        preview = " · dry run" if dry_run.isChecked() else ""
        operation = {"mirror": "Mirror", "copy": "Copy", "move": "Move", "bisync": "Two-way"}[chosen] + preview
        self._add_transfer_row(worker, operation=operation, upload=to_cloud, source=source,
                               destination=dest, is_dir=True, total=-1,
                               label=f"{operation} {source} → {dest}")
        self.refresh_transfer_times()
        self.set_status(f"Started {operation.lower()} sync…")

    # ---- Mount ----
    def _free_drive_letters(self) -> list[str]:
        used = {f"{chr(letter)}:" for letter in range(ord('A'), ord('Z') + 1)
                if os.path.exists(f"{chr(letter)}:\\")}
        used |= set(self.mounts)
        return [f"{chr(letter)}:" for letter in range(ord('G'), ord('Z') + 1)
                if f"{chr(letter)}:" not in used]

    def mount_dialog(self):
        if not self.rclone or not self.remote:
            self.set_status("Select a remote before mounting.")
            return
        letters = self._free_drive_letters()
        if not letters:
            self.set_status("No free drive letters available.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Mount remote as drive")
        form = QFormLayout(dialog)
        form.addRow(QLabel(f"Mount {self.account_display_name()} as a Windows drive.\n"
                           "Requires WinFsp (winfsp.dev) installed."))
        path_edit = QLineEdit(self.remote_path)
        path_edit.setPlaceholderText("Subfolder, or blank for the whole remote")
        letter = QComboBox()
        letter.addItems(letters)
        form.addRow("Folder (optional)", path_edit)
        form.addRow("Drive letter", letter)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Mount")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.do_mount(self.remote, path_edit.text().strip(), letter.currentText())

    def do_mount(self, remote: str, path: str, drive: str):
        try:
            args = mount_args(remote, path, drive)
        except RcloneError as exc:
            QMessageBox.warning(self, "Mount", str(exc))
            return
        try:
            proc = subprocess.Popen(
                [self.rclone_path, *args], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", env=network_env(),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            QMessageBox.warning(self, "Mount", str(exc))
            return
        self.mounts[drive] = proc
        self.set_status(f"Mounting {remote}: on {drive}…")
        QTimer.singleShot(2800, lambda: self._check_mount(drive))

    def _check_mount(self, drive: str):
        proc = self.mounts.get(drive)
        if proc is None:
            return
        if proc.poll() is not None:
            error = ""
            try:
                error = (proc.stderr.read() or "").strip() if proc.stderr else ""
            except OSError:
                pass
            self.mounts.pop(drive, None)
            if "winfsp" in error.lower() or "cgofuse" in error.lower() or "fuse" in error.lower():
                QMessageBox.warning(self, "WinFsp required",
                                    "Mounting needs WinFsp. Install it from https://winfsp.dev/rel/ "
                                    "and try again.")
                self.set_status("Mount failed — install WinFsp (winfsp.dev)")
            else:
                self.set_status(f"Mount failed: {error[:150] or 'rclone exited'}")
            return
        self.set_status(f"Mounted on {drive} — opening in Explorer")
        QDesktopServices.openUrl(QUrl.fromLocalFile(f"{drive}\\"))

    def unmount(self, drive: str):
        proc = self.mounts.pop(drive, None)
        if proc and proc.poll() is None:
            proc.terminate()
        self.set_status(f"Unmounted {drive}")

    def show_rclone_version(self):
        if not self.rclone:
            self.set_status("Select the rclone executable first.")
            return
        self.run_async(lambda: self.rclone.run("version", timeout=20),
                       lambda text: QMessageBox.information(self, "rclone version", text.strip()[:1200]),
                       context="rclone version")

    def show_config_location(self):
        if not self.rclone:
            self.set_status("Select the rclone executable first.")
            return
        self.run_async(lambda: self.rclone.run("config", "file", timeout=20),
                       lambda text: QMessageBox.information(self, "rclone config", text.strip()),
                       context="rclone config")

    def _account_text(self, remote: str) -> str:
        return str(self.settings.value(f"account_label/{remote}", remote))

    def show_accounts_menu(self):
        self.accounts_menu.exec(self.account_btn.mapToGlobal(self.account_btn.rect().bottomLeft()))

    def rebuild_accounts_menu(self):
        """The cloud-pane tab dropdown: switch account, or manage."""
        menu = self.accounts_menu
        menu.clear()
        for index in range(self.accounts.count()):
            item = self.accounts.item(index)
            remote = item.data(Qt.ItemDataRole.UserRole)
            action = menu.addAction(icons.backend_icon(self.remote_types.get(remote, "")),
                                    item.text().strip(), lambda _=False, row=index: self.accounts.setCurrentRow(row))
            action.setCheckable(True)
            action.setChecked(remote == self.remote)
        menu.addSeparator()
        menu.addAction("＋  Add Google account", self.add_google_account)
        menu.addAction("＋  Add other cloud…", self.add_remote)
        menu.addAction("⚙  Manage accounts…", self.account_manager_dialog)

    def account_manager_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Accounts")
        dialog.setMinimumWidth(440)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(9)
        layout.addWidget(QLabel("Connected remotes"))
        listw = QListWidget()
        for index in range(self.accounts.count()):
            source = self.accounts.item(index)
            item = QListWidgetItem(source.icon(), source.text().strip())
            item.setData(Qt.ItemDataRole.UserRole, source.data(Qt.ItemDataRole.UserRole))
            listw.addItem(item)
        listw.setIconSize(QSize(22, 22))
        listw.setCurrentRow(max(0, self.accounts.currentRow()))
        listw.setMinimumHeight(150)
        layout.addWidget(listw)

        def selected():
            item = listw.currentItem()
            return item.data(Qt.ItemDataRole.UserRole) if item else None

        add_row = QHBoxLayout()
        add_google = QPushButton("＋  Add Google account")
        add_google.setObjectName("primary")
        add_google.clicked.connect(lambda: (dialog.accept(), self.add_google_account()))
        add_other = QPushButton("＋  Add other cloud…")
        add_other.clicked.connect(lambda: (dialog.accept(), self.add_remote()))
        add_row.addWidget(add_google)
        add_row.addWidget(add_other)
        add_row.addStretch()
        layout.addLayout(add_row)

        manage_row = QHBoxLayout()
        def rename_selected():
            remote = selected()
            if remote:
                self.rename_account(remote)
                if listw.currentItem():
                    listw.currentItem().setText(self._account_text(remote).strip())
        rename = QPushButton("Rename…")
        rename.clicked.connect(rename_selected)
        reconnect = QPushButton("Reconnect…")
        reconnect.clicked.connect(lambda: selected() and (dialog.accept(), self.reconnect_account(selected())))
        remove = QPushButton("Remove…")
        remove.clicked.connect(lambda: selected() and (dialog.accept(), self.remove_account(selected())))
        manage_row.addWidget(rename)
        manage_row.addWidget(reconnect)
        manage_row.addWidget(remove)
        manage_row.addStretch()
        layout.addLayout(manage_row)

        footer = QHBoxLayout()
        status = QLabel(self.binary_label.text() or "rclone not selected")
        status.setObjectName("muted")
        footer.addWidget(status, 1)
        set_binary = QPushButton("Set rclone executable…")
        set_binary.clicked.connect(lambda: (dialog.accept(), self.choose_rclone()))
        footer.addWidget(set_binary)
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        footer.addWidget(close)
        layout.addLayout(footer)
        dialog.exec()

    def rename_account(self, remote: str):
        current = self.settings.value(f"account_label/{remote}", remote)
        name, accepted = QInputDialog.getText(self, "Rename account", "Display name:", text=str(current))
        name = name.strip()
        if not accepted or not name:
            return
        self.settings.setValue(f"account_label/{remote}", name)
        for index in range(self.accounts.count()):
            current_item = self.accounts.item(index)
            if current_item.data(Qt.ItemDataRole.UserRole) == remote:
                current_item.setText(self._account_text(remote))
                break
        self.rebuild_accounts_menu()
        if self.remote == remote:
            self.update_buttons()
        self.set_status(f"Renamed account to {name}")

    def reconnect_account(self, remote: str):
        if not self.rclone:
            return
        cancelled = Event()
        progress = QProgressDialog("Re-authorize this account in the browser window that opens.",
                                   "Cancel", 0, 0, self)
        progress.setWindowTitle("Reconnect account")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.canceled.connect(cancelled.set)
        progress.show()
        self.set_status("Waiting for Google sign-in in your browser…")
        def done(_result):
            progress.close()
            self.set_status(f"Reconnected {self.settings.value(f'account_label/{remote}', remote)}")
            if self.remote == remote:
                self.load_remote()
        def failed(message):
            progress.close()
            self.set_status(message)
            if not cancelled.is_set():
                QMessageBox.warning(self, "Could not reconnect", message)
        self.run_async(lambda: self.rclone.reconnect_drive(remote, cancelled), done,
                       context="Reconnect", on_error=failed)

    def remove_account(self, remote: str):
        label = self.settings.value(f"account_label/{remote}", remote)
        answer = QMessageBox.question(
            self, "Remove account",
            f"Remove '{label}' from rclone?\n\nThis deletes the saved connection on this PC. "
            "Your Google Drive files are not affected, and you can add the account again later.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        def done(_result):
            self.settings.remove(f"account_label/{remote}")
            if self.remote == remote:
                self.remote = ""
                self.remote_type = ""
                self.cloud.show_entries([])
            self.set_status(f"Removed {label}")
            self.load_accounts()
        self.run_async(lambda: self.rclone.delete_remote(remote), done, context="Remove account")

    def account_display_name(self) -> str:
        return str(self.settings.value(f"account_label/{self.remote}", self.remote) or "Google Drive")

    def run_async(self, fn, success, *, context: str, on_error=None):
        worker = Worker(fn)
        self.workers.add(worker)
        def succeeded(value):
            self.workers.discard(worker)
            if not self.closed:
                success(value)
        def failed(message):
            self.workers.discard(worker)
            if not self.closed:
                (on_error or (lambda msg: self.set_status(f"{context}: {msg}")))(message)
        worker.signals.result.connect(succeeded)
        worker.signals.error.connect(failed)
        self.pool.start(worker)

    def run_async_progress(self, fn, progress, success, *, context: str, on_error=None):
        worker = Worker(lambda: fn(worker.signals.progress.emit))
        self.workers.add(worker)
        worker.signals.progress.connect(lambda value: progress(value) if not self.closed else None)
        def done(value):
            self.workers.discard(worker)
            if not self.closed:
                success(value)
        def failed(message):
            self.workers.discard(worker)
            if not self.closed:
                (on_error or (lambda msg: self.set_status(f"{context}: {msg}")))(message)
        worker.signals.result.connect(done)
        worker.signals.error.connect(failed)
        self.pool.start(worker)

    def closeEvent(self, event):
        self.closed = True
        for worker in list(self.transfer_workers):
            worker.cancel()
        for drive, proc in list(self.mounts.items()):
            if proc.poll() is None:
                proc.terminate()
            self.mounts.pop(drive, None)
        super().closeEvent(event)

    def choose_rclone(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select rclone executable", str(Path.home()), "Executables (*.exe);;All files (*)")
        if filename:
            self.rclone_path = filename
            self.rclone = Rclone(filename)
            self.settings.setValue("rclone_path", filename)
            self.load_accounts()

    def add_google_account(self):
        if not self.rclone_path:
            self.choose_rclone()
            return
        name = "gdrive_" + uuid.uuid4().hex[:8]
        cancelled = Event()
        progress = QProgressDialog("Choose your Google account in the browser window, then allow Drive access.",
                                   "Cancel", 0, 0, self)
        progress.setWindowTitle("Connect Google Drive")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.canceled.connect(cancelled.set)
        progress.show()
        self.set_status("Waiting for Google sign-in in your browser…")
        def connect_account():
            self.rclone.create_drive(name, cancelled)
            return name
        def done(remote):
            progress.close()
            # Let load_accounts resolve the real "Name (email)" via the Drive API,
            # instead of locking in an id-based fallback that blocks resolution.
            self.settings.remove(f"account_label/{remote}")
            self.remote = ""
            self.remote_path = ""
            self.set_view(False)
            self.load_accounts(preferred=remote)
            self.set_status("Connected Google Drive")
        def failed(message):
            progress.close()
            self.set_status(message)
            if not cancelled.is_set():
                QMessageBox.warning(self, "Could not connect Google Drive", message)
            self.load_accounts()
        self.run_async(connect_account, done, context="Google sign-in", on_error=failed)

    def add_remote(self):
        if not self.rclone_path:
            self.choose_rclone()
            return
        keys = list(BACKENDS)
        labels = [BACKENDS[key]["label"] for key in keys]
        choice, accepted = QInputDialog.getItem(
            self, "Add remote", "Choose a cloud service to connect:", labels, 0, False)
        if not accepted:
            return
        backend = keys[labels.index(choice)]
        name = f"{backend}_{uuid.uuid4().hex[:8]}"
        fields = BACKENDS[backend]["fields"]
        params: dict[str, str] = {}
        if fields:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Add {BACKENDS[backend]['label']}")
            form = QFormLayout(dialog)
            form.addRow(QLabel(f"Enter your {BACKENDS[backend]['label']} details."))
            editors: dict[str, QLineEdit] = {}
            for key, label, default, secret in fields:
                edit = QLineEdit(default)
                if secret:
                    edit.setEchoMode(QLineEdit.EchoMode.Password)
                    edit.setPlaceholderText("stored by rclone, obscured")
                form.addRow(label, edit)
                editors[key] = edit
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            form.addRow(buttons)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            params = {key: editor.text().strip() for key, editor in editors.items()}
            required = fields[0][0]
            if not params.get(required):
                QMessageBox.warning(self, "Missing details", f"{fields[0][1]} is required.")
                return
        self._create_remote_async(name, backend, params)

    def _create_remote_async(self, name: str, backend: str, params: dict[str, str]):
        cancelled = Event()
        oauth = backend in OAUTH_BACKENDS
        progress = None
        if oauth:
            progress = QProgressDialog(
                f"Authorize {BACKENDS[backend]['label']} in the browser window that opens, then allow access.",
                "Cancel", 0, 0, self)
            progress.setWindowTitle(f"Connect {BACKENDS[backend]['label']}")
            progress.setMinimumDuration(0)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.canceled.connect(cancelled.set)
            progress.show()
            self.set_status(f"Waiting for {BACKENDS[backend]['label']} authorization…")
        else:
            self.set_status(f"Adding {BACKENDS[backend]['label']}…")
        def op():
            self.rclone.create_remote(name, backend, params, cancelled)
            return name
        def done(_result):
            if progress:
                progress.close()
            self.settings.setValue(f"account_label/{name}", BACKENDS[backend]["label"])
            self.set_status(f"Added {BACKENDS[backend]['label']}")
            self.load_accounts(preferred=name)
        def failed(message):
            if progress:
                progress.close()
            self.set_status(message)
            if not cancelled.is_set():
                QMessageBox.warning(self, "Could not add remote", message)
            self.load_accounts()
        self.run_async(op, done, context="Add remote", on_error=failed)

    def load_accounts(self, preferred: str | None = None):
        if not isinstance(preferred, str):
            preferred = None
        self.binary_label.setText(f"rclone: {Path(self.rclone_path).name}" if self.rclone_path else "rclone not found")
        if not self.rclone:
            self.set_status("Select rclone.exe to connect your configured accounts.")
            return
        self.set_status("Loading accounts…")
        previous = preferred or self.remote
        def done(pairs):
            self.remote_types = {name: kind for name, kind in pairs}
            names = [name for name, _kind in pairs]
            self.accounts.blockSignals(True)
            self.accounts.clear()
            for name, kind in pairs:
                label = str(self.settings.value(f"account_label/{name}", name))
                item = QListWidgetItem(icons.backend_icon(kind), self._account_text(name))
                item.setData(Qt.ItemDataRole.UserRole, name)
                item.setToolTip(f"{name}  ·  {BACKENDS.get(kind, {}).get('label', kind or 'remote')}")
                self.accounts.addItem(item)
                # Resolve a friendly "Name (email)" for accounts that are still unnamed
                # or stuck on an id-based fallback from an older version.
                unresolved = label == name or label.startswith("Google Drive (")
                if unresolved and kind == "drive":
                    def apply_label(value, remote_name=name):
                        self.settings.setValue(f"account_label/{remote_name}", value)
                        for index in range(self.accounts.count()):
                            current = self.accounts.item(index)
                            if current.data(Qt.ItemDataRole.UserRole) == remote_name:
                                current.setText(self._account_text(remote_name))
                                break
                        self.rebuild_accounts_menu()
                        if self.remote == remote_name:
                            self.update_buttons()
                    def label_done(value, remote_name=name):
                        if value and value != remote_name:
                            apply_label(value, remote_name)
                        else:
                            apply_label(f"Google Drive ({remote_name[-4:]})", remote_name)
                    self.run_async(lambda remote_name=name: GoogleDriveAPI(self.rclone, remote_name).account_label(),
                                   label_done, context="Account name",
                                   on_error=lambda _m, remote_name=name: apply_label(
                                       f"Google Drive ({remote_name[-4:]})", remote_name))
            self.accounts.blockSignals(False)
            if names:
                index = names.index(previous) if previous in names else 0
                self.accounts.setCurrentRow(index)
                self.account_selected(self.accounts.item(index), None)
                self.set_status(f"{len(names)} remote{'s' if len(names) != 1 else ''} connected")
            else:
                self.remote = ""
                self.remote_type = ""
                self.cloud.show_entries([])
                self.set_status("No remotes yet. Open Accounts to connect Google Drive or another cloud.")
            self.rebuild_accounts_menu()
            self.update_buttons()
        self.run_async(self.rclone.remotes, done, context="Accounts")

    def account_selected(self, current, _previous):
        if current is None:
            return
        remote = current.data(Qt.ItemDataRole.UserRole)
        if remote != self.remote:
            self.remote = remote
            self.remote_type = self.remote_types.get(remote, "")
            self.remote_path = ""
            self.owner_filter = None
            self.shared_root = []
            self.shared_loading = False
            self.shared_next_token = ""
            self.shared_folder_id = ""
            self.shared_folder_key = ""
            self.link_folder_id = ""
            self.link_resource_key = ""
            self.folder_history = []
            self.cloud.show_entries([])
            self.reset_shared_tree()
            if self.remote_type == "drive":
                self.load_shared_sidebar(remote)
            else:
                self.shared = False
        self.load_remote()

    def set_view(self, shared: bool):
        self.shared = shared
        self.link_folder_id = ""
        self.link_resource_key = ""
        self.remote_path = ""
        self.owner_filter = None
        self.shared_folder_id = ""
        self.shared_folder_key = ""
        self.folder_history = []
        self.cloud.show_entries([])
        self.update_buttons()
        self.load_remote()

    def open_link(self):
        if not self.remote:
            self.set_status("Select a Google Drive account first.")
            return
        value, accepted = QInputDialog.getText(self, "Open shared folder", "Paste a Google Drive folder link:")
        if not accepted or not value.strip():
            return
        try:
            folder_id, resource_key = parse_drive_folder_url(value)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid folder link", str(exc))
            return
        self.link_folder_id = folder_id
        self.link_resource_key = resource_key
        self.shared_folder_id = folder_id
        self.shared_folder_key = resource_key
        self.folder_history = []
        self.shared = False
        self.remote_path = ""
        self.owner_filter = None
        self.cloud.show_entries([])
        self.load_remote()
        # Remember this link under "Opened links" in the Drive tree.
        remote = self.remote
        self._add_saved_link(remote, folder_id, resource_key, "Shared folder")
        self.run_async(lambda: GoogleDriveAPI(self.rclone, remote).folder_name(folder_id, resource_key),
                       lambda name: self._add_saved_link(remote, folder_id, resource_key, name),
                       context="Link name", on_error=lambda _message: None)

    def update_buttons(self):
        is_drive = self.remote_type == "drive"
        on_drive_view = not self.shared and not self.link_folder_id
        self.view_drive.setChecked(is_drive and on_drive_view)
        self.view_shared.setChecked(is_drive and self.shared and not self.link_folder_id)
        self.view_drive.setEnabled(bool(self.remote) and is_drive)
        self.view_shared.setEnabled(bool(self.remote) and is_drive)
        self.view_drive.setVisible(is_drive or not self.remote)
        self.view_shared.setVisible(is_drive or not self.remote)
        self.open_shared_link.setVisible(is_drive or not self.remote)
        self.open_shared_link.setEnabled(bool(self.remote) and is_drive)
        self.cloud.tree.setVisible(bool(self.remote) and is_drive)
        if self.remote:
            self.account_btn.setIcon(icons.backend_icon(self.remote_type))
            self.account_btn.setText(self._account_text(self.remote).strip() + "   ▼")
        else:
            self.account_btn.setIcon(QIcon())
            self.account_btn.setText("Select account   ▼")

    def load_local(self):
        self.pc.location.setText(str(self.local_path))
        self.pc.show_entries([])
        self.local_request += 1
        request, folder = self.local_request, self.local_path
        self.run_async(lambda: local_entries(folder),
                       lambda entries: self.pc.show_entries(entries) if request == self.local_request else None,
                       context="This PC")

    def browse_local(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose PC folder", str(self.local_path))
        if folder:
            self.local_path = Path(folder)
            self.settings.setValue("local_path", folder)
            self.load_local()

    def local_address(self):
        target = Path(self.pc.location.text().strip()).expanduser()
        if target.is_dir():
            self.local_path = target.resolve()
            self.settings.setValue("local_path", str(self.local_path))
            self.load_local()
        else:
            self.set_status("That PC folder does not exist.")
            self.pc.location.setText(str(self.local_path))

    def local_up(self):
        self.local_path = self.local_path.parent
        self.load_local()

    def local_open(self, row: int, _col: int):
        if row < len(self.pc.entries) and self.pc.entries[row].is_dir:
            self.local_path = Path(self.pc.entries[row].path)
            self.settings.setValue("local_path", str(self.local_path))
            self.load_local()

    def load_remote(self):
        self.update_buttons()
        if not self.remote or not self.rclone:
            return
        self.remote_request += 1
        request = self.remote_request
        remote, path, shared, owner = self.remote, self.remote_path, self.shared, self.owner_filter
        folder_id, resource_key = self.link_folder_id, self.link_resource_key
        display = self.account_display_name()
        label = f"{display}:/{path}" if path else f"{display}:/"
        if folder_id:
            label = f"Shared link / {path}" if path else "Shared link /"
        elif shared:
            owner_label = "All shared items" if owner == ALL_SHARED else owner
            label = f"Shared with me / {owner_label or path}" if (owner or path) else "Shared with me / People"
        self.cloud.location.setText(label)
        if not self.cloud.entries or not (shared and not path and owner is None):
            self.cloud.show_entries([])
        self.cloud.show_notice("Loading shared items…" if shared or folder_id else "Loading Drive files…")
        self.set_status("Loading Drive files…")
        if shared and owner is not None and not path:
            self.show_owner_group(owner)
            return
        def failed(message):
            if request != self.remote_request:
                return
            self.cloud.show_notice(f"Could not load this folder: {message}")
            self.set_status(f"Drive: {message}")
        def done(entries):
            if request != self.remote_request:
                return
            self.cloud.show_notice("")
            if shared and not path and owner is None:
                self.shared_root = entries
                if not entries:
                    self.populate_shared_tree([])
                    self.cloud.show_entries([])
                    self.cloud.show_notice(f"No shared items found for {remote}. Check that this is the Google account used in Drive.")
                    self.set_status("No shared items found")
                    return
                self.populate_shared_tree(entries)
                groups = sorted({e.owner or "Unknown owner" for e in entries}, key=str.casefold)
                self.cloud.show_entries([Entry(name, "", True) for name in groups], group=True)
                self.set_status(f"{len(groups)} people · {len(entries)} shared items")
            else:
                self.cloud.show_entries(entries)
                self.set_status(f"{len(entries)} items · upload requires edit access" if folder_id else f"{len(entries)} items")
        if shared and not path and owner is None and self.shared_root:
            done(self.shared_root)
        elif shared and not path and owner is None and self.shared_loading:
            self.set_status("Loading shared items from Google Drive…")
            return
        elif shared or folder_id:
            current_id = self.shared_folder_id if path or folder_id else ""
            current_key = self.shared_folder_key if current_id else ""
            self.run_async(lambda: GoogleDriveAPI(self.rclone, remote).list_files(
                folder_id=current_id, resource_key=current_key, prefix=path),
                done, context="Drive", on_error=failed)
        else:
            self.run_async(lambda: self.rclone.list(remote, path), done, context="Drive", on_error=failed)

    def show_owner_group(self, owner: str):
        self.owner_filter = owner
        label = "All shared items" if owner == ALL_SHARED else owner
        self.cloud.location.setText(f"Shared with me / {label}")
        entries = self.shared_root if owner == ALL_SHARED else [e for e in self.shared_root if (e.owner or "Unknown owner") == owner]
        self.cloud.show_entries(entries)
        self.cloud.show_notice("")
        self.set_status(f"{len(entries)} items in {label}")

    def populate_shared_tree(self, entries: list[Entry]):
        tree = self.cloud.tree
        if not hasattr(self, "shared_tree_root"):
            self.reset_shared_tree()
        self.folder_tree_generation = getattr(self, "folder_tree_generation", 0) + 1
        self.shared_tree_root.takeChildren()
        groups: dict[str, list[Entry]] = {}
        for entry in entries:
            groups.setdefault(entry.owner or "Unknown owner", []).append(entry)
        for owner in sorted(groups, key=str.casefold):
            person = QTreeWidgetItem([owner])
            person.setIcon(0, icons.person_icon())
            person.setData(0, Qt.ItemDataRole.UserRole, ("owner", owner))
            self.shared_tree_root.addChild(person)
            for entry in groups[owner]:
                if entry.is_dir:
                    folder = QTreeWidgetItem([entry.name])
                    folder.setIcon(0, icons.folder_icon())
                    folder.setData(0, Qt.ItemDataRole.UserRole,
                                   ("folder", entry.path, entry.id, entry.resource_key))
                    person.addChild(folder)
                    folder.addChild(QTreeWidgetItem(["Loading…"]))
        tree.expandItem(self.shared_tree_root)

    def reset_shared_tree(self):
        tree = self.cloud.tree
        self.tree_generation = getattr(self, "tree_generation", 0) + 1
        tree.clear()
        drive = QTreeWidgetItem(["My Drive"])
        drive.setIcon(0, icons.drive_icon())
        drive.setData(0, Qt.ItemDataRole.UserRole, ("drive", ""))
        tree.addTopLevelItem(drive)
        self.shared_tree_root = QTreeWidgetItem(["Shared with me"])
        self.shared_tree_root.setIcon(0, icons.people_icon())
        self.shared_tree_root.setData(0, Qt.ItemDataRole.UserRole, ("shared", ""))
        tree.addTopLevelItem(self.shared_tree_root)
        self.links_root = QTreeWidgetItem(["Opened links"])
        self.links_root.setIcon(0, icons.link_icon())
        self.links_root.setData(0, Qt.ItemDataRole.UserRole, ("linkroot", ""))
        tree.addTopLevelItem(self.links_root)
        self.populate_links_tree()

    def _saved_links(self, remote: str) -> list[dict]:
        if not remote:
            return []
        try:
            return json.loads(self.settings.value(f"opened_links/{remote}", "[]")) or []
        except (ValueError, TypeError):
            return []

    def _add_saved_link(self, remote: str, folder_id: str, key: str, name: str):
        links = self._saved_links(remote)
        existing = next((link for link in links if link.get("id") == folder_id), None)
        if existing is None:
            links.append({"id": folder_id, "key": key, "name": name})
        elif name and existing.get("name") != name:
            existing["name"] = name
        self.settings.setValue(f"opened_links/{remote}", json.dumps(links))
        if remote == self.remote:
            self.populate_links_tree()

    def remove_saved_link(self, folder_id: str):
        links = [link for link in self._saved_links(self.remote) if link.get("id") != folder_id]
        self.settings.setValue(f"opened_links/{self.remote}", json.dumps(links))
        self.populate_links_tree()
        self.set_status("Removed from Opened links")

    def populate_links_tree(self):
        if not hasattr(self, "links_root"):
            return
        self.links_root.takeChildren()
        for link in self._saved_links(self.remote):
            child = QTreeWidgetItem([link.get("name") or "Shared folder"])
            child.setIcon(0, icons.folder_icon())
            child.setData(0, Qt.ItemDataRole.UserRole,
                          ("link", link.get("name", ""), link.get("id", ""), link.get("key", "")))
            self.links_root.addChild(child)
        if self.links_root.childCount():
            self.links_root.setExpanded(True)

    def load_shared_sidebar(self, remote: str):
        if self.shared_loading or remote != self.remote:
            return
        self.shared_loading = True
        generation = self.tree_generation
        start_token = self.shared_next_token
        def page(value):
            if remote != self.remote or generation != self.tree_generation:
                return
            batch, next_token = value
            self.shared_root.extend(batch)
            self.shared_next_token = next_token
            self.populate_shared_tree(self.shared_root)
            if self.shared and not self.remote_path:
                if self.owner_filter is None:
                    groups = sorted({e.owner for e in self.shared_root}, key=str.casefold)
                    self.cloud.show_entries([Entry(name, "", True) for name in groups], group=True)
                else:
                    self.show_owner_group(self.owner_filter)
            self.set_status(f"Loaded {len(self.shared_root)} shared items" +
                            (" · loading more…" if next_token else ""))
        def done(_entries):
            if remote == self.remote and generation == self.tree_generation:
                self.shared_loading = False
                if self.shared_next_token:
                    self.set_status(f"{len(self.shared_root)} shared items loaded · more will load after Google quota resets")
                    QTimer.singleShot(65000, lambda: self.load_shared_sidebar(remote) if not self.closed else None)
        def failed(message):
            if remote == self.remote and generation == self.tree_generation:
                self.shared_loading = False
                if not self.shared_root:
                    self.shared_tree_root.takeChildren()
                    self.shared_tree_root.addChild(QTreeWidgetItem([f"Unavailable: {message[:55]}"]))
                self.set_status(f"Shared items: {message}")
                if "quota" in message.lower():
                    QTimer.singleShot(65000, lambda: self.load_shared_sidebar(remote) if not self.closed else None)
        self.run_async_progress(
            lambda emit: GoogleDriveAPI(self.rclone, remote).list_files(
                page_token=start_token, on_page=lambda batch, token: emit((batch, token))),
            page, done, context="Shared sidebar", on_error=failed)

    def shared_tree_clicked(self, item: QTreeWidgetItem, _column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind, value = data[:2]
        if kind == "drive":
            self.set_view(False)
        elif kind == "shared":
            self.set_view(True)
        elif kind == "owner":
            if not self.shared:
                self.shared = True
                self.link_folder_id = ""
                self.link_resource_key = ""
                self.update_buttons()
            self.remote_request += 1
            self.remote_path = ""
            self.shared_folder_id = ""
            self.shared_folder_key = ""
            self.folder_history = []
            self.show_owner_group(value)
        elif kind == "folder":
            self.shared = True
            self.link_folder_id = ""
            self.link_resource_key = ""
            self.owner_filter = None
            self.remote_path = value
            self.shared_folder_id = data[2]
            self.shared_folder_key = data[3]
            self.folder_history = []
            self.load_remote()
        elif kind == "link":
            self.open_saved_link(data[2], data[3])

    def open_saved_link(self, folder_id: str, resource_key: str):
        self.link_folder_id = folder_id
        self.link_resource_key = resource_key
        self.shared_folder_id = folder_id
        self.shared_folder_key = resource_key
        self.shared = False
        self.owner_filter = None
        self.remote_path = ""
        self.folder_history = []
        self.cloud.show_entries([])
        self.update_buttons()
        self.load_remote()

    def shared_tree_expanded(self, item: QTreeWidgetItem):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != "folder" or item.data(0, Qt.ItemDataRole.UserRole + 1):
            return
        path, folder_id, key = data[1:4]
        generation = self.tree_generation
        folder_generation = self.folder_tree_generation
        remote = self.remote
        item.setData(0, Qt.ItemDataRole.UserRole + 1, True)
        def done(entries):
            if (generation != self.tree_generation or folder_generation != self.folder_tree_generation
                    or remote != self.remote):
                return
            item.takeChildren()
            for entry in entries:
                if entry.is_dir:
                    child = QTreeWidgetItem([entry.name])
                    child.setIcon(0, icons.folder_icon())
                    child.setData(0, Qt.ItemDataRole.UserRole,
                                  ("folder", entry.path, entry.id, entry.resource_key))
                    child.addChild(QTreeWidgetItem(["Loading…"]))
                    item.addChild(child)
        def failed(message):
            if (generation != self.tree_generation or folder_generation != self.folder_tree_generation
                    or remote != self.remote):
                return
            item.takeChildren()
            item.addChild(QTreeWidgetItem([f"Unavailable: {message[:80]}"]))
            item.setData(0, Qt.ItemDataRole.UserRole + 1, False)
        self.run_async(lambda: GoogleDriveAPI(self.rclone, remote).list_files(
            folder_id=folder_id, resource_key=key, prefix=path), done,
                       context="Shared folders", on_error=failed)

    def shared_tree_menu(self, point):
        item = self.cloud.tree.itemAt(point)
        data = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        if data and data[0] == "link":
            menu = QMenu(self)
            menu.addAction("Open", lambda: self.open_saved_link(data[2], data[3]))
            menu.addAction("Remove from Opened links", lambda: self.remove_saved_link(data[2]))
            menu.exec(self.cloud.tree.viewport().mapToGlobal(point))
            return
        if not data or data[0] != "folder":
            return
        if not self.shared:
            self.shared_tree_clicked(item, 0)
        path = data[1]
        entry = next((value for value in self.shared_root if value.path == path),
                     Entry(item.text(0), path, True, id=data[2], resource_key=data[3]))
        menu = QMenu(self)
        menu.addAction("Open", lambda: self.shared_tree_clicked(item, 0))
        menu.addAction("Calculate size", lambda: self.calculate_size(self.cloud, entry))
        menu.addAction("Download to PC", lambda: self.start_transfer(False, entries=[entry]))
        menu.addAction("Properties", lambda: self.show_properties(self.cloud, entry))
        if entry.id:
            menu.addAction("Open in browser", lambda: self.open_in_browser(entry))
        menu.exec(self.cloud.tree.viewport().mapToGlobal(point))

    def remote_up(self):
        if (self.shared or self.link_folder_id) and self.folder_history:
            self.remote_path, self.shared_folder_id, self.shared_folder_key, self.owner_filter = self.folder_history.pop()
        elif self.shared and self.remote_path:
            self.remote_path = ""
            self.shared_folder_id = ""
            self.shared_folder_key = ""
        elif self.remote_path:
            self.remote_path = self.remote_path.rpartition("/")[0]
        elif self.owner_filter is not None:
            self.owner_filter = None
        self.load_remote()

    def remote_open(self, row: int, _col: int):
        if row >= len(self.cloud.entries):
            return
        entry = self.cloud.entries[row]
        if not entry.is_dir:
            return
        if self.shared and self.owner_filter is None and not self.remote_path:
            self.show_owner_group(entry.path if entry.path == ALL_SHARED else entry.name)
        else:
            if self.shared or self.link_folder_id:
                self.folder_history.append((self.remote_path, self.shared_folder_id,
                                            self.shared_folder_key, self.owner_filter))
                self.shared_folder_id = entry.id
                self.shared_folder_key = entry.resource_key
            self.remote_path = entry.path
            self.load_remote()

    def pc_drop(self, side: str, entries: list[Entry], target: Entry | None):
        if side != "cloud":
            return
        folder = Path(target.path) if target else self.local_path
        self.start_transfer(False, entries=entries, local_folder=folder)

    def cloud_drop(self, side: str, entries: list[Entry], target: Entry | None):
        if side not in ("pc", "explorer"):
            return
        if self.shared and not (self.shared_folder_id or target and target.id):
            self.set_status("Open a shared folder before uploading.")
            return
        folder = target.path if target else self.remote_path
        self.start_transfer(True, entries=entries, remote_folder=folder)

    def file_menu(self, pane: FilePane, point):
        table = pane.table
        row = table.rowAt(point.y())
        entry = pane.entries[row] if 0 <= row < len(pane.entries) else None
        if entry and row not in {item.row() for item in table.selectedItems()}:
            table.clearSelection()
            table.selectRow(row)
        menu = QMenu(self)
        if entry:
            menu.addAction("Open", lambda: self.open_entry(pane, entry, row))
            menu.addAction("Calculate size", lambda: self.calculate_size(pane, entry))
            menu.addAction("Properties", lambda: self.show_properties(pane, entry))
            menu.addSeparator()
            menu.addAction("Upload to Drive" if pane.local else "Download to PC",
                           lambda: self.start_transfer(pane.local, entries=table.selected_entries()))
            if not pane.local and entry.id:
                menu.addAction("Open in browser", lambda: self.open_in_browser(entry))
            if not self.shared or pane.local or self.shared_folder_id:
                menu.addSeparator()
                menu.addAction("Rename", lambda: self.rename_entry(pane, entry))
                menu.addAction("Delete", lambda: self.delete_entry(pane, entry))
        if pane.local or not self.shared or self.shared_folder_id:
            menu.addSeparator()
            menu.addAction("New folder", lambda: self.new_folder(pane, entry if entry and entry.is_dir else None))
        menu.exec(table.viewport().mapToGlobal(point))

    def open_entry(self, pane: FilePane, entry: Entry, row: int):
        if entry.is_dir:
            if pane.local:
                self.local_open(row, 0)
            else:
                self.remote_open(row, 0)
        elif pane.local:
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(entry.path))
            except OSError as exc:
                self.set_status(f"Open: {exc}")
        elif entry.id:
            self.open_in_browser(entry)
        else:
            self.set_status("This file has no browser link. Use Download to PC.")

    def calculate_size(self, pane: FilePane, entry: Entry):
        self.set_status(f"Calculating size of {entry.name}…")
        if pane.local:
            def get_size():
                path = Path(entry.path)
                if path.is_file():
                    return path.stat().st_size, 1
                total = count = 0
                for folder, _dirs, files in os.walk(path):
                    for name in files:
                        try:
                            total += (Path(folder) / name).stat().st_size
                            count += 1
                        except OSError:
                            continue
                return total, count
        else:
            remote, path, shared = self.remote, entry.path, self.shared
            folder_id, resource_key = self.link_folder_id, self.link_resource_key
            if shared or folder_id:
                get_size = lambda: GoogleDriveAPI(self.rclone, remote).calculate_size(entry)
            else:
                get_size = lambda: self.rclone.size(remote, path)
        def done(result):
            size, count = result
            message = f"{entry.name}: {size_text(size)} across {count:,} file{'s' if count != 1 else ''}"
            self.set_status(message)
            QMessageBox.information(self, "Calculated size", message)
        self.run_async(get_size, done, context="Calculate size")

    def show_properties(self, pane: FilePane, entry: Entry):
        details = [f"Name: {entry.name}", f"Location: {entry.path}",
                   f"Type: {'Folder' if entry.is_dir else 'File'}"]
        if entry.size >= 0:
            details.append(f"Size: {size_text(entry.size)}")
        if entry.modified:
            details.append(f"Modified: {entry.modified}")
        if entry.owner:
            details.append(f"Owner: {entry.owner}")
        if entry.id and not pane.local:
            details.append(f"Drive ID: {entry.id}")
        QMessageBox.information(self, "Properties", "\n".join(details))

    def open_in_browser(self, entry: Entry):
        url = (f"https://drive.google.com/drive/folders/{entry.id}" if entry.is_dir else
               f"https://drive.google.com/file/d/{entry.id}/view")
        QDesktopServices.openUrl(QUrl(url))

    @staticmethod
    def valid_name(name: str) -> bool:
        return bool(name) and name not in (".", "..") and not any(c in name for c in "/\\:*?\"<>|")

    def new_folder(self, pane: FilePane, parent: Entry | None):
        name, accepted = QInputDialog.getText(self, "New folder", "Folder name:")
        name = name.strip()
        if not accepted:
            return
        if not self.valid_name(name):
            QMessageBox.warning(self, "Invalid name", "Choose a folder name without path characters.")
            return
        if pane.local:
            folder = (Path(parent.path) if parent else self.local_path) / name
            operation = lambda: folder.mkdir()
            refresh = self.load_local
        else:
            if self.shared or self.link_folder_id:
                parent_id = parent.id if parent else self.shared_folder_id
                parent_key = parent.resource_key if parent else self.shared_folder_key
                operation = lambda: GoogleDriveAPI(self.rclone, self.remote).create_folder(name, parent_id, parent_key)
            else:
                path = "/".join(part for part in ((parent.path if parent else self.remote_path), name) if part)
                operation = lambda: self.rclone.mutate("mkdir", self.remote, path)
            refresh = self.load_remote
        self.run_async(operation, lambda _result: refresh(), context="New folder")

    def rename_entry(self, pane: FilePane, entry: Entry):
        name, accepted = QInputDialog.getText(self, "Rename", "New name:", text=entry.name)
        name = name.strip()
        if not accepted or name == entry.name:
            return
        if not self.valid_name(name):
            QMessageBox.warning(self, "Invalid name", "Choose a name without path characters.")
            return
        if pane.local:
            source = Path(entry.path)
            target = source.with_name(name)
            if target.exists():
                QMessageBox.warning(self, "Rename", "An item with that name already exists.")
                return
            operation = lambda: source.rename(target)
            refresh = self.load_local
        else:
            parent = entry.path.rpartition("/")[0]
            target = f"{parent}/{name}" if parent else name
            def operation():
                if self.shared or self.link_folder_id:
                    api = GoogleDriveAPI(self.rclone, self.remote)
                    siblings = api.list_files(folder_id=self.shared_folder_id, resource_key=self.shared_folder_key)
                else:
                    siblings = self.rclone.list(self.remote, parent)
                if any(item.name.casefold() == name.casefold() for item in siblings):
                    raise RcloneError("An item with that name already exists.")
                if self.shared or self.link_folder_id:
                    api.rename(entry, name)
                else:
                    self.rclone.mutate("moveto", self.remote, entry.path, destination=target)
            refresh = self.load_remote
        self.run_async(operation, lambda _result: refresh(), context="Rename")

    def delete_entry(self, pane: FilePane, entry: Entry):
        detail = " and everything inside it" if entry.is_dir else ""
        answer = QMessageBox.question(self, "Delete item", f"Delete {entry.name}{detail}?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        if pane.local:
            path = Path(entry.path)
            operation = (lambda: shutil.rmtree(path)) if entry.is_dir else (lambda: path.unlink())
            refresh = self.load_local
        else:
            if self.shared or self.link_folder_id:
                operation = lambda: GoogleDriveAPI(self.rclone, self.remote).delete(entry)
            else:
                operation = lambda: self.rclone.mutate("purge" if entry.is_dir else "deletefile", self.remote,
                                                       entry.path)
            refresh = self.load_remote
        self.run_async(operation, lambda _result: refresh(), context="Delete")

    def _find_conflicts(self, selected: list[Entry], upload: bool, dest_remote: str,
                        dest_local: Path) -> list[str]:
        """Top-level names that already exist at the destination (best-effort, no extra I/O)."""
        if upload:
            if dest_remote == self.remote_path:
                existing = {entry.name.casefold() for entry in self.cloud.entries}
                return [entry.name for entry in selected if entry.name.casefold() in existing]
            return []
        return [entry.name for entry in selected if (Path(dest_local) / entry.name).exists()]

    def _ask_conflict(self, names: list[str], upload: bool) -> str:
        dialog = QDialog(self)
        dialog.setWindowTitle("Items already exist")
        dialog.setMinimumWidth(430)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        header = QLabel(f"{len(names)} item{'s' if len(names) != 1 else ''} already exist at the "
                        f"{'destination folder on Drive' if upload else 'destination folder'}.")
        header.setWordWrap(True)
        layout.addWidget(header)
        listw = QListWidget()
        for name in names[:12]:
            listw.addItem(QListWidgetItem(name))
        if len(names) > 12:
            listw.addItem(QListWidgetItem(f"…and {len(names) - 12} more"))
        listw.setMaximumHeight(150)
        layout.addWidget(listw)
        note = QLabel("Choose what to do — this applies to all of them (including matching files inside folders).")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        choice = {"value": "cancel"}
        def pick(value):
            choice["value"] = value
            dialog.accept()
        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(lambda: pick("cancel"))
        skip = QPushButton("Skip existing")
        skip.setToolTip("Keep the existing items; copy only new ones")
        skip.clicked.connect(lambda: pick("skip"))
        replace = QPushButton("Replace")
        replace.setObjectName("primary")
        replace.setToolTip("Overwrite the existing items with the copied versions")
        replace.clicked.connect(lambda: pick("replace"))
        row.addWidget(cancel)
        row.addStretch()
        row.addWidget(skip)
        row.addWidget(replace)
        layout.addLayout(row)
        dialog.exec()
        return choice["value"]

    def start_transfer(self, upload: bool, *, entries: list[Entry] | None = None,
                       remote_folder: str | None = None, local_folder: Path | None = None):
        if not self.rclone or not self.remote:
            return
        selected = entries if entries is not None else (self.pc.selected() if upload else self.cloud.selected())
        if not selected:
            self.set_status("Select one or more items to transfer.")
            return
        if not upload and self.shared and self.owner_filter is None and not self.remote_path:
            self.set_status("Open a person to select shared files or folders.")
            return
        destination_remote = remote_folder if remote_folder is not None else self.remote_path
        destination_local = local_folder if local_folder is not None else self.local_path
        # Keep the direct API path for uploads, where it is needed for shared
        # folder permissions. Downloads are faster and more resilient through
        # rclone, which can run parallel transfers and resume transient failures.
        use_api = (self.shared or bool(self.link_folder_id)) and upload
        parent_id, parent_key = self.shared_folder_id, self.shared_folder_key
        if use_api and upload and destination_remote != self.remote_path:
            target = next((item for item in self.cloud.entries if item.path == destination_remote and item.is_dir), None)
            if target:
                parent_id, parent_key = target.id, target.resource_key
        if use_api and upload and not parent_id:
            self.set_status("Open a shared folder before uploading.")
            return
        # Windows-style conflict handling for items that already exist at the destination.
        conflicts = self._find_conflicts(selected, upload, destination_remote, destination_local)
        if conflicts:
            choice = self._ask_conflict(conflicts, upload)
            if choice == "cancel":
                self.set_status("Transfer cancelled.")
                return
            replace = choice == "replace"
        else:
            replace = False
        for entry in selected:
            if use_api:
                worker = ApiTransferWorker(self.rclone, self.remote, entry, upload=upload,
                                           parent_id=parent_id, parent_key=parent_key,
                                           local_folder=destination_local, replace=replace)
            else:
                args = transfer_args(entry, self.remote, destination_remote, destination_local,
                                     upload=upload, shared=self.shared, replace=replace,
                                     folder_id=self.link_folder_id,
                                     resource_key=self.link_resource_key)
                args += self._extra_transfer_flags()
                worker = TransferWorker(self.rclone_path, args)
            label = f"{'Uploading' if upload else 'Downloading'} {entry.name}"
            source = entry.path if upload else f"{self.account_display_name()}:/{entry.path}"
            destination = (f"{self.account_display_name()}:/{destination_remote}/{entry.name}" if upload else
                           str(destination_local / entry.name))
            self._add_transfer_row(worker, operation="Upload" if upload else "Download",
                                   upload=upload, source=source, destination=destination,
                                   is_dir=entry.is_dir, total=entry.size, label=label)
        self.refresh_transfer_times()
        self.set_status(f"Started {len(selected)} transfer{'s' if len(selected) != 1 else ''}…")

    def _add_transfer_row(self, worker, *, operation: str, upload: bool, source: str,
                          destination: str, is_dir: bool, total: int, label: str):
        self.transfer_workers.append(worker)
        item = QTreeWidgetItem([operation, source, destination, "Starting",
                                size_text(total) if total >= 0 else "—", "", "—", "—", ""])
        item.setIcon(0, icons.folder_icon() if is_dir else icons.file_icon())
        for column in (1, 2, 4, 6, 7):
            item.setForeground(column, QColor("#73829a"))
        self.transfers.addTopLevelItem(item)
        bar = self._new_bar(indeterminate=True)
        self.transfers.setItemWidget(item, 5, bar)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("tinycancel")
        cancel.clicked.connect(worker.cancel)
        self.transfers.setItemWidget(item, 8, cancel)
        self.transfer_items[worker] = {
            "item": item, "bar": bar, "cancel": cancel, "start": time.monotonic(),
            "is_dir": is_dir, "children": {}, "eta": "—", "speed": "—", "name": label,
            "upload": upload, "done": 0, "total": max(0, total), "speed_bps": 0.0}
        worker.signals.progress.connect(lambda event, w=worker: self.transfer_progress(w, event))
        worker.signals.done.connect(lambda ok, msg, w=worker, name=label: self.transfer_done(w, name, ok, msg))
        self.pool.start(worker)

    def _extra_transfer_flags(self) -> list[str]:
        flags: list[str] = []
        options = self.transfer_opts
        if options.get("bwlimit"):
            flags += ["--bwlimit", str(options["bwlimit"])]
        if str(options.get("transfers", "")).isdigit():
            flags += ["--transfers", str(options["transfers"])]
        if str(options.get("checkers", "")).isdigit():
            flags += ["--checkers", str(options["checkers"])]
        for line in str(options.get("excludes", "")).replace(",", "\n").splitlines():
            if line.strip():
                flags += ["--exclude", line.strip()]
        for line in str(options.get("includes", "")).replace(",", "\n").splitlines():
            if line.strip():
                flags += ["--include", line.strip()]
        return flags

    @staticmethod
    def _new_bar(*, indeterminate: bool = False) -> QProgressBar:
        bar = QProgressBar()
        if indeterminate:
            bar.setRange(0, 0)
        else:
            bar.setRange(0, 100)
            bar.setValue(0)
        bar.setTextVisible(True)
        bar.setFormat("%p%")
        return bar

    @staticmethod
    def _mark_bar(bar: QProgressBar, state: str):
        bar.setProperty("state", state)
        bar.style().unpolish(bar)
        bar.style().polish(bar)

    def _child_row(self, state: dict, name: str) -> dict:
        child = state["children"].get(name)
        if child:
            return child
        item = QTreeWidgetItem(["", name, "", "Waiting", "—", "", "—", "—", ""])
        item.setIcon(1, icons.file_icon())
        item.setForeground(1, QColor("#5c6b83"))
        for column in (3, 4, 6, 7):
            item.setForeground(column, QColor("#8a97ab"))
        state["item"].addChild(item)
        bar = self._new_bar()
        self.transfers.setItemWidget(item, 5, bar)
        child = {"item": item, "bar": bar}
        state["children"][name] = child
        return child

    def transfer_progress(self, worker, event: dict):
        state = self.transfer_items.get(worker)
        if not state or not isinstance(event, dict):
            return
        if event.get("kind") == "file_done":
            if state["is_dir"]:
                child = self._child_row(state, event["name"])
                child["bar"].setValue(100)
                self._mark_bar(child["bar"], "done")
                child["item"].setText(3, "Done")
                child["item"].setText(6, "—")
                child["item"].setText(7, "—")
            return
        if event.get("kind") != "stats":
            return
        overall = event["overall"]
        bar = state["bar"]
        if overall["total"] > 0:
            bar.setRange(0, 100)
            bar.setValue(overall["percent"])
        item = state["item"]
        if overall["total"] > 0:
            item.setText(4, f"{size_text(overall['done'])} / {size_text(overall['total'])}")
        elif overall["done"] > 0:
            item.setText(4, size_text(overall["done"]))
        item.setText(6, speed_text(overall["speed"]))
        state["done"] = overall["done"]
        if overall["total"] > 0:
            state["total"] = overall["total"]
        state["speed_bps"] = overall["speed"]
        files_total = overall.get("files_total") or 0
        if state["is_dir"] and files_total:
            item.setText(3, f"Transferring · {overall['files_done']}/{files_total} files")
        else:
            item.setText(3, "Transferring")
        state["eta"] = eta_text(overall.get("eta"))
        for file in event.get("transferring", []):
            if not state["is_dir"] or not file["name"]:
                continue
            child = self._child_row(state, file["name"])
            if child["item"].text(3) == "Done":
                continue
            child["bar"].setValue(file["percent"])
            child["item"].setText(3, "Transferring")
            if file["total"] > 0:
                child["item"].setText(4, f"{size_text(file['done'])} / {size_text(file['total'])}")
            child["item"].setText(6, speed_text(file["speed"]))
            child["item"].setText(7, eta_text(file.get("eta")))
        self.refresh_transfer_times()

    def transfer_done(self, worker, label: str, ok: bool, message: str):
        state = self.transfer_items.pop(worker, None)
        if state:
            item = state["item"]
            item.setText(3, "Complete" if ok else message[:80])
            bar = state["bar"]
            bar.setRange(0, 100)
            if ok:
                bar.setValue(100)
                self._mark_bar(bar, "done")
                for child in state["children"].values():
                    child["bar"].setValue(100)
                    self._mark_bar(child["bar"], "done")
                    child["item"].setText(3, "Done")
            else:
                self._mark_bar(bar, "failed")
                item.setForeground(3, QColor("#bd3e44"))
                if message != "Cancelled":
                    QMessageBox.warning(self, "Transfer failed", f"{label}\n\n{message}")
            item.setText(6, "—")
            cancel = state.get("cancel")
            if cancel is not None:
                cancel.setEnabled(False)
                cancel.setText("Done" if ok else "—")
            elapsed = self.elapsed_text(int(time.monotonic() - state["start"]))
            item.setText(7, elapsed)
        if worker in self.transfer_workers:
            self.transfer_workers.remove(worker)
        self.set_status(f"{label}: {message}")
        self.refresh_transfer_times()
        if not self.transfer_workers:
            self.load_local()
            self.load_remote()

    def clear_finished_transfers(self):
        active_items = [state["item"] for state in self.transfer_items.values()]
        for index in range(self.transfers.topLevelItemCount() - 1, -1, -1):
            item = self.transfers.topLevelItem(index)
            if not any(item is active for active in active_items):
                self.transfers.takeTopLevelItem(index)
        self.refresh_transfer_times()

    def clear_failed_transfers(self):
        active_items = [state["item"] for state in self.transfer_items.values()]
        for index in range(self.transfers.topLevelItemCount() - 1, -1, -1):
            item = self.transfers.topLevelItem(index)
            done = not any(item is active for active in active_items)
            if done and not item.text(3).startswith(("Complete", "Done")):
                self.transfers.takeTopLevelItem(index)
        self.refresh_transfer_times()

    def _worker_for_item(self, item) -> object | None:
        for worker, state in self.transfer_items.items():
            if state["item"] is item:
                return worker
        return None

    def transfer_menu(self, point):
        clicked = self.transfers.itemAt(point)
        top = clicked.parent() if (clicked and clicked.parent()) else clicked
        worker = self._worker_for_item(top) if top else None
        menu = QMenu(self)
        if worker is not None:
            menu.addAction("Stop / cancel", lambda: worker.cancel())
            menu.addSeparator()
        elif top is not None:
            menu.addAction("Open destination folder", lambda: self._open_transfer_dest(top))
            menu.addAction("Remove from list", lambda: self._remove_transfer_item(top))
            menu.addSeparator()
        menu.addAction("Cancel all active", self.cancel_all_transfers)
        menu.addAction("Clear completed", self.clear_finished_transfers)
        menu.addAction("Clear failed / cancelled", self.clear_failed_transfers)
        menu.exec(self.transfers.viewport().mapToGlobal(point))

    def cancel_all_transfers(self):
        for worker in list(self.transfer_workers):
            worker.cancel()

    def _remove_transfer_item(self, item):
        index = self.transfers.indexOfTopLevelItem(item)
        if index >= 0:
            self.transfers.takeTopLevelItem(index)
        self.refresh_transfer_times()

    def _open_transfer_dest(self, item):
        target = Path(item.text(2))
        folder = target if target.is_dir() else target.parent
        if folder.exists():
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            except OSError as exc:
                self.set_status(f"Open: {exc}")
        else:
            self.set_status("This destination is on the cloud.")

    @staticmethod
    def elapsed_text(seconds: int) -> str:
        return f"{seconds // 3600:d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"

    def refresh_transfer_times(self):
        active = len(self.transfer_workers)
        total = self.transfers.topLevelItemCount()
        if not total:
            self.transfer_summary.setText("No transfers yet")
        else:
            self.transfer_summary.setText(f"{active} active · {total} total")
        for state in self.transfer_items.values():
            elapsed = self.elapsed_text(int(time.monotonic() - state["start"]))
            state["item"].setText(7, f"ETA {state['eta']} · {elapsed}")
        self.update_status_bar()

    def update_status_bar(self):
        states = list(self.transfer_items.values())
        if not states:
            self.total_bar.hide()
            self.total_label.setText("")
            self.download_label.setText("↓ —")
            self.upload_label.setText("↑ —")
            return
        done = sum(state["done"] for state in states)
        grand = sum(state["total"] for state in states)
        up = sum(state["speed_bps"] for state in states if state["upload"])
        down = sum(state["speed_bps"] for state in states if not state["upload"])
        self.download_label.setText(f"↓ {speed_text(down)}")
        self.upload_label.setText(f"↑ {speed_text(up)}")
        if grand > 0:
            self.total_bar.show()
            self.total_bar.setValue(int(done * 100 / grand))
            self.total_label.setText(f"Total {size_text(done)} / {size_text(grand)}")
        else:
            self.total_bar.hide()
            self.total_label.setText(f"Total {size_text(done)}" if done else "")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    if "--smoke-test" in sys.argv:
        QLabel("Qt ready")
        return
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
