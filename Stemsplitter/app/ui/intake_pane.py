"""INTAKE pane — Wave 2 of Session 1.

Drop target for individual files or a whole folder. Each accepted file
becomes one checkable row (filename only — no preview, duration,
format badge, or sort; see docs/00-locked-spec.md NOT BUILDING and
docs/01-session-foundation-intake.md DRIFT). Only checked rows count
as "in": get_checked_paths() is the seam Session 2's run config dict
"files" field reads from (docs/00-locked-spec.md THE RUN CONFIG DICT).

Files are converted to wav on the way in via core/intake.py, using the
ffmpeg path Wave 1's core/locate.py already finds.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from core.intake import ingest

_ORIGINAL_NAME_ROLE = Qt.ItemDataRole.UserRole + 1


class IntakePane(QFrame):
    def __init__(self, ffmpeg_path: str | None) -> None:
        super().__init__()
        self._ffmpeg_path = ffmpeg_path
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)

        title = QLabel("INTAKE")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        hint = QLabel("Drop files or a folder here")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.list_widget, 1)

        controls = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn.clicked.connect(self._deselect_all)
        controls.addWidget(select_all_btn)
        controls.addWidget(deselect_all_btn)
        layout.addLayout(controls)

    # --- drag and drop ---------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasUrls():
            return
        dropped_paths = [
            url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()
        ]
        event.acceptProposedAction()
        self._ingest(dropped_paths)

    # --- ingest ------------------------------------------------------------

    def _ingest(self, dropped_paths: list[str]) -> None:
        if not self._ffmpeg_path:
            print("intake: ffmpeg not found, cannot convert dropped files")
            return
        for intake_file in ingest(dropped_paths, self._ffmpeg_path):
            item = QListWidgetItem(intake_file.display_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, intake_file.wav_path)
            item.setData(_ORIGINAL_NAME_ROLE, Path(intake_file.original_path).stem)
            self.list_widget.addItem(item)

    # --- select all / deselect all ------------------------------------------

    def _select_all(self) -> None:
        self._set_all_checked(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        self._set_all_checked(Qt.CheckState.Unchecked)

    def _set_all_checked(self, state: Qt.CheckState) -> None:
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(state)

    # --- seam: checked file list --------------------------------------------

    def get_checked_paths(self) -> list[str]:
        """Absolute wav paths for every checked row.

        This is the seam Session 2's run config dict "files" field
        reads from — see docs/00-locked-spec.md THE RUN CONFIG DICT.
        """
        paths: list[str] = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                paths.append(item.data(Qt.ItemDataRole.UserRole))
        return paths

    def get_checked_original_names(self) -> dict[str, str]:
        """Original filename stems for every checked row, keyed by wav
        path — same checked-row loop as get_checked_paths()."""
        names: dict[str, str] = {}
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                names[item.data(Qt.ItemDataRole.UserRole)] = item.data(_ORIGINAL_NAME_ROLE)
        return names
