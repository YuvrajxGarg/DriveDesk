"""Render the DriveDesk brand mark to assets/logo.png and assets/icon.ico.

Run:  python make_icon.py
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtWidgets import QApplication
from PIL import Image
import io

import icons


def main():
    app = QApplication([])  # noqa: F841 — needed for QPixmap painting
    assets = Path(__file__).parent / "assets"
    assets.mkdir(exist_ok=True)

    icons.app_logo_pixmap(1024).save(str(assets / "logo.png"))

    frames = []
    for size in (256, 128, 64, 48, 32, 24, 16):
        pixmap = icons.app_logo_pixmap(size)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        frames.append(Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGBA"))

    frames[0].save(str(assets / "icon.ico"), format="ICO",
                   sizes=[(f.width, f.height) for f in frames])
    print("Wrote", assets / "logo.png", "and", assets / "icon.ico")


if __name__ == "__main__":
    main()
