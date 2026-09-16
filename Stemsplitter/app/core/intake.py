"""File collection + ffmpeg conversion for the intake pane.

Wave 2 of Session 1. Walks dropped files/folders into a flat list of
candidate audio files, then converts each into a wav copy via ffmpeg
(the same path Wave 1's core/locate.py finds) so everything downstream
works from a single consistent format. See
docs/01-session-foundation-intake.md.
"""

from __future__ import annotations

import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class IntakeFile:
    original_path: str  # absolute path as dropped
    display_name: str  # basename shown in the row
    wav_path: str  # absolute path to the converted wav


_workdir_cache: Path | None = None


def _workdir() -> Path:
    """One temp directory per app run, created on first use."""
    global _workdir_cache
    if _workdir_cache is None:
        _workdir_cache = Path(tempfile.mkdtemp(prefix="stemsplitter_intake_"))
    return _workdir_cache


def collect_paths(dropped_paths: list[str]) -> list[str]:
    """Expand a mixed list of file/folder paths into a flat file list.

    Folders are walked recursively. Directories and dotfiles are skipped.
    Order is preserved; duplicates (by resolved absolute path) are dropped.
    """
    seen: set[str] = set()
    files: list[str] = []

    for raw in dropped_paths:
        p = Path(raw)
        if p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and not child.name.startswith("."):
                    resolved = str(child.resolve())
                    if resolved not in seen:
                        seen.add(resolved)
                        files.append(resolved)
        elif p.is_file() and not p.name.startswith("."):
            resolved = str(p.resolve())
            if resolved not in seen:
                seen.add(resolved)
                files.append(resolved)

    return files


def convert_to_wav(src_path: str, ffmpeg_path: str) -> str | None:
    """Convert one file to wav via ffmpeg.

    Returns the absolute path to the converted wav, or None if ffmpeg
    can't read the file (non-zero exit / no output produced). This is
    the "accept anything ffmpeg reads" test: try the conversion, trust
    the exit code.
    """
    dest = _workdir() / f"{uuid.uuid4().hex}.wav"
    result = subprocess.run(
        [ffmpeg_path, "-y", "-i", src_path, "-loglevel", "error", str(dest)],
        capture_output=True,
    )
    if result.returncode != 0 or not dest.exists():
        return None
    return str(dest)


def ingest(dropped_paths: list[str], ffmpeg_path: str) -> list[IntakeFile]:
    """Collect dropped files/folders and convert each to wav.

    Files ffmpeg can't read are dropped silently from the result and
    reported to the console (matching Wave 1's console-reporting style
    in main.py — no dialog, no UI addition).
    """
    intake_files: list[IntakeFile] = []
    for path in collect_paths(dropped_paths):
        wav_path = convert_to_wav(path, ffmpeg_path)
        if wav_path is None:
            print(f"intake: skipped (ffmpeg could not read): {path}")
            continue
        intake_files.append(
            IntakeFile(
                original_path=path,
                display_name=Path(path).name,
                wav_path=wav_path,
            )
        )
    return intake_files
