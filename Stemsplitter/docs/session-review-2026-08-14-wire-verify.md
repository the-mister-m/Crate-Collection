# SESSION REVIEW — Stemsplitter Session 4 (Wire + Verify) — 2026-08-14 17:15–19:47 EDT

    task:    Stem Splitter build — session 4 of 4, last session of the build
    author:  builder agent (Sonnet), running both waves in series
    reads:   00-locked-spec.md, 01/02/03-session-*.md, 04-session-wire-verify.md,
             then the real code: app/ui/*, app/core/*, app/engine/*

No agents/ file loaded as this session's definition — ran as a direct
session, not spawned as a subagent with a defined agents/ file.

---

## EDITS

- [app/ui/node_list.py](../app/ui/node_list.py) — embedded `NodeControls` into
  every `NodeCard` at creation (the seam was previously unpopulated — PARAMS
  would have shown empty cards with no controls); added `node_added`/
  `node_removed` signals and `get_cards()` so main_window.py can wire PARAMS
  to OUTPUT and to the run config.
- [app/ui/output_pane.py](../app/ui/output_pane.py) — fixed the carried-forward
  numbering mismatch: `add_node()` now takes the same `node_id`/title
  node_list.py assigns at creation instead of renumbering by live list
  position; removed `_renumber()`.
- [app/ui/main_window.py](../app/ui/main_window.py) — removed the stale
  docstring and dead `_make_pane()` helper (carried-forward item 3); added
  the Run button, status label, run-config assembly (`_build_run_config()`),
  and progress/error-report wiring.
- [app/ui/run_worker.py](../app/ui/run_worker.py) — new file, a `QThread`
  subclass that calls `engine.pipeline.run()` off the UI thread.

## STRAY FILES

- None left in the repo. Verification was driven from throwaway scripts in
  the session's own scratchpad (outside the repo), not committed anywhere.

## GOALS DONE

**Wave 1 — wire.** Panes → run config dict → engine → progress/error report,
verified against 00-locked-spec.md's schema exactly (confirmed by printing
an assembled dict from real widget state and diffing its keys against the
node schema).

**Wave 2 — verify**, the one named scenario, driven through the real wired
path (`intake._ingest()` on a real file → PARAMS/OUTPUT nodes built through
the actual pane widgets → `_on_go()` → `RunWorker` → `engine.run()`, not a
hand-written dict bypassing the UI):

1. **2 separations, not 3** — confirmed: exactly 2 `separate: start`
   progress events (`htdemucs` once, `mdx_extra_q` once) across 3 configured
   nodes; the two nodes sharing `htdemucs` at matching settings shared one
   pass.
2. **3 files written, correct directories, correct names** — confirmed:
   each of the 3 nodes wrote to its own `output_dir`, filenames matching
   `{track}_{mix}.{ext}` with `{mix}` = `drums+vocals`, `bass+other`,
   `vocals` — exactly the stems each node had checked.
3. **Mixed files contain checked stems, not unchecked ones** — spot-checked:
   the three output files have distinct MD5s and clearly different
   `ffmpeg volumedetect` levels (drums+vocals mean −73.5dB, bass+other mean
   −16.5dB, vocals-only mean −85.5dB) — not identical content under
   different names.
4. **Progress moved while it ran** — confirmed: 18 progress events across 7
   distinct stage/status pairs (convert / separate / mix × start / done /
   error), and the status label text changing over the course of the run,
   not just present at start and end.
5. **A deliberately bad file was skipped, named in the error report, batch
   continued** — confirmed: 5 `ErrorRecord`s (2 `convert`-stage, explicitly
   naming the bad path with ffmpeg's "No such file or directory"; 3
   `mix`-stage, one per node fed by that file, "skipped: separation
   failed..."), while the good file's 3 nodes still wrote successfully.
6. **Close/reopen opens empty, no persistence** — confirmed: no
   `QSettings`/save-file code anywhere in `ui`/`core`/`main.py`; a freshly
   constructed `MainWindow` after a populated one had 0 intake rows, 0
   nodes, 0 output cards.

**Is the build functionally complete end to end: yes.** All six items
verified through the real wired UI-to-engine path.

## FINDINGS — reported, not fixed

Per this session's rule: anything behind the seam beyond the three named
carried-forward items is a finding, not something to fix unilaterally.

- **`{track}` renders as a UUID, not the original filename.**
  `run_config["files"]` carries intake's already-converted wav paths
  (UUID-named, from core/intake.py's `convert_to_wav`), and the engine's
  runner derives `{track}` from that file's own stem. Output lands
  correctly, just named e.g. `790c590e..._vocals.wav` instead of
  `testaudio_vocals.wav`. Cosmetic, not a crash.
- **Intake's own ffmpeg-unreadable-file filter is silent and pre-run.** A
  genuinely corrupt file dropped through the real INTAKE flow never becomes
  a checked row at all (console print only, in core/intake.py's `ingest()`)
  — it never reaches the engine's structured error report. The
  skip-and-report mechanism verified above (item 5) works correctly for
  anything that gets *into* a run and fails later; intake's pre-run filter
  is a separate, earlier gate from Session 1 that this session didn't
  touch.
- **`engine/types.py`'s `Job` docstring is stale** — it says jobs are
  grouped "by (file, model) only." The actual code in `planner.py`, and
  that file's own docstring, correctly group by
  `(file, model, shifts, overlap, segment)`, matching the corrected locked
  spec. Not fixed — cosmetic docstring only, not this session's named job.
- **No UI control exists for the run-level `jobs` field** — matches the
  three-pane spec, there genuinely isn't one anywhere. Wired a default of
  `os.cpu_count() or 1`; irrelevant on the test machine (device is `mps`,
  `jobs` is CPU-only and ignored per the flag whitelist).

## BRANDON'S TODOS

- None required — the findings above are FYI, not blockers.

## CLOSER REVIEW

- Settle discrepancies, rewrite the Stemsplitter warm-start block in
  MEMORY.md — closer only.
- [INDEX.md](../../INDEX.md) — Stemsplitter subproject section, this
  report added.
- [SESSIONLOG.md](../../SESSIONLOG.md) — Session 4 entry appended.
