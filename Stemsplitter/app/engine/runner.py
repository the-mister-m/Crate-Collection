"""WAVE B — runner.

Converts each job's input file to wav via ffmpeg, then invokes demucs
with only the flags in DEMUCS FLAG WHITELIST (docs/00-locked-spec.md):
-n, --shifts, --overlap, --segment, -j, -d, -o. No encoding flags are
passed here — encoding to the node's requested format happens in
Wave C (mixer.py), since one demucs job can feed nodes that want
different formats.

Demucs' own output layout is pinned here, once, for Wave C to depend
on: <work_dir>/separated/<model>/<track>/<stem>.wav — this is
demucs' native default (-o work_dir, no --filename override), where
<track> is the original input file's basename without its extension.

A failed file is recorded as an ErrorRecord and its JobResult carries
ok=False. It is never raised — the batch continues to the next job.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .types import ErrorRecord, Job, JobResult, ProgressCallback


def _emit(progress_cb: ProgressCallback | None, event: dict) -> None:
    if progress_cb is not None:
        progress_cb(event)


def _convert_to_wav(file_path: str, dest_dir: Path, ffmpeg_path: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    track_name = Path(file_path).stem
    out_wav = dest_dir / f"{track_name}.wav"
    cmd = [ffmpeg_path, "-y", "-loglevel", "error", "-i", file_path, out_wav.as_posix()]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not out_wav.exists():
        detail = result.stderr.strip()[-2000:] or "ffmpeg exited non-zero"
        raise RuntimeError(f"ffmpeg failed to convert {file_path}: {detail}")
    return out_wav


def _build_demucs_cmd(wav_path: Path, out_dir: Path, job: Job) -> list[str]:
    cmd = [sys.executable, "-m", "demucs", "-n", job.model, "-d", job.device]
    cmd += ["--shifts", str(job.shifts)]
    cmd += ["--overlap", str(job.overlap)]
    if job.segment is not None:
        cmd += ["--segment", str(job.segment)]
    if job.device == "cpu":
        # -j is CPU-only per the locked spec's flag table.
        cmd += ["-j", str(job.jobs)]
    cmd += ["-o", out_dir.as_posix()]
    cmd += [wav_path.as_posix()]
    return cmd


def run_jobs(
    jobs: list[Job],
    work_dir: str,
    ffmpeg_path: str,
    progress_cb: ProgressCallback | None = None,
) -> tuple[list[JobResult], list[ErrorRecord]]:
    """Run every planned job in order. Returns (results, errors).

    A job whose file fails to convert or separate is recorded as an
    error and yields a JobResult with ok=False; the loop continues.
    """
    work_root = Path(work_dir)
    converted_dir = work_root / "converted"
    separated_dir = work_root / "separated"

    results: list[JobResult] = []
    errors: list[ErrorRecord] = []

    # Convert each unique input file to wav once, even if several jobs
    # share it (multiple models requested on the same file).
    wav_cache: dict[str, Path] = {}

    for index, job in enumerate(jobs):
        _emit(progress_cb, {"stage": "convert", "file": job.file, "model": job.model, "status": "start"})
        try:
            if job.file not in wav_cache:
                file_dir = converted_dir / f"file{index}"
                wav_cache[job.file] = _convert_to_wav(job.file, file_dir, ffmpeg_path)
            wav_path = wav_cache[job.file]
        except Exception as exc:
            msg = str(exc)
            errors.append(ErrorRecord(stage="convert", target=job.file, message=msg))
            _emit(progress_cb, {"stage": "convert", "file": job.file, "model": job.model, "status": "error", "message": msg})
            results.append(JobResult(job=job, ok=False, error=msg))
            continue
        _emit(progress_cb, {"stage": "convert", "file": job.file, "model": job.model, "status": "done"})

        _emit(progress_cb, {"stage": "separate", "file": job.file, "model": job.model, "status": "start"})
        cmd = _build_demucs_cmd(wav_path, separated_dir, job)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            msg = result.stderr.strip()[-2000:] or "demucs exited non-zero"
            errors.append(ErrorRecord(stage="separate", target=job.file, message=msg))
            _emit(progress_cb, {"stage": "separate", "file": job.file, "model": job.model, "status": "error", "message": msg})
            results.append(JobResult(job=job, ok=False, error=msg))
            continue

        track_name = wav_path.stem
        stems_dir = separated_dir / job.model / track_name
        if not stems_dir.is_dir():
            msg = f"demucs reported success but stems dir is missing: {stems_dir}"
            errors.append(ErrorRecord(stage="separate", target=job.file, message=msg))
            _emit(progress_cb, {"stage": "separate", "file": job.file, "model": job.model, "status": "error", "message": msg})
            results.append(JobResult(job=job, ok=False, error=msg))
            continue

        _emit(progress_cb, {"stage": "separate", "file": job.file, "model": job.model, "status": "done"})
        results.append(JobResult(job=job, ok=True, stems_dir=stems_dir.as_posix()))

    return results, errors
