# SESSION REVIEW — Stemsplitter — 2026-08-14 15:44–17:01 EDT

    task:    design session for the Stemsplitter subproject
    author:  session agent (Opus)
    reads:   the five buildplan files listed below

Design session only. No subagents spawned. No build started.

## EDITS

- [00-locked-spec.md](00-locked-spec.md) — LOCKED spec: panes, run config dict, flag whitelist, models, NOT BUILDING
- [01-session-foundation-intake.md](01-session-foundation-intake.md) — session 1 buildplan
- [02-session-panes.md](02-session-panes.md) — session 2 buildplan
- [03-session-engine.md](03-session-engine.md) — session 3 buildplan
- [04-session-wire-verify.md](04-session-wire-verify.md) — session 4 buildplan
- [../../INDEX.md](../../INDEX.md) — Stemsplitter subproject section added
- [../../SESSIONLOG.md](../../SESSIONLOG.md) — design session entry appended
- [../../TODO.md](../../TODO.md) — Stemsplitter open threads section added

## STRAY FILES

None. Nothing written to scratchpad, nothing left outside `Stemsplitter/docs/`.

## GOALS DONE

- App scoped in one session, as Brandon required
- Stack chosen by Brandon: Python + PySide6
- Build split into four sessions, ten agents, every agent under 200k
- The one real seam named and frozen: the run config dict
- NOT BUILDING list written — the anti-drift device Brandon asked for

## BRANDON'S TODOS

- **Which model weights ship.** Marked OPEN in the locked spec. Session 1
  stops and asks rather than choosing. The sizes in that file came from
  memory and are unverified — confirm against the real checkpoints before
  anything is packaged.
- **Style note before Session 2.** Three parallel UI agents with no shared
  visual reference will produce three mismatched panes. Write the note, or
  run Session 2 in series and pay for the extra session.

## CLOSER REVIEW

Gets a copy of this review, not a contract.

- **New subproject exists** — `Stemsplitter/` under Audio Diffusion Harness,
  carrying only `docs/`. Resolved: no separate docset. It is a subproject;
  the parent folder's docset covers it.
- **The locked spec is a decision record.** Everything in it came from
  Brandon in this session, except the one item explicitly marked OPEN.
  Resolved: stays in `docs/`. `references/` is Brandon's space, not
  offered to.
- **Warm start** — Audio Diffusion Harness was touched this session and its
  MEMORY.md block needs rewriting. Next move is the two gates above, not a
  build session. Closer: Brandon.
- **CLAUDE.md map** — resolved: `Stemsplitter/` added to the parent
  folder's MAP, nav section states it's a subproject covered by this
  docset.
