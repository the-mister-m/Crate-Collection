SESSION REVIEW — Audio Diffusion Harness / Stemsplitter — 2026-08-23, 16:54–17:11 EDT (from transcript)

Session 6. No subagents — session agent direct, no buildspec written
first. Brandon asked for a UI change, gated it after two questions,
said go, then said update the docset and spec.

WHAT HE ASKED FOR
A per-node mode. The old behaviour sums a node's checked stems into one
file; the new one writes each checked stem as its own file. His words:
"Remove stems" vs "separate stems", and "suffix would be the name of
the stem that was split".

TWO THINGS HE DECIDED, NOT ME
- Where the stem name goes in the filename: it replaces field 2. He
  picked that off three options, knowing the option's own preview showed
  a blank field 1 giving `MySongdrums.wav`.
- Checkbox meaning does not flip. Checked = kept in both modes. The
  "Remove stems" label is the use-case name, not an inversion.

EDITS — code
- [../app/ui/node_controls.py](../app/ui/node_controls.py) — two mode radios above the stems grid; MODE_REMOVE default; mode_changed signal; "mode" added to get_node_config()
- [../app/ui/node_list.py](../app/ui/node_list.py) — NodeCard/NodeList relay the mode change upward with node_id attached
- [../app/ui/output_pane.py](../app/ui/output_pane.py) — set_node_mode() greys the suffix field in separate mode; field2's QLabel now held so its text can change
- [../app/ui/main_window.py](../app/ui/main_window.py) — wires node_mode_changed to OUTPUT; stops requiring a suffix on separate-mode nodes
- [../app/engine/mixer.py](../app/engine/mixer.py) — rewritten: _read_stem/_write helpers, then branches on mode. Separate writes one file per checked stem, `_render_filename(field1, stem_name, ...)`

EDITS — docs
- [00-locked-spec.md](00-locked-spec.md) — amended on Brandon's explicit instruction, every change marked AMENDED. New MODE section; `mode` in the node dict; the "one mixed file / never individual stems" lock retired; the NOT BUILDING line struck through rather than deleted
- [00-locked-spec.md](00-locked-spec.md) — ALSO carried Session 5's unreconciled staleness, which Brandon's "all" covers: `filename_template` replaced by `filename_field1`/`filename_field2`, `original_names` documented, and the `--filename TPL` whitelist row removed (naming has not been a demucs flag since Session 3)
- [../../INDEX.md](../../INDEX.md), [../../SESSIONLOG.md](../../SESSIONLOG.md) — this session's entries

NOT TOUCHED, ON PURPOSE
- Buildplans [01](01-session-foundation-intake.md)–[05](05-session-output-naming.md) are session history, not living contracts. [03-session-engine.md](03-session-engine.md) line 38 still says `filename_template` and line 80 still forbids writing individual stems; [05-session-output-naming.md](05-session-output-naming.md) still calls field 2 unconditionally required. The amended spec says outright that where they disagree, it wins. Rewriting them would be rewriting what past sessions were told.
- MEMORY.md — Closer's.
- `engine/planner.py`, `runner.py`, `types.py` — mode does not reach planning. Untouched.

VERIFICATION — real, not asserted
- All five edited files compile.
- Headless Qt smoke test: default mode `remove`, suffix field enabled; flip to `separate` → config reads `separate`, suffix disabled, label drops "(required)", placeholder reads "= the stem's name"; flip back restores all three.
- mixer.py against synthetic stems (drums .1 / bass .2 / vocals .4 / other .8, vocals unchecked). Remove → one file `MySong_backing.wav`. Separate → three files `MySong_drums/bass/other.wav`. Separate's drums file measured exactly 0.1 — untouched.
- The summed file measured 0.99 where 1.1 went in. That is demucs' own `save_audio(clip="rescale")`, pre-existing on the encoder path and already documented in mixer.py's docstring. Not a regression and not new. Separate mode never trips it.
- `engine/test_planner.py` NOT run — pytest still absent from app/.venv, the same gap Session 5 flagged. Planner was untouched this session, so nothing regressed there, but the test genuinely did not run.

STRAY FILES
- None in the project. The mixer test wrote synthetic wavs to OS temp dirs (/var/folders/...), not into the repo.

GOALS DONE
- Per-node remove/separate mode, UI through engine, verified end to end.
- Spec reconciled with the code, including Session 5's leftover.

BRANDON'S TODOS
- Nothing new opened. TODO.md's two existing optional follow-ups (silent intake ffmpeg filter, stale `types.py` Job docstring) are still open and still not gates.
- Standing gap, third session running: no pytest in `app/.venv`, no pip either. Whether that gets fixed is his call.

CLOSER REVIEW
- Gets copy of review, not a contract.
- Decide whether the spec's AMENDED-block convention (amendments marked inline, old lines struck through, buildplans left as history) is how future unlocks get recorded — closer.
- MEMORY.md warm-start block for Stemsplitter now says v1 + naming patch; it needs the mode change — closer.
