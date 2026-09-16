"""RunWorker — Session 4 wiring.

Runs the headless engine (engine/pipeline.py) off the Qt UI thread so
the window doesn't freeze during separation. See
docs/04-session-wire-verify.md WAVE 1: "Wire a 'go' action that calls
app/engine/pipeline.run() ... off the UI thread (QThread or similar)".

progress_cb is called from inside run(), which executes in this
QThread's own thread — Signal.emit() from a non-GUI thread is safe;
Qt queues delivery to the connected slot(s) since they live on the
main thread (default AutoConnection).
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from engine.pipeline import run as run_pipeline


class RunWorker(QThread):
    progress = Signal(dict)
    finished_run = Signal(object)  # engine.types.RunReport
    failed = Signal(str)

    def __init__(self, run_config: dict, parent=None) -> None:
        super().__init__(parent)
        self._run_config = run_config

    def run(self) -> None:  # executes in the worker thread
        try:
            report = run_pipeline(self._run_config, progress_cb=self.progress.emit)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished_run.emit(report)
