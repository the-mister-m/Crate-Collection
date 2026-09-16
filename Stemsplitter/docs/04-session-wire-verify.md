# SESSION 4 — WIRE + VERIFY

    task:    Stem Splitter build — session 4 of 4
    author:  session agent (Opus), design session 2026-08-14
    reads:   00-locked-spec.md  ← read this first, all of it
             01-session-foundation-intake.md
             02-session-panes.md
             03-session-engine.md
    feeds:   nothing. This is the last session.

Read the locked spec before anything else. Do not add to it.

---

## GOAL

Join the two halves. The panes emit a run config dict; the engine consumes
it; progress and errors come back to the UI. Then prove it works.

---

## WAVES

    WAVE 1 — wire                          series
      panes → run config dict → engine
      progress from the runner back into the UI
      the error report surfaced when the batch finishes

    WAVE 2 — verify                        series, after 1
      one real audio file
      three output nodes
      two different models
      confirm: 2 separations not 3, 3 files written, correct
      directories, correct names, correct stems present and absent

---

## CARRIED FROM SESSION 2 — for Wave 1

Three findings from Session 2's parallel build, handed to Wave 1 so it isn't
rediscovering them by reading code cold:

- **Node numbering disagrees between panes.** `node_list.py` numbers cards by
  fixed creation order. `output_pane.py` renumbers by live list position.
  They agree until a middle node is removed, then they don't. Wire one
  convention — stable id assigned at creation, title never renumbered — and
  make both panes use it.
- **`get_node_config()` matches.** `node_controls.py` exposes it as designed;
  `node_list.py`'s `NodeCard.get_config()` already calls it correctly.
  Nothing to fix, just confirm at wire time.
- **`main_window.py` carries two leftovers** from three agents editing it
  blind in parallel: a stale docstring ("PARAMS and OUTPUT stay placeholders")
  and a dead `_make_pane()` helper now that both are wired. Wave 1 is the
  first agent with the whole file in view — clean both up as part of wiring,
  not a stop-and-ask.

## SEAMS

    in:   both halves, already built
    This session exists to violate the seam. That is its job and also
    its danger.

---

## THE RULE FOR THIS SESSION

Anything that needs changing behind the seam **stops and asks Brandon.**

An integration agent's instinct is to reach into Session 2 or Session 3
and quietly reshape it so the wiring gets easier. That undoes two sessions
of isolation in one edit. If the panes emit something the engine can't
take, that is a finding to report, not a thing to fix unilaterally.

---

## BUDGET

    2 agents, series
    ~80k session context, ~45k per agent

---

## DRIFT — MED-HIGH

- rewriting Session 2 or 3 to simplify the wiring
- adding features that only become visible once it's working end to end
  (a cancel button, a queue, a history) — all in NOT BUILDING
- expanding verify into a test suite. Verify is the one scenario named
  above and nothing more.

---

## DONE WHEN

- drop a folder, check some files, build three nodes, hit go
- files land where the nodes say, named as the templates say
- the mixed files contain the checked stems and not the unchecked ones
- progress moved while it ran
- a bad file was skipped and named in the error report
- the app is closed and reopened, and it opens empty — no persistence
