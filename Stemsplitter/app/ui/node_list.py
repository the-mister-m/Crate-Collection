"""PARAMS pane — Wave A of Session 2.

The node list chrome: scrollable column of NodeCard widgets, "Add Output"
to append a node, expand/collapse per node, remove a node, and "Print
Config" to print the run config dict assembled from all nodes.

NodeCard (this file) is the shared card shell also used by OUTPUT
(Wave C's output_pane.py, per docs/02-session-panes.md). This file owns
and builds the card's header row, disclosure, remove button, and
separator. The body below the separator is an empty QVBoxLayout seam
(``controls_seam``) that Wave B's NodeControls widget gets embedded into
during wiring — this file does not build or import NodeControls.

Session 2 runs three agents in true parallel against mock data; there is
no engine and nothing here calls demucs. See docs/00-locked-spec.md for
the run config dict schema and docs/02-session-panes.md for this
session's brief.

Seam assumption (see session report for the reconciliation note): a
NodeCard's Print Config contribution looks for a widget already sitting
in ``controls_seam`` and calls ``widget.get_node_config() -> dict`` on it
defensively (getattr/hasattr-guarded) if present. That is the method
name/signature this file assumes Wave B's NodeControls exposes.

Wired in Session 4 (docs/04-session-wire-verify.md): NodeCard now embeds
a real ui.node_controls.NodeControls instance into controls_seam at
creation, and NodeList emits node_added/node_removed so main_window.py
can keep OutputPane's cards in step — same node_id, same title, set once
at creation and never renumbered. This resolves the numbering mismatch
carried from Session 2 (see 00-locked-spec.md / 04-session-wire-verify.md
CARRIED FROM SESSION 2): node_list.py's convention — stable id, title
frozen at creation — is now the convention both panes use.
"""

from __future__ import annotations

from pprint import pprint

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.node_controls import NodeControls


class NodeCard(QFrame):
    """One node's card: header (disclosure, title, remove) + seam for
    Wave B's NodeControls body. Shared shell with OUTPUT's cards."""

    remove_requested = Signal(object)  # emits self
    # Relays this card's NodeControls.mode_changed upward with the node_id
    # attached, so OUTPUT's matching card can react. (node_id, mode)
    mode_changed = Signal(str, str)

    def __init__(self, node_id: str, title_text: str) -> None:
        super().__init__()
        self.node_id = node_id
        self.setFrameShape(QFrame.Shape.StyledPanel)

        body = QVBoxLayout(self)
        body.setContentsMargins(8, 8, 8, 8)
        body.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        self._disclosure = QToolButton()
        self._disclosure.setAutoRaise(True)
        self._disclosure.setCheckable(True)
        self._disclosure.setChecked(True)
        self._disclosure.setArrowType(Qt.ArrowType.DownArrow)
        self._disclosure.toggled.connect(self._on_toggled)
        header.addWidget(self._disclosure)

        self.title_label = QLabel(title_text)
        title_font = self.title_label.font()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header.addWidget(self.title_label)

        header.addStretch(1)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        header.addWidget(remove_btn)

        body.addLayout(header)

        # Collapsible content: separator + the seam for Wave B's widget.
        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(separator)

        # Seam: Wave B's NodeControls instance lives here. Wired in
        # Session 4 — embedded directly at creation, one per card.
        self.controls_seam = QVBoxLayout()
        content_layout.addLayout(self.controls_seam)

        self.controls = NodeControls()
        self.controls.mode_changed.connect(
            lambda mode: self.mode_changed.emit(self.node_id, mode)
        )
        self.controls_seam.addWidget(self.controls)

        body.addWidget(self._content)

    def _on_toggled(self, checked: bool) -> None:
        self._content.setVisible(checked)
        self._disclosure.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )

    def get_config(self) -> dict:
        """Best-effort node config slice for Print Config.

        Always includes "id". If a widget has been embedded into
        controls_seam (Wave B's NodeControls, wired in Session 4) and it
        exposes get_node_config() -> dict, its keys are merged in
        defensively.
        """
        config: dict = {"id": self.node_id}
        if self.controls_seam.count() > 0:
            item = self.controls_seam.itemAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None and hasattr(widget, "get_node_config"):
                try:
                    config.update(widget.get_node_config())
                except Exception as exc:  # defensive: Wave B's method is unverified
                    print(f"node_list: get_node_config() failed for {self.node_id}: {exc}")
        return config


class NodeList(QFrame):
    """PARAMS pane: scrollable node column + Add Output / Print Config."""

    # Wired in Session 4: lets main_window.py keep OutputPane's cards in
    # step with this pane's, using the same node_id and title — see the
    # numbering-fix note in this file's module docstring.
    node_added = Signal(str, str)  # node_id, title
    node_removed = Signal(str)  # node_id
    node_mode_changed = Signal(str, str)  # node_id, mode

    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)

        title = QLabel("PARAMS")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        hint = QLabel("No outputs yet — click Add Output")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(hint)

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

        button_row = QHBoxLayout()
        add_btn = QPushButton("Add Output")
        add_btn.clicked.connect(self._add_node)
        button_row.addWidget(add_btn)

        print_btn = QPushButton("Print Config")
        print_btn.clicked.connect(self._print_config)
        button_row.addWidget(print_btn)

        button_row.addStretch(1)
        layout.addLayout(button_row)

        self._nodes: list[NodeCard] = []
        self._next_number = 1

    # --- add / remove ------------------------------------------------------

    def _add_node(self) -> None:
        n = self._next_number
        self._next_number += 1
        card = NodeCard(node_id=f"node-{n}", title_text=f"Output {n}")
        card.remove_requested.connect(self._remove_node)
        card.mode_changed.connect(self.node_mode_changed)
        insert_at = self._container_layout.count() - 1  # before trailing stretch
        self._container_layout.insertWidget(insert_at, card)
        self._nodes.append(card)
        self.node_added.emit(card.node_id, card.title_label.text())

    def _remove_node(self, card: NodeCard) -> None:
        self._container_layout.removeWidget(card)
        card.setParent(None)
        card.deleteLater()
        if card in self._nodes:
            self._nodes.remove(card)
            self.node_removed.emit(card.node_id)

    # --- seam: card list, for Session 4's wiring -----------------------------

    def get_cards(self) -> list[NodeCard]:
        """Live node cards, creation order. Session 4 reads each card's
        get_config() off this list to assemble the run config dict."""
        return list(self._nodes)

    # --- seam: run config dict ----------------------------------------------

    def _print_config(self) -> None:
        """Prints the run config dict per docs/00-locked-spec.md's schema.

        device/jobs/files are mock placeholders in this session — Session 1's
        real device string and Intake's checked file list are wired in in
        docs/04-session-wire-verify.md, not here.
        """
        config = {
            "device": "cpu",  # mock — wired to Session 1's real device in Session 4
            "jobs": 1,  # mock
            "files": [],  # mock — wired to intake_pane.get_checked_paths() in Session 4
            "nodes": [card.get_config() for card in self._nodes],
        }
        pprint(config)
