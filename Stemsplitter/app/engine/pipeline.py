"""Engine entry point — wires WAVE A -> WAVE B -> WAVE C in series.

Takes the run config dict (docs/00-locked-spec.md) and returns a
RunReport of written files and errors. This is the only function
Session 4 needs to call; it is the entire seam between this headless
engine and whatever wires it up.

Headless: no UI imports anywhere in this package.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from core.locate import locate_ffmpeg

from .mixer import mix_and_write
from .planner import plan
from .runner import run_jobs
from .types import ProgressCallback, RunReport, WrittenFile


def run(run_config: dict, progress_cb: ProgressCallback | None = None) -> RunReport:
    """Run a full separation batch for one run config dict.

    Raises RuntimeError only for environment problems (ffmpeg not
    found) that make the run impossible to attempt at all. Per-file
    and per-node failures never raise — they land in the returned
    RunReport.errors and the batch continues.
    """
    ffmpeg = locate_ffmpeg()
    if not ffmpeg.found or not ffmpeg.path:
        raise RuntimeError("ffmpeg not found on PATH")

    # demucs.audio.AudioFile shells out to the literal "ffmpeg" command,
    # so make sure its directory is on PATH for this process.
    ffmpeg_dir = str(Path(ffmpeg.path).parent)
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    if ffmpeg_dir not in path_parts:
        os.environ["PATH"] = os.pathsep.join([ffmpeg_dir, *path_parts])

    jobs = plan(run_config)

    # Fresh temp dir per run — no caching of separated stems between
    # runs, per NOT BUILDING in the locked spec.
    work_dir = tempfile.mkdtemp(prefix="stemsplitter_")
    job_results, wave_b_errors = run_jobs(jobs, work_dir, ffmpeg.path, progress_cb)

    nodes_by_id = {node["id"]: node for node in run_config["nodes"]}
    written, wave_c_errors = mix_and_write(job_results, nodes_by_id, run_config["original_names"], progress_cb)

    report = RunReport()
    report.written = [WrittenFile(node_id=w["node_id"], path=w["path"]) for w in written]
    report.errors = wave_b_errors + wave_c_errors
    return report
