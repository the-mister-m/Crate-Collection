"""Shared dataclasses for the separation engine.

See docs/00-locked-spec.md for the run config dict and node schema
these types are built from. Headless — no UI imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Job:
    """One demucs separation pass: one file, one model, one set of
    demucs-affecting parameters (shifts/overlap/segment).

    Every node listed in node_ids consumes this job's stems as a cheap
    sum, per HOW THE RUN WORKS in the locked spec. Jobs are grouped by
    (file, model) only, per the locked spec's own wording. If nodes
    sharing a (file, model) pair specify different shifts/overlap/
    segment, the first such node encountered supplies the values for
    the single shared demucs call — see planner.py.
    """

    file: str  # absolute path to the original input file
    model: str
    device: str  # run-level: cuda | mps | cpu
    jobs: int  # run-level: -j, CPU only
    shifts: int
    overlap: float
    segment: int | None
    node_ids: list[str] = field(default_factory=list)


@dataclass
class JobResult:
    job: Job
    ok: bool
    stems_dir: str | None = None  # dir containing <stem>.wav files, if ok
    error: str | None = None


@dataclass
class ErrorRecord:
    stage: str  # "convert" | "separate" | "mix"
    target: str  # file path or node id
    message: str


@dataclass
class WrittenFile:
    node_id: str
    path: str


@dataclass
class RunReport:
    written: list[WrittenFile] = field(default_factory=list)
    errors: list[ErrorRecord] = field(default_factory=list)


# A progress event is a plain dict, e.g.:
#   {"stage": "separate", "file": ..., "model": ..., "status": "start"}
#   {"stage": "mix", "node": ..., "file": ..., "status": "error", "message": ...}
ProgressCallback = Callable[[dict], None]
