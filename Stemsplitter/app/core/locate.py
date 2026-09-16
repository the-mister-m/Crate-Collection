"""Locate demucs and ffmpeg on the host system.

Per docs/00-locked-spec.md, demucs is a Python dependency (no bridge) —
so "locating" it means checking whether the demucs package is importable
in the running interpreter, in addition to checking for a `demucs`
console-script on PATH. ffmpeg is a separate system binary, located via
PATH only.
"""

from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass


@dataclass
class LocateResult:
    found: bool
    path: str | None       # console-script / binary path, if any
    importable: bool = False  # demucs only: True if the package imports


def locate_ffmpeg() -> LocateResult:
    path = shutil.which("ffmpeg")
    return LocateResult(found=path is not None, path=path)


def locate_demucs() -> LocateResult:
    path = shutil.which("demucs")
    importable = importlib.util.find_spec("demucs") is not None
    return LocateResult(found=path is not None or importable, path=path, importable=importable)


if __name__ == "__main__":
    ff = locate_ffmpeg()
    dm = locate_demucs()
    print(f"ffmpeg:  found={ff.found} path={ff.path}")
    print(f"demucs:  found={dm.found} path={dm.path} importable={dm.importable}")
