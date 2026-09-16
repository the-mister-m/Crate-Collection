"""WAVE C — mixer + writer.

Each node writes in one of two modes, per its ``mode`` field:

  remove   — sum the node's checked stems into a single file. A plain
             sum, no gain, pan, EQ, or normalisation, per NOT BUILDING
             in docs/00-locked-spec.md. One file per node, named
             field1 + field2.
  separate — write each checked stem as its own file, no summing. N
             files per node, named field1 + <stem name>: the stem name
             takes the place of field2, which the UI greys out.

Separate mode is why the locked spec's "exactly one mixed file per
node" and "a node's individual stems are never written out" no longer
hold; the spec has not been amended to match.

Reuses demucs' own demucs.audio.save_audio for encoding, so mp3/flac/
int24/float32 output matches demucs' native encoder exactly (demucs is
already a project dependency; this is not a new one). save_audio's
default clip="rescale" is demucs' own anti-clipping safety on the
encoder path, not mixing we are adding.

filename fields:
  field 1 — literal text used for every file in the run; empty means
            each file uses its own original filename (basename, no
            extension) instead
  field 2 — joined directly after field 1 with nothing between them.
            Required in remove mode; in separate mode the stem name is
            substituted for it and the field is ignored.
  ext     — the node's format (wav/mp3/flac), unchanged
"""

from __future__ import annotations

from pathlib import Path

from demucs.audio import AudioFile, save_audio

from .types import ErrorRecord, JobResult, ProgressCallback

_BIT_DEPTH = {
    "int24": {"bits_per_sample": 24, "as_float": False},
    "float32": {"bits_per_sample": 32, "as_float": True},
    None: {"bits_per_sample": 16, "as_float": False},
}

MODE_SEPARATE = "separate"


def _emit(progress_cb: ProgressCallback | None, event: dict) -> None:
    if progress_cb is not None:
        progress_cb(event)


def _render_filename(field1: str, field2: str, track: str, ext: str) -> str:
    stem = field1 if field1 else track
    return f"{stem}{field2}.{ext}"


def _read_stem(stems_dir: str, stem_name: str):
    """One separated stem as (wav, samplerate). Raises if it is missing."""
    stem_path = Path(stems_dir) / f"{stem_name}.wav"
    if not stem_path.exists():
        raise ValueError(f"stem file missing: {stem_path}")
    af = AudioFile(stem_path)
    # streams=0: a stem wav has exactly one audio stream; this returns a
    # [channels, time] tensor instead of AudioFile's default
    # [streams, channels, time].
    return af.read(streams=0), af.samplerate()


def _write(wav, samplerate, node: dict, out_name: str) -> str:
    depth = _BIT_DEPTH[node["bit_depth"]]
    out_path = Path(node["output_dir"]) / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_audio(
        wav,
        out_path,
        samplerate,
        bitrate=node["mp3_bitrate"],
        bits_per_sample=depth["bits_per_sample"],
        as_float=depth["as_float"],
    )
    return out_path.as_posix()


def mix_and_write(
    job_results: list[JobResult],
    nodes_by_id: dict[str, dict],
    original_names: dict[str, str],
    progress_cb: ProgressCallback | None = None,
) -> tuple[list[dict], list[ErrorRecord]]:
    """For every node fed by a successful job, write its checked stems —
    summed into one file in remove mode, one file each in separate mode.
    Nodes fed by a failed job are recorded as errors and never written.
    Returns (written, errors), where written is a list of
    {"node_id": ..., "path": ...} dicts — one entry per file written, so
    a separate-mode node contributes several.
    """
    written: list[dict] = []
    errors: list[ErrorRecord] = []

    for jr in job_results:
        track_name = original_names[jr.job.file]

        for node_id in jr.job.node_ids:
            node = nodes_by_id[node_id]

            if not jr.ok:
                errors.append(ErrorRecord(
                    stage="mix",
                    target=node_id,
                    message=(
                        f"skipped: separation failed for {jr.job.file} "
                        f"({jr.job.model}): {jr.error}"
                    ),
                ))
                continue

            checked = sorted(name for name, on in node["stems"].items() if on)
            _emit(progress_cb, {"stage": "mix", "node": node_id, "file": jr.job.file, "status": "start"})

            try:
                if not checked:
                    raise ValueError("node has no checked stems")

                ext = node["format"]
                field1 = node["filename_field1"]

                if node.get("mode") == MODE_SEPARATE:
                    # One file per checked stem; the stem name is the suffix.
                    for stem_name in checked:
                        wav, samplerate = _read_stem(jr.stems_dir, stem_name)
                        out_name = _render_filename(field1, stem_name, track_name, ext)
                        path = _write(wav, samplerate, node, out_name)
                        written.append({"node_id": node_id, "path": path})
                else:
                    mix = None
                    samplerate = None
                    for stem_name in checked:
                        wav, samplerate = _read_stem(jr.stems_dir, stem_name)
                        mix = wav if mix is None else mix + wav

                    out_name = _render_filename(field1, node["filename_field2"], track_name, ext)
                    path = _write(mix, samplerate, node, out_name)
                    written.append({"node_id": node_id, "path": path})

                _emit(progress_cb, {"stage": "mix", "node": node_id, "file": jr.job.file, "status": "done"})
            except Exception as exc:
                msg = str(exc)
                errors.append(ErrorRecord(stage="mix", target=node_id, message=msg))
                _emit(progress_cb, {"stage": "mix", "node": node_id, "file": jr.job.file, "status": "error", "message": msg})

    return written, errors
