# STEM SPLITTER — LOCKED SPEC

    task:    Stem Splitter build — the frozen contract every session reads first
    author:  session agent (Opus), design session 2026-08-14
    reads:   nothing. This file is the root.
    read by: 01-session-foundation-intake.md
             02-session-panes.md
             03-session-engine.md
             04-session-wire-verify.md
             05-session-output-naming.md

This file is LOCKED. No agent adds a key, a flag, a pane, or a feature.
Anything that seems missing is missing on purpose — see NOT BUILDING.
If a build genuinely cannot proceed without a change here, the agent
STOPS and asks Brandon. It does not edit this file.

**AMENDED 2026-08-23, on Brandon's explicit instruction.** Two changes,
both marked AMENDED below:

1. `filename_template` is gone, replaced by `filename_field1` /
   `filename_field2` — Session 5's change, which this file was never
   updated to carry (flagged in that session's review, left for
   Brandon).
2. A node gains `mode`. Separate mode writes each checked stem as its
   own file, which retires the old "one mixed file, never individual
   stems" lock and its NOT BUILDING line.

Everything not marked AMENDED is still locked and still Brandon's to
unlock. Sessions 01–05's buildplans are history and were not rewritten;
where they disagree with this file, this file wins.

---

## WHAT IT IS

A desktop app. Drop in audio files or a folder. Pick which stems you want.
It runs demucs and writes them — summed into one file, or one file per
stem, per node. (AMENDED — the second mode is new.)

Stack: **Python + PySide6 (Qt)**. Demucs is Python; there is no bridge.

---

## THE THREE PANES

    ┌──────────────┬───────────────────────┬──────────────┐
    │   INTAKE     │        PARAMS         │   OUTPUT     │
    │              │                       │              │
    │ drop files   │  node list            │ per node:    │
    │ or a folder  │  expand / collapse    │  destination │
    │              │  scrollable           │  dir         │
    │ checkbox per │                       │              │
    │ file — only  │  [ add output ] →     │  filename    │
    │ checked ones │  appends a node       │  template    │
    │ run          │                       │              │
    │              │  per node: model,     │              │
    │              │  remove / separate,   │              │
    │              │  stem checkboxes with │              │
    │              │  select/deselect all, │              │
    │              │  shifts, overlap,     │              │
    │              │  segment, format      │              │
    └──────────────┴───────────────────────┴──────────────┘

Left is what goes in. Middle is what happens to it. Right is where it lands.

---

## THE RUN CONFIG DICT

This is the only seam that matters. Session 2 emits it. Session 3 consumes
it. Session 4 connects them. Neither session needs to read the other's code.

```python
{
  "device": "cuda" | "mps" | "cpu",
  "jobs":   int,                      # CPU only, ignored on gpu
  "files":  [str, ...],               # absolute paths, checked files only
  "nodes":  [ <node>, ... ]
}
```

A node:

```python
{
  "id":                str,           # stable, unique within the run
  "model":             str,           # see MODELS
  "mode":              "remove" | "separate",   # AMENDED — see MODE
  "stems":             {str: bool},   # keys are that model's stem names
  "shifts":            int,           # 0 = off
  "overlap":           float,         # 0.25 default
  "segment":           int | None,    # seconds, None = model default
  "format":            "wav" | "mp3" | "flac",
  "mp3_bitrate":       int,           # ignored unless format == mp3
  "bit_depth":         "int24" | "float32" | None,
  "output_dir":        str,           # absolute
  "filename_field1":   str,           # AMENDED — literal text; empty = the
                                      #   file's own original name
  "filename_field2":   str            # AMENDED — joins directly after
                                      #   field1, nothing between. Required
                                      #   in remove mode; in separate mode
                                      #   the stem name is substituted for it
}

The run config dict also carries `"original_names": {wav_path: str}` —
the original filename stem for each intake row, which is what an empty
`filename_field1` resolves to. (AMENDED — Session 5 added it and this
file was never updated.)
```

Notes that are part of the lock:

- `stems` keys depend on the model. 4-stem models use `drums`, `bass`,
  `vocals`, `other`. A 6-stem model adds `guitar` and `piano`.
- **AMENDED.** What a node produces depends on its `mode`. See MODE.
- Nothing here persists. The app opens with no nodes. Every session is
  rebuilt by hand.

---

## MODE

*AMENDED 2026-08-23. This section is new; it replaces the old "a node
always produces one mixed file" lock.*

Every node is in one of two modes. In **both**, a checked stem is a stem
you want — the checkboxes never invert. Mode only decides whether the
stems you checked land in one file or several.

| mode | writes | named |
|---|---|---|
| `remove` | the checked stems summed into **one** file | `field1` + `field2` |
| `separate` | **one file per checked stem**, no summing | `field1` + the stem's name |

`remove` is the default and is the original behaviour, unchanged. Its
name is the use case: check what you want kept, and what you left
unchecked is what got removed.

In `separate` the stem name takes the place of `field2`, so OUTPUT
greys that field out. `field1` still applies and is still where the
user puts their own separator — an empty `field1` gives
`MySongdrums.wav`, since the two parts join with nothing between them
exactly as they do in `remove`.

Mode costs nothing at separation time. Demucs produces every stem
either way; mode only changes what gets written.

The sum is still a plain sum — no gain, pan, EQ, or normalisation.
Separate mode does not sum at all, so it never touches the audio.

---

## DEMUCS FLAG WHITELIST

These and nothing else. An agent that wants another stops and asks.

| flag | what it does | where it lives |
|---|---|---|
| `-n MODEL` | which model | node |
| `--shifts N` | N averaged passes. Real quality gain, N× runtime | node |
| `--overlap F` | seam overlap, default 0.25 | node |
| `--segment N` | chunk length. This is the memory dial, not a quality dial | node |
| `-j N` | parallel jobs, CPU only | run |
| `-d DEVICE` | cuda / mps / cpu | run |
| `--mp3` `--flac` `--int24` `--float32` `--mp3-bitrate` | output encoding | node |
| `-o DIR` | destination | node |

Naming is **not** a demucs flag. (AMENDED — the old `--filename TPL`
row is gone.) Since Session 3 the mixer writes files itself, so the two
filename fields are ours, not demucs'.

---

## MODELS

Available in demucs v4:

- `mdx_extra_q` — quantized, ~150 MB. Fastest, lowest quality.
- `htdemucs` — default, ~80 MB, 4 stems.
- `htdemucs_ft` — fine-tuned bag of four, ~320 MB. Cleaner, ~4× slower.
- `htdemucs_6s` — ~80 MB, adds guitar and piano.
- `mdx_extra` — ~600 MB.

Weights **ship with the app**. No first-run download, no internet required.

> OPEN — not decided in the design session. Which of these ship?
> Sizes are approximate and must be confirmed against the real
> checkpoints before Session 1 packages anything. Session 1 stops
> and asks Brandon rather than choosing.

Model is a **dropdown the user picks**, per node. Device is detected and
sets a sane default. The app does not try to guess how powerful the
machine is.

---

## HOW THE RUN WORKS

Separation is the expensive part and it produces every stem regardless.
So demucs runs **once per (file × model × quality settings)** — shifts,
overlap, and segment are baked into the separation pass itself, so nodes
only share a pass when those three match too. Every node sharing a pass
is a cheap sum over the same result.

    file.mp3
       │  ffmpeg → wav
       ▼
    ┌─────────────┐
    │   demucs    │   once per model
    └──────┬──────┘
           │  drums  bass  vocals  other
      ┌────┴────┬──────────┐
      ▼         ▼          ▼
    node A    node B    node C      cheap sums
    d+b+o     d+b       b+o
      │         │          │
      ▼         ▼          ▼
    dir A     dir B      dir C

A separate-mode node sits in exactly the same place on that tree — it
just writes each of its stems instead of adding them together first.

Ten nodes on one model, same quality settings, cost barely more than one
node. Nodes on different models — or the same model with different
shifts/overlap/segment — each pay full price. Grouping nodes by model and
matching quality settings is the whole performance story.

**Failure.** A file that fails does not stop the batch. It is skipped, the
run continues, and an error report is shown at the end.

---

## NOT BUILDING

Named and forbidden. Agents do not drift toward what you thought of; they
drift toward what looks obviously missing. This is that list.

- presets, saved configs, or any persistence between launches
- a job queue, scheduler, or run history
- retries, resume, or caching of separated stems
- waveform previews, playback, scrubbing, or any audio display
- drag-to-reorder anything
- per-stem gain, panning, EQ, or any mixing beyond a plain sum
- ~~writing individual stems out~~ — AMENDED, this is now separate mode
- a CLI, a plugin, a server mode, or an API
- auto-detecting machine capability to pick a model
- telemetry, update checks, crash reporting
- tests beyond what Session 4's verify step names
- a README

---

## SESSION MAP

    SESSION 1 — Foundation + Intake     2 agents, series
    SESSION 2 — Params + Output panes   3 agents, parallel
    SESSION 3 — Engine                  3 agents, series
    SESSION 4 — Wire + Verify           2 agents, series
    SESSION 5 — Output naming patch      1 agent, series
    SESSION 6 — Remove / separate mode   session agent, direct

Sessions 2 and 3 never see each other's code. The run config dict above is
the entire contract between them.
