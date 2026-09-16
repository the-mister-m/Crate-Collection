"""Stem Splitter — entry point.

Wave 1 (shell): opens the three-pane window skeleton, detects the
compute device, and locates demucs and ffmpeg. Nothing runs or
separates yet. See docs/01-session-foundation-intake.md.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from core.device import detect_device
from core.locate import locate_demucs, locate_ffmpeg
from ui.main_window import MainWindow


def main() -> int:
    device = detect_device()
    ffmpeg = locate_ffmpeg()
    demucs = locate_demucs()

    print(f"device: {device}")
    print(f"ffmpeg: found={ffmpeg.found} path={ffmpeg.path}")
    print(f"demucs: found={demucs.found} path={demucs.path} importable={demucs.importable}")

    app = QApplication(sys.argv)
    window = MainWindow(device=device, ffmpeg_path=ffmpeg.path, demucs_found=demucs.found)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
