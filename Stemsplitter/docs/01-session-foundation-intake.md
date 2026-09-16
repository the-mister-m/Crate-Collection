# SESSION 1 — FOUNDATION + INTAKE

    task:    Stem Splitter build — session 1 of 4
    author:  session agent (Opus), design session 2026-08-14
    reads:   00-locked-spec.md  ← read this first, all of it
    feeds:   02-session-panes.md

Read the locked spec before anything else. Do not add to it.

---

## GOAL

An app window that opens, knows where demucs and ffmpeg are, knows what
device it's running on, and lets you drop files in and check the ones you
want.

Nothing runs yet. Nothing separates yet. The intake pane is real, the other
two panes are empty placeholders.

---

## WAVES

    WAVE 1 — shell                          series
      PySide6 window, three-pane layout skeleton
      locate demucs and ffmpeg
      detect device → "cuda" | "mps" | "cpu"
      package the model weights (see OPEN below)

    WAVE 2 — intake pane                    series, after wave 1
      drop target: individual files OR a whole folder
      accept anything ffmpeg reads; convert to wav on the way in
      one row per file, checkbox each
      select / deselect all
      only checked files enter the run config

Series, not parallel — both agents touch the same window file.

---

## OPEN — STOP AND ASK

The locked spec does not say which model weights ship. Before packaging
anything, confirm with Brandon:

- which models ship
- their real on-disk sizes (the spec's figures are approximate)

Do not choose. Ask.

---

## SEAMS

    in:   nothing. This is the root session.
    out:  the checked file list (absolute paths)
          the device string
          Both become fields of the run config dict — see 00-locked-spec.md.

---

## BUDGET

    2 agents, series
    ~70k session context, ~40k per agent

---

## DRIFT — LOW

Everything here is concrete and verifiable. The window either opens or it
doesn't; demucs is either found or it isn't.

The one thing to watch: an agent building intake will want to add a file
preview, a duration column, a format badge, a sort. None of that is in the
spec. One row, one name, one checkbox.

---

## DONE WHEN

- the window opens with three panes visible
- dropping a folder fills the intake list
- checking and unchecking works, select/deselect all works
- the app can print its device string and the paths to demucs and ffmpeg
- nothing else happens when you click anything
