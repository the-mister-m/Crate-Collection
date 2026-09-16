"""Main window: three-pane layout + Session 4 wiring.

Per docs/00-locked-spec.md: INTAKE | PARAMS | OUTPUT, left to right.
Session 1 built the shell and the real intake pane. Session 2 built
PARAMS (node_list.py + node_controls.py) and OUTPUT (output_pane.py)
against mock data. This file (docs/04-session-wire-verify.md) is where
the two halves join: PARAMS and OUTPUT node cards are kept in step by
id (see ui/node_list.py's and ui/output_pane.py's module docstrings —
CARRIED FROM SESSION 2 numbering fix), and the Run button assembles the
run config dict (docs/00-locked-spec.md THE RUN CONFIG DICT) and hands
it to engine/pipeline.py via ui/run_worker.py, off the UI thread.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.intake_pane import IntakePane
from ui.node_list import NodeList
from ui.output_pane import OutputPane
from ui.run_worker import RunWorker


class MainWindow(QMainWindow):
    def __init__(self, device: str, ffmpeg_path: str | None, demucs_found: bool) -> None:
        super().__init__()
        self.setWindowTitle("Stem Splitter")
        self.resize(1100, 650)

        self._device = device
        self._jobs = os.cpu_count() or 1  # run-level -j; CPU-only, ignored on gpu

        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)

        panes = QHBoxLayout()
        self.intake_pane = IntakePane(ffmpeg_path)
        self.params_pane = NodeList()
        self.output_pane = OutputPane()

        panes.addWidget(self.intake_pane, 1)
        panes.addWidget(self.params_pane, 1)
        panes.addWidget(self.output_pane, 1)
        outer.addLayout(panes, 1)

        # --- run bar: go action + progress/status -----------------------
        run_bar = QHBoxLayout()
        self._run_btn = QPushButton("Run")
        self._run_btn.clicked.connect(self._on_go)
        self._run_btn.setEnabled(demucs_found)
        run_bar.addWidget(self._run_btn)

        self._run_status_label = QLabel(
            "" if demucs_found else "demucs not found — cannot run"
        )
        run_bar.addWidget(self._run_status_label, 1)
        outer.addLayout(run_bar)

        # --- keep PARAMS and OUTPUT node cards in step, id for id -------
        self._output_cards: dict[str, QWidget] = {}
        self.params_pane.node_added.connect(self._on_node_added)
        self.params_pane.node_removed.connect(self._on_node_removed)
        self.params_pane.node_mode_changed.connect(self._on_node_mode_changed)

        self._worker: RunWorker | None = None

        status = self.statusBar()
        demucs_status = "found" if demucs_found else "NOT FOUND"
        ffmpeg_status = ffmpeg_path if ffmpeg_path else "NOT FOUND"
        status.showMessage(
            f"device: {device}  |  demucs: {demucs_status}  |  ffmpeg: {ffmpeg_status}"
        )

    # --- keep OUTPUT's cards in step with PARAMS' -----------------------

    def _on_node_added(self, node_id: str, title: str) -> None:
        self._output_cards[node_id] = self.output_pane.add_node(node_id, title)

    def _on_node_removed(self, node_id: str) -> None:
        card = self._output_cards.pop(node_id, None)
        if card is not None:
            self.output_pane.remove_node(card)

    def _on_node_mode_changed(self, node_id: str, mode: str) -> None:
        """PARAMS owns the mode; OUTPUT only shows what it costs it — in
        separate mode the suffix is the stem name, not the user's."""
        card = self._output_cards.get(node_id)
        if card is not None:
            self.output_pane.set_node_mode(card, mode)

    # --- seam: assemble the run config dict ------------------------------

    def _build_run_config(self) -> dict | None:
        """docs/00-locked-spec.md THE RUN CONFIG DICT. Returns None if
        there's nothing checked in INTAKE or no output nodes yet."""
        files = self.intake_pane.get_checked_paths()
        if not files:
            return None
        original_names = self.intake_pane.get_checked_original_names()

        nodes: list[dict] = []
        for card in self.params_pane.get_cards():
            output_card = self._output_cards.get(card.node_id)
            if output_card is None:
                continue
            node_config = card.get_config()
            output_config = self.output_pane.get_output_config(output_card)
            # Separate mode fills the suffix in for you — one stem name per
            # file — so there is nothing to require there.
            if node_config.get("mode") != "separate" and not output_config["filename_field2"]:
                raise ValueError(
                    f"Filename suffix is required — missing on node "
                    f"\"{output_card._header_label.text()}\"."
                )
            nodes.append({**node_config, **output_config})

        if not nodes:
            return None

        return {
            "device": self._device,
            "jobs": self._jobs,
            "files": files,
            "nodes": nodes,
            "original_names": original_names,
        }

    # --- go action ---------------------------------------------------------

    def _on_go(self) -> None:
        try:
            run_config = self._build_run_config()
        except ValueError as exc:
            message = str(exc)
            self._run_status_label.setText(f"Run failed: {message}")
            QMessageBox.critical(self, "Run failed", message)
            return
        if run_config is None:
            self._run_status_label.setText(
                "Check files in INTAKE and add at least one output node first."
            )
            return

        self._set_running(True)
        self._run_status_label.setText("Starting…")

        self._worker = RunWorker(run_config)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_run.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _set_running(self, running: bool) -> None:
        self._run_btn.setEnabled(not running)

    # --- progress from the runner back into the UI --------------------------

    def _on_progress(self, event: dict) -> None:
        stage = event.get("stage", "?")
        status = event.get("status", "?")
        label = event.get("node") or event.get("model") or ""
        file_path = event.get("file")
        file_name = Path(file_path).name if file_path else ""

        text = f"{stage}: {status}"
        if file_name:
            text += f" — {file_name}"
        if label:
            text += f" ({label})"
        self._run_status_label.setText(text)

    # --- batch finished: surface the error report ----------------------------

    def _on_finished(self, report) -> None:
        self._set_running(False)
        written_n = len(report.written)
        error_n = len(report.errors)
        self._run_status_label.setText(f"Done — {written_n} file(s) written, {error_n} error(s).")

        lines = [f"Wrote {written_n} file(s)."]
        if report.errors:
            lines.append("")
            lines.append(f"{error_n} error(s):")
            for err in report.errors:
                lines.append(f"  [{err.stage}] {err.target}: {err.message}")
        else:
            lines.append("No errors.")

        QMessageBox.information(self, "Run complete", "\n".join(lines))

    def _on_failed(self, message: str) -> None:
        self._set_running(False)
        self._run_status_label.setText(f"Run failed: {message}")
        QMessageBox.critical(self, "Run failed", message)
