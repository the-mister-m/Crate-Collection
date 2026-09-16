# SESSION REVIEW — Stemsplitter (output naming patch) — 2026-08-15

Builder agent (agents/builder.md). Buildspec:
[05-session-output-naming.md](05-session-output-naming.md), all four
waves built in series, single agent, no handoff needed.

(clickable links only — no code blocks, no restating)

## EDITS

- [../app/ui/intake_pane.py](../app/ui/intake_pane.py) — Wave 1: carries original filename stem alongside wav path (`_ORIGINAL_NAME_ROLE`, `get_checked_original_names()`)
- [../app/ui/main_window.py](../app/ui/main_window.py) — Wave 1: builds and passes `original_names` in run config; Wave 4: blocks run with readable `ValueError` when a node's field 2 is empty, caught in `_on_go`
- [../app/engine/pipeline.py](../app/engine/pipeline.py) — Wave 1: passes `run_config["original_names"]` into `mix_and_write`
- [../app/engine/mixer.py](../app/engine/mixer.py) — Wave 1: `mix_and_write` takes `original_names`, indexes it directly for `track_name`; Wave 3: `_render_filename` replaced with the plain two-field join, docstring updated
- [../app/ui/output_pane.py](../app/ui/output_pane.py) — Wave 2: `DEFAULT_FILENAME_TEMPLATE` removed; single template field replaced with two `QLineEdit`s (`_field1_edit` / `_field2_edit`); `get_output_config()` returns `filename_field1`/`filename_field2`

## STRAY FILES

- none

## GOALS DONE

- uuid-named output bug fixed: output filenames now come from field1 (or original filename if field1 blank) + field2, joined with nothing between
- field 2 required; empty on any node blocks the whole run before separation starts, with an error naming the node
- batch collisions from a typed field 1 are accepted — no guard added, per lock
- `docs/00-locked-spec.md` and `planner.py`/`runner.py`/`types.py`/`test_planner.py` untouched, as instructed

## TEST RESULT

`python -m pytest engine/test_planner.py` could not run — pytest is not
installed in `app/.venv` (no pip either; venv only has the packages in
`requirements.txt`: PySide6, torch). This is an environment gap, not
something the spec's edits caused.

`test_planner.py`'s own docstring says it's stdlib-only unittest and
names its own invocation: `python -m unittest app.engine.test_planner -v`.
Ran the equivalent from the `app/` directory (that module path needs
`core`/`engine` importable, which requires running from inside `app/`):

    cd Stemsplitter/app && .venv/bin/python -m unittest engine.test_planner -v

Result: **1 test, OK.** Planner untouched and still passes, confirming
this session's edits didn't touch it.

## BRANDON'S TODOS

- pytest is absent from `app/.venv` and not in `requirements.txt` — flagging only, not fixed (not named in this buildspec)

## CLOSER REVIEW

- Gets copy of review, not a contract.
- Confirm the pytest-vs-unittest substitution was acceptable — [action: Brandon/closer]
- `docs/00-locked-spec.md` node schema still shows `filename_template`, superseded by `filename_field1`/`filename_field2` per this spec's own NOT CHANGING note — reconciliation is the Closer's/Brandon's call, not touched here
