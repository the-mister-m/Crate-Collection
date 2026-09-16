"""Device detection for Stem Splitter.

Returns one of "cuda" | "mps" | "cpu", per the run config dict in
docs/00-locked-spec.md. Uses torch's own capability checks — demucs
depends on torch anyway, so this is the same signal it will use at
run time.
"""

from __future__ import annotations


def detect_device() -> str:
    """Detect the best available torch device.

    Returns "cuda" if a CUDA GPU is available, "mps" if running on
    Apple Silicon with Metal support, otherwise "cpu".
    """
    try:
        import torch
    except ImportError:
        return "cpu"

    if torch.cuda.is_available():
        return "cuda"

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"

    return "cpu"


if __name__ == "__main__":
    print(detect_device())
