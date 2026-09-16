"""OUTPUT pane — Wave C of Session 2.

Per node: a destination directory picker and a filename template field.
This pane does not own node lifecycle (add/remove/expand/collapse is
Wave A's node_list.py) — it only exposes add_node() / remove_node() /
get_output_config() so Session 4 can wire Wave A's add/remove actions
to this pane. See docs/02-session-panes.md WAVE C and the style note
for the card pattern this duplicates from Wave A's NodeCard (built in
parallel, not importable here).

Wired in Session 4 (docs/04-session-wire-verify.md CARRIED FROM SESSION 2):
this pane no longer numbers cards by live list position. That disagreed
with node_list.py, which numbers by fixed creation order — they drifted
apart once a middle node was removed. add_node() now takes the node_id
and title node_list.py already assigned at creation; main_window.py
wires NodeList.node_added/node_removed to keep this pane's cards in
step, id for id. A card's header is set once, at creation, and never
renumbered.

The suffix field is only the user's in "remove" mode. In "separate" mode
the mixer names each file after the stem it holds, so set_node_mode()
greys the field out and says so — main_window.py drives that off
NodeList.node_mode_changed.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

class OutputPane(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._nodes: list[QFrame] = []

        layout = QVBoxLayout(self)

        title = QLabel("OUTPUT")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        self._hint = QLabel("No outputs yet")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(8)
        self._container_layout.addStretch(1)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self._update_hint()

    # --- seam: node lifecycle -----------------------------------------------

    def add_node(self, node_id: str, title: str) -> QFrame:
        """Append one output card for the given node_id, titled to match
        its PARAMS card. Returns the card as the handle to use with
        remove_node() / get_output_config()."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card._node_id = node_id  # type: ignore[attr-defined]

        body = QVBoxLayout(card)
        body.setContentsMargins(8, 8, 8, 8)
        body.setSpacing(6)

        header = QLabel(title)
        header_font = header.font()
        header_font.setBold(True)
        header.setFont(header_font)
        body.addWidget(header)
        card._header_label = header  # type: ignore[attr-defined]

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        body.addWidget(separator)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        dest_row = QHBoxLayout()
        dest_row.setContentsMargins(0, 0, 0, 0)
        dest_row.setSpacing(6)
        dest_edit = QLineEdit()
        choose_btn = QPushButton("Choose…")
        choose_btn.clicked.connect(lambda: self._choose_destination(dest_edit))
        dest_row.addWidget(dest_edit, 1)
        dest_row.addWidget(choose_btn)
        form.addRow("Destination", dest_row)

        field1_edit = QLineEdit()
        field1_edit.setPlaceholderText("uses each file's own name if left blank")
        form.addRow("Filename", field1_edit)

        field2_edit = QLineEdit()
        field2_label = QLabel("Filename suffix (required)")
        form.addRow(field2_label, field2_edit)

        body.addLayout(form)

        card._dest_edit = dest_edit  # type: ignore[attr-defined]
        card._field1_edit = field1_edit  # type: ignore[attr-defined]
        card._field2_edit = field2_edit  # type: ignore[attr-defined]
        card._field2_label = field2_label  # type: ignore[attr-defined]

        self._container_layout.insertWidget(self._container_layout.count() - 1, card)
        self._nodes.append(card)
        self._update_hint()

        return card

    def remove_node(self, handle: QFrame) -> None:
        if handle not in self._nodes:
            return
        self._nodes.remove(handle)
        self._container_layout.removeWidget(handle)
        handle.deleteLater()
        self._update_hint()

    def set_node_mode(self, handle: QFrame, mode: str) -> None:
        """Reflect a node's mode in its suffix field.

        In "separate" mode the suffix is the stem name, chosen by the
        mixer — the field goes read-only and says so rather than
        disappearing, so the card keeps its shape when the mode flips
        back. Destination and Filename stay the user's in both modes.
        """
        if handle not in self._nodes:
            return
        separate = mode == "separate"
        edit = handle._field2_edit  # type: ignore[attr-defined]
        label = handle._field2_label  # type: ignore[attr-defined]
        edit.setEnabled(not separate)
        edit.setPlaceholderText("= the stem's name" if separate else "")
        label.setText("Filename suffix" if separate else "Filename suffix (required)")

    def get_output_config(self, handle: QFrame) -> dict:
        return {
            "output_dir": handle._dest_edit.text(),  # type: ignore[attr-defined]
            "filename_field1": handle._field1_edit.text(),  # type: ignore[attr-defined]
            "filename_field2": handle._field2_edit.text(),  # type: ignore[attr-defined]
        }

    # --- internal ------------------------------------------------------------

    def _choose_destination(self, dest_edit: QLineEdit) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Choose destination")
        if chosen:
            dest_edit.setText(chosen)

    def _update_hint(self) -> None:
        self._hint.setText("No outputs yet" if not self._nodes else "")
