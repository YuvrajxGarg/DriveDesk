"""Crisp painted icons (no external assets) plus real Windows shell icons for local files.

All QIcon builders are cached and must be called after a QApplication exists.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import QFileInfo, QPointF, QRectF, Qt
from PyQt6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient, QRadialGradient,
                         QPainter, QPainterPath, QPen, QPixmap, QPolygonF)
from PyQt6.QtWidgets import QFileIconProvider

_SIZE = 44
_provider: QFileIconProvider | None = None
_file_cache: dict[str, QIcon] = {}

BACKEND_COLOR = {
    "dropbox": "#0061FF", "onedrive": "#0364B8", "box": "#0075C9", "pcloud": "#1BA0E2",
    "googlephotos": "#4285F4", "s3": "#E2711D", "b2": "#E21E29", "sftp": "#5C6470",
    "mega": "#D9272E", "webdav": "#3B7A57", "yandex": "#FF3333",
}
BACKEND_LETTER = {
    "dropbox": "D", "onedrive": "O", "box": "B", "pcloud": "p", "googlephotos": "P",
    "s3": "S", "b2": "b", "sftp": "S", "mega": "M", "webdav": "W", "yandex": "Y",
}


def _canvas() -> tuple[QPixmap, QPainter, float]:
    pixmap = QPixmap(_SIZE, _SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    return pixmap, painter, float(_SIZE)


@lru_cache(maxsize=None)
def folder_icon() -> QIcon:
    pixmap, p, s = _canvas()
    p.setPen(Qt.PenStyle.NoPen)
    # Back sheet / tab.
    p.setBrush(QColor("#E4A93C"))
    p.drawRoundedRect(QRectF(s * 0.11, s * 0.24, s * 0.44, s * 0.30), s * 0.06, s * 0.06)
    # Folder body.
    p.setBrush(QColor("#F4C24A"))
    p.drawRoundedRect(QRectF(s * 0.10, s * 0.34, s * 0.80, s * 0.42), s * 0.06, s * 0.06)
    # Top highlight.
    p.setBrush(QColor("#FBD879"))
    p.drawRoundedRect(QRectF(s * 0.10, s * 0.34, s * 0.80, s * 0.10), s * 0.05, s * 0.05)
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def file_icon() -> QIcon:
    pixmap, p, s = _canvas()
    p.setPen(Qt.PenStyle.NoPen)
    body = QPainterPath()
    body.moveTo(s * 0.24, s * 0.14)
    body.lineTo(s * 0.60, s * 0.14)
    body.lineTo(s * 0.78, s * 0.32)
    body.lineTo(s * 0.78, s * 0.86)
    body.lineTo(s * 0.24, s * 0.86)
    body.closeSubpath()
    p.setBrush(QColor("#EDEFF3"))
    p.drawPath(body)
    # Folded corner.
    corner = QPolygonF([QPointF(s * 0.60, s * 0.14), QPointF(s * 0.78, s * 0.32), QPointF(s * 0.60, s * 0.32)])
    p.setBrush(QColor("#C6CBD5"))
    p.drawPolygon(corner)
    # Text lines.
    p.setPen(QPen(QColor("#AEB4C0"), s * 0.035))
    for i in range(3):
        y = s * (0.48 + i * 0.11)
        p.drawLine(QPointF(s * 0.33, y), QPointF(s * 0.69, y))
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def drive_icon() -> QIcon:
    pixmap, p, s = _canvas()
    p.setPen(Qt.PenStyle.NoPen)
    top = QPointF(s * 0.5, s * 0.18)
    left = QPointF(s * 0.14, s * 0.82)
    right = QPointF(s * 0.86, s * 0.82)
    triangle = QPolygonF([top, left, right])
    path = QPainterPath()
    path.addPolygon(triangle)
    p.setClipPath(path)
    # Blue (left) → green (right) base.
    gradient = QLinearGradient(left, right)
    gradient.setColorAt(0.0, QColor("#2684FC"))
    gradient.setColorAt(1.0, QColor("#00AC47"))
    p.fillRect(QRectF(0, 0, s, s), QBrush(gradient))
    # Yellow upper wedge.
    p.setBrush(QColor("#FFC024"))
    wedge = QPolygonF([top, QPointF(s * 0.305, s * 0.505), QPointF(s * 0.695, s * 0.505)])
    p.drawPolygon(wedge)
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def backend_icon(kind: str) -> QIcon:
    if kind == "drive":
        return drive_icon()
    pixmap, p, s = _canvas()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(BACKEND_COLOR.get(kind, "#5B6470")))
    p.drawRoundedRect(QRectF(s * 0.13, s * 0.13, s * 0.74, s * 0.74), s * 0.20, s * 0.20)
    p.setPen(QColor("#FFFFFF"))
    font = QFont("Segoe UI", int(s * 0.4))
    font.setBold(True)
    p.setFont(font)
    letter = BACKEND_LETTER.get(kind, (kind[:1].upper() or "☁"))
    p.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, letter)
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def person_icon() -> QIcon:
    pixmap, p, s = _canvas()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#7EA6F2"))
    p.drawEllipse(QRectF(s * 0.34, s * 0.18, s * 0.32, s * 0.32))
    shoulders = QPainterPath()
    shoulders.addEllipse(QRectF(s * 0.20, s * 0.55, s * 0.60, s * 0.50))
    p.setClipRect(QRectF(0, 0, s, s * 0.86))
    p.drawPath(shoulders)
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def people_icon() -> QIcon:
    pixmap, p, s = _canvas()
    p.setPen(Qt.PenStyle.NoPen)
    p.setClipRect(QRectF(0, 0, s, s * 0.86))
    # Back person.
    p.setBrush(QColor("#4F6DA8"))
    p.drawEllipse(QRectF(s * 0.52, s * 0.22, s * 0.28, s * 0.28))
    p.drawPath(_blob(QRectF(s * 0.40, s * 0.55, s * 0.52, s * 0.46)))
    # Front person.
    p.setBrush(QColor("#7EA6F2"))
    p.drawEllipse(QRectF(s * 0.20, s * 0.24, s * 0.30, s * 0.30))
    p.drawPath(_blob(QRectF(s * 0.08, s * 0.58, s * 0.52, s * 0.46)))
    p.end()
    return QIcon(pixmap)


def _blob(rect: QRectF) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(rect)
    return path


_STROKE = "#C4C8D0"


def _stroke_pen(s: float, width: float = 0.09) -> QPen:
    pen = QPen(QColor(_STROKE), s * width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


@lru_cache(maxsize=None)
def up_icon() -> QIcon:
    pixmap, p, s = _canvas()
    p.setPen(_stroke_pen(s))
    p.drawLine(QPointF(s * 0.5, s * 0.30), QPointF(s * 0.5, s * 0.72))
    p.drawLine(QPointF(s * 0.5, s * 0.30), QPointF(s * 0.32, s * 0.48))
    p.drawLine(QPointF(s * 0.5, s * 0.30), QPointF(s * 0.68, s * 0.48))
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def refresh_icon() -> QIcon:
    pixmap, p, s = _canvas()
    c, r = s * 0.5, s * 0.24
    p.setPen(_stroke_pen(s))
    p.setBrush(Qt.BrushStyle.NoBrush)
    rect = QRectF(c - r, c - r, 2 * r, 2 * r)
    p.drawArc(rect, int(65 * 16), int(280 * 16))
    # Arrowhead at the open end (~65 degrees), pointing clockwise.
    a = math.radians(65)
    ex, ey = c + r * math.cos(a), c - r * math.sin(a)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(_STROKE))
    head = QPolygonF([QPointF(ex + s * 0.02, ey - s * 0.14), QPointF(ex + s * 0.16, ey + s * 0.02),
                      QPointF(ex - s * 0.10, ey + s * 0.03)])
    p.drawPolygon(head)
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def browse_icon() -> QIcon:
    pixmap, p, s = _canvas()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#E0A73A"))
    p.drawRoundedRect(QRectF(s * 0.12, s * 0.28, s * 0.62, s * 0.44), s * 0.05, s * 0.05)
    # Open front flap.
    flap = QPolygonF([QPointF(s * 0.20, s * 0.46), QPointF(s * 0.92, s * 0.46),
                      QPointF(s * 0.78, s * 0.74), QPointF(s * 0.06, s * 0.74)])
    p.setBrush(QColor("#F4C24A"))
    p.drawPolygon(flap)
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def link_icon() -> QIcon:
    pixmap, p, s = _canvas()
    pen = QPen(QColor("#7EA6F2"), s * 0.11)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(s * 0.14, s * 0.40, s * 0.40, s * 0.22), s * 0.11, s * 0.11)
    p.drawRoundedRect(QRectF(s * 0.46, s * 0.38, s * 0.40, s * 0.22), s * 0.11, s * 0.11)
    p.drawLine(QPointF(s * 0.40, s * 0.51), QPointF(s * 0.60, s * 0.49))
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def settings_icon() -> QIcon:
    pixmap, p, s = _canvas()
    p.setPen(QPen(QColor("#B8C1D4"), s * 0.095))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(s * 0.28, s * 0.28, s * 0.44, s * 0.44))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#B8C1D4"))
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        cx = s * 0.5 + math.cos(rad) * s * 0.35
        cy = s * 0.5 + math.sin(rad) * s * 0.35
        p.save()
        p.translate(cx, cy)
        p.rotate(angle)
        p.drawRoundedRect(QRectF(-s * 0.055, -s * 0.10, s * 0.11, s * 0.20), s * 0.035, s * 0.035)
        p.restore()
    p.setBrush(QColor("#252933"))
    p.drawEllipse(QRectF(s * 0.42, s * 0.42, s * 0.16, s * 0.16))
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def mount_icon() -> QIcon:
    pixmap, p, s = _canvas()
    p.setPen(QPen(QColor("#B8C1D4"), s * 0.08))
    p.setBrush(QColor("#3D4658"))
    p.drawRoundedRect(QRectF(s * 0.13, s * 0.24, s * 0.74, s * 0.52), s * 0.10, s * 0.10)
    p.setPen(QPen(QColor("#7EA6F2"), s * 0.08))
    p.drawLine(QPointF(s * 0.28, s * 0.40), QPointF(s * 0.72, s * 0.40))
    p.drawLine(QPointF(s * 0.28, s * 0.58), QPointF(s * 0.58, s * 0.58))
    p.setBrush(QColor("#7EA6F2"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(s * 0.66, s * 0.53, s * 0.12, s * 0.12))
    p.end()
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def toolbox_icon() -> QIcon:
    pixmap, p, s = _canvas()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#C8A35B"))
    p.drawRoundedRect(QRectF(s * 0.12, s * 0.34, s * 0.76, s * 0.48), s * 0.08, s * 0.08)
    p.setBrush(QColor("#E0BD6E"))
    p.drawRoundedRect(QRectF(s * 0.30, s * 0.20, s * 0.40, s * 0.22), s * 0.06, s * 0.06)
    p.setBrush(QColor("#5D4A2B"))
    p.drawRect(QRectF(s * 0.12, s * 0.48, s * 0.76, s * 0.09))
    p.drawRoundedRect(QRectF(s * 0.43, s * 0.44, s * 0.14, s * 0.17), s * 0.03, s * 0.03)
    p.end()
    return QIcon(pixmap)


def app_logo_pixmap(size: int = 512) -> QPixmap:
    """The DriveDesk brand mark: a gradient tile with a cloud and up/down transfer arrows."""
    s = float(size)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    margin = s * 0.05
    tile = QRectF(margin, margin, s - 2 * margin, s - 2 * margin)
    radius = s * 0.225
    tile_path = QPainterPath()
    tile_path.addRoundedRect(tile, radius, radius)
    gradient = QLinearGradient(margin, margin, s - margin, s - margin)
    gradient.setColorAt(0.0, QColor("#3D5AF1"))
    gradient.setColorAt(0.55, QColor("#5B43E8"))
    gradient.setColorAt(1.0, QColor("#8A2BE2"))
    p.fillPath(tile_path, gradient)
    p.setClipPath(tile_path)
    sheen = QLinearGradient(0, margin, 0, s * 0.62)
    sheen.setColorAt(0.0, QColor(255, 255, 255, 48))
    sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(tile, QBrush(sheen))
    glow = QRadialGradient(s * 0.5, s * 0.9, s * 0.5)
    glow.setColorAt(0.0, QColor(0, 0, 0, 55))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.fillRect(tile, QBrush(glow))
    p.setClipping(False)
    # Cloud.
    cloud = QPainterPath()
    cloud.addEllipse(QRectF(s * 0.29, s * 0.40, s * 0.22, s * 0.22))
    cloud.addEllipse(QRectF(s * 0.41, s * 0.31, s * 0.26, s * 0.26))
    cloud.addEllipse(QRectF(s * 0.55, s * 0.40, s * 0.20, s * 0.20))
    cloud.addRoundedRect(QRectF(s * 0.30, s * 0.50, s * 0.44, s * 0.17), s * 0.085, s * 0.085)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawPath(cloud.simplified())
    # Up/down transfer arrows knocked into the cloud (green up, blue down).
    up = QPainterPath()
    ax = s * 0.445
    up.moveTo(ax, s * 0.42)
    up.lineTo(ax - s * 0.055, s * 0.50)
    up.lineTo(ax - s * 0.022, s * 0.50)
    up.lineTo(ax - s * 0.022, s * 0.60)
    up.lineTo(ax + s * 0.022, s * 0.60)
    up.lineTo(ax + s * 0.022, s * 0.50)
    up.lineTo(ax + s * 0.055, s * 0.50)
    up.closeSubpath()
    p.setBrush(QColor("#2FA45B"))
    p.drawPath(up)
    down = QPainterPath()
    bx = s * 0.56
    down.moveTo(bx, s * 0.60)
    down.lineTo(bx - s * 0.055, s * 0.52)
    down.lineTo(bx - s * 0.022, s * 0.52)
    down.lineTo(bx - s * 0.022, s * 0.42)
    down.lineTo(bx + s * 0.022, s * 0.42)
    down.lineTo(bx + s * 0.022, s * 0.52)
    down.lineTo(bx + s * 0.055, s * 0.52)
    down.closeSubpath()
    p.setBrush(QColor("#3B7CF0"))
    p.drawPath(down)
    p.end()
    return pixmap


@lru_cache(maxsize=None)
def app_logo() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(app_logo_pixmap(size))
    return icon


def _get_provider() -> QFileIconProvider:
    global _provider
    if _provider is None:
        _provider = QFileIconProvider()
    return _provider


def local_icon(path: str, is_dir: bool) -> QIcon:
    """Real Windows shell icon for a local file; a themed folder for directories."""
    if is_dir:
        return folder_icon()
    suffix = Path(path).suffix.lower()
    if suffix and suffix in _file_cache:
        return _file_cache[suffix]
    try:
        icon = _get_provider().icon(QFileInfo(path))
        if icon.isNull():
            icon = file_icon()
    except Exception:
        icon = file_icon()
    if suffix:
        _file_cache[suffix] = icon
    return icon


def entry_icon(path: str, is_dir: bool, *, local: bool) -> QIcon:
    if is_dir:
        return folder_icon()
    if local:
        return local_icon(path, is_dir)
    return file_icon()
