# SESSION 5 — OUTPUT NAMING (patch)

    task:    fix uuid-named output files; replace the single filename
             template field with Brandon's two-field naming, per
             session diagnosis 2026-08-15
    author:  buildspec agent, 2026-08-15
    reads:   00-locked-spec.md  ← THE RUN CONFIG DICT, node schema
             04-session-wire-verify.md  ← main_window.py's current shape
    feeds:   nothing planned after this. Standalone patch on a shipped app.

Read 00-locked-spec.md's THE RUN CONFIG DICT section before anything else.
This session's node schema change (below) supersedes that file's
`filename_template` key for this one field. The lock file itself is NOT
edited — see NOT CHANGING.

---

## THE BUG (diagnosed already — do not re-diagnose)

`core/intake.py convert_to_wav()` names every converted file
`<uuid4hex>.wav`. That uuid rides untouched through `Job.file` and lands
in the output filename via `mixer.py`'s `Path(jr.job.file).stem`.
`IntakeFile.original_path` already carries the real name — it just never
travels past the UI row.

---

## LOCKED DECISIONS — verbatim, do not add to them

- The old single "Filename template" field with `{track}_{mix}.{ext}` GOES
  AWAY entirely.
- Replaced by TWO text fields on each output card.
- FIELD 1: greyed placeholder showing the track's own title. Left empty =
  each file uses its own original filename (basename, no extension). Typed
  in = that literal text is used for EVERY file in the run. Batch
  collisions from this are ACCEPTED — no guards, no warnings, no
  uniquifying suffixes.
- FIELD 2: REQUIRED. Replaces the generated stem list (was
  `"bass+drums+other"`). Empty on ANY node = the run is BLOCKED with an
  error before separation starts. Take the error, do not work around it.
- The two fields join with NOTHING between them. No underscore, no space.
  Brandon types his own separator into field 2 if he wants one.
- Extension still comes from the node's existing "format" setting.
- Example: `"01. The Propaganda.mp3"` dropped, field 1 empty, field 2
  `" drums"`, format mp3 → `"01. The Propaganda drums.mp3"`.

---

## THE ROUTE — patch, not rewrite

`run_config["files"]` stays a plain `list[str]` of wav paths.
`planner.py`, `runner.py`, `types.py`, `test_planner.py` are UNTOUCHED —
they never cared about the original filename and still don't.

One new key rides alongside `"files"` in the run config dict:

```python
"original_names": {wav_path: original_stem, ...}
```

built in the same function that builds `"files"`, from the same checked
rows, so the two are guaranteed to agree — this is a second place the
truth lives, deliberate, accepted.

---

## WAVE 1 — carry the original filename: intake → run config → mixer

**`app/ui/intake_pane.py`**
- Add `from pathlib import Path` to the imports.
- Add a module-level constant near the top: `_ORIGINAL_NAME_ROLE =
  Qt.ItemDataRole.UserRole + 1`.
- In `_ingest()` (current lines 85–94), after the existing
  `item.setData(Qt.ItemDataRole.UserRole, intake_file.wav_path)` (line 93),
  add: `item.setData(_ORIGINAL_NAME_ROLE, Path(intake_file.original_path).stem)`
  — stem, not `display_name` (`display_name` keeps the extension).
- Add a new method, right after `get_checked_paths()` (after current line
  121): `get_checked_original_names(self) -> dict[str, str]`. Same
  checked-row loop as `get_checked_paths()`, returns
  `{wav_path: original_stem}` for every checked row.

**`app/ui/main_window.py`**
- In `_build_run_config()` (current lines 98–122): call
  `self.intake_pane.get_checked_original_names()` right where `files` is
  already fetched (line 101), store it, and add it to the returned dict
  (line 117–122) as `"original_names": original_names`.

**`app/engine/pipeline.py`**
- In `run()` (current lines 44–56): `mix_and_write` gets a third
  positional arg. Change the call on line 52 to pass
  `run_config["original_names"]` between `nodes_by_id` and `progress_cb`.

**`app/engine/mixer.py`**
- `mix_and_write()` signature (current lines 52–56): add
  `original_names: dict[str, str]` as a new parameter, positioned between
  `nodes_by_id` and `progress_cb`.
- Line 66: replace `track_name = Path(jr.job.file).stem` with
  `track_name = original_names[jr.job.file]`. Direct indexing, no
  `.get()` fallback — `jr.job.file` is always a key of `original_names`
  by construction (both built from the same checked rows in the same
  main_window function). A `KeyError` here means Wave 1 was wired wrong
  somewhere upstream, not a real-world case to guard.

---

## WAVE 2 — output_pane.py: one field becomes two

**`app/ui/output_pane.py`**
- Remove `DEFAULT_FILENAME_TEMPLATE` (line 37).
- In `add_node()`, replace the single template row (current lines
  119–121: `template_edit` + `form.addRow("Filename template",
  template_edit)`) with two `QLineEdit`s and two form rows:
  - Field 1: no default text, placeholder text conveying "uses the
    track's own filename when left blank" (exact wording is not locked —
    your call, keep it short).
  - Field 2: no default text, no placeholder needed. Label it as
    required in the row label text (e.g. "Filename suffix (required)") —
    exact wording your call, requiredness is not.
- Replace `card._template_edit = template_edit` (current line 126) with
  `card._field1_edit` / `card._field2_edit` handles on the card, same
  pattern.
- `get_output_config()` (current lines 142–146): return
  `"filename_field1": handle._field1_edit.text()` and
  `"filename_field2": handle._field2_edit.text()` in place of
  `"filename_template"`.

---

## WAVE 3 — mixer.py: `_render_filename` becomes the two-field join

**`app/engine/mixer.py`**
- Update the module docstring's "filename_template variables" block
  (current lines 15–21) to describe field 1 / field 2 instead of
  `{track}_{mix}.{ext}`.
- Replace `_render_filename()` (current lines 44–49) entirely:
  ```python
  def _render_filename(field1: str, field2: str, track: str, ext: str) -> str:
      stem = field1 if field1 else track
      return f"{stem}{field2}.{ext}"
  ```
  No `{mix}`/`{track}`/`{ext}` template parsing, no `KeyError` case — it's
  a plain join now.
- Update the call site (current line 105) to
  `_render_filename(node["filename_field1"], node["filename_field2"],
  track_name, ext)`. Drop the `checked` argument from this call only —
  `checked` (the sorted stem-name list) is still used earlier, in the
  stem-summing loop (current lines 91–101); it just no longer feeds the
  filename.

---

## WAVE 4 — main_window.py: block the run if field 2 is empty anywhere

**`app/ui/main_window.py`**
- In `_build_run_config()` (current lines 98–122), inside the node loop
  (lines 106–112), after computing `output_config`, check
  `output_config["filename_field2"]`. If falsy, raise `ValueError` with a
  message naming which node is missing it — use that node's title (the
  output card's `_header_label.text()`, same handle already in scope as
  `output_card`) so the error is readable, not just an id.
- In `_on_go()` (current lines 126–141), wrap the
  `self._build_run_config()` call (line 127) in `try/except ValueError`.
  On catch: set `_run_status_label` text and show `QMessageBox.critical`
  with the exception message, same pattern already used in `_on_failed`
  (lines 181–184). Return without starting the worker. Leave the existing
  `if run_config is None:` branch (no files / no nodes) exactly as is —
  it's a separate case, not this one.

---

## NOT CHANGING

- `app/engine/planner.py`, `app/engine/runner.py`, `app/engine/types.py`,
  `app/engine/test_planner.py` — untouched. `run_config["files"]` shape
  is unchanged; they never read `original_names`.
- `app/core/intake.py` — `IntakeFile` already has everything needed.
  Untouched.
- `app/ui/node_list.py`, `app/ui/node_controls.py`, `app/ui/run_worker.py`
  — untouched.
- No separator character inserted between field 1 and field 2, ever.
- No collision guard, warning, or uniquifying suffix for repeated field-1
  batch output names. Brandon accepted this.
- `docs/00-locked-spec.md` — NOT edited by this session. Its node schema
  still shows `filename_template`; that key is superseded by
  `filename_field1`/`filename_field2` for this feature only. Flagging the
  mismatch here for the Closer/Brandon to reconcile — the builder does
  not touch the lock file.
- `docs/02-session-panes.md`, `docs/03-session-engine.md` — session
  history, append-only, never rewritten to match new reality.

---

## DRIFT

- adding a default separator, a collision guard, or a "smart" dedup for
  field 1 — explicitly forbidden above
- editing `docs/00-locked-spec.md` to "fix" the node schema
- reaching into `planner.py`/`runner.py`/`types.py` because the two-places
  -truth pattern (`files` + `original_names`) feels wrong — it's accepted
  as-is, not a thing to unify
- keeping `filename_template` around alongside the two new fields "for
  compatibility" — it is fully replaced, not supplemented
- turning Wave 4's validation into general form validation (e.g. also
  blocking on empty destination dir) — only field 2 is locked as required

---

## BUDGET

    1 agent, series waves 1 → 2 → 3 → 4
    ~60k context expected; ceiling 275k

Checkpoint after each wave: confirm the wave's own files match this spec,
then check context used. Under 200k — continue to the next wave without
asking. Over 200k — stop and write the handoff report; do not push into
the next wave.

---

## DONE WHEN

- drop `"01. The Propaganda.mp3"`, leave field 1 empty, format mp3,
  field 2 `" drums"` → output file is `"01. The Propaganda drums.mp3"`,
  not a uuid
- typed field-1 text is used literally, identically, for every file in
  that run — including when two files collide and overwrite (accepted)
- a node with field 2 empty blocks the whole run before separation
  starts, with a readable error naming that node
- format/extension still comes from the node's format setting, unchanged
