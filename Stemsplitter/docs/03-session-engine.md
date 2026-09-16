# SESSION 3 — ENGINE

    task:    Stem Splitter build — session 3 of 4
    author:  session agent (Opus), design session 2026-08-14
    reads:   00-locked-spec.md  ← read this first, all of it
    feeds:   04-session-wire-verify.md

Read the locked spec before anything else. Do not add to it.

This session is headless. It has no UI, imports no UI, and never reads
Session 2's code. It takes a run config dict in and writes files out.

---

## GOAL

Hand it a run config dict. It separates, sums, encodes, and routes. It
reports progress and it reports failures.

---

## WAVES

    WAVE A — planner                       series
      group nodes by model
      emit one demucs job per (file × model)
      each job carries the list of nodes that consume it

    WAVE B — runner                        series, after A
      ffmpeg convert to wav
      invoke demucs with the whitelisted run + node flags
      emit progress as it goes
      a failed file is skipped, recorded, and the batch continues

    WAVE C — mixer + writer                series, after B
      sum the checked stems for each node
      encode to the node's format
      write to the node's output_dir using its filename_template

Series, not parallel. Each wave consumes the previous wave's output shape,
and demucs' on-disk output layout is a real seam the later waves depend on.

If Session 3 runs hot on context, WAVE C splits into its own session.

---

## THE THING THAT MAKES THIS FAST

Separation is expensive and produces every stem regardless. Nodes sharing
a model share one separation pass. Ten nodes on `htdemucs` cost barely
more than one. This is why the planner exists and why it comes first.

---

## SEAMS

    in:   the run config dict — see 00-locked-spec.md
    out:  written audio files, plus an error report for skipped files
    internal: demucs' own output directory layout. Waves B and C both
              depend on it. Pin it once, in the runner.

---

## BUDGET

    3 agents, series
    ~110k session context, ~60k per agent
    The fattest session.

---

## DRIFT — MEDIUM

Demucs is real and testable, so errors surface fast. The risk here isn't
wrongness, it's scope. Expected failures:

- adding a job queue, retry logic, or resume
- caching separated stems between runs
- adding flags outside the whitelist because they'd obviously help
- writing individual stems out "since we have them anyway"
- per-stem gain or normalisation in the mixer — it is a plain sum

All of the above are in NOT BUILDING.

---

## DONE WHEN

- a hand-written dict with 3 nodes across 2 models runs end to end
- the planner provably issues 2 separations, not 3
- output files land in the right directories with the right names
- a deliberately corrupt file is skipped and appears in the error report
- no UI code exists anywhere in this session's output
