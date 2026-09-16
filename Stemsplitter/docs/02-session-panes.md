# SESSION 2 — PARAMS + OUTPUT PANES

    task:    Stem Splitter build — session 2 of 4
    author:  session agent (Opus), design session 2026-08-14
    reads:   00-locked-spec.md  ← read this first, all of it
             01-session-foundation-intake.md  (the window it plugs into)
    feeds:   04-session-wire-verify.md

Read the locked spec before anything else. Do not add to it.

---

## GOAL

The middle and right panes, fully built, driven by mock data. Clicking
around produces a correct run config dict and nothing else. No engine
exists yet and this session does not build one.

---

## WAVES

    WAVE A — node list chrome              parallel
      the scrollable node column
      "add output" appends a node
      expand / collapse a node
      remove a node

    WAVE B — node controls                 parallel
      inside one node: model dropdown, stem checkboxes with
      select/deselect all, shifts, overlap, segment, format,
      mp3 bitrate, bit depth
      stem checkbox names come from the selected model

    WAVE C — output pane                   parallel
      per node: destination directory picker
      per node: filename template field

Three agents, genuinely parallel. No shared state. Each works against the
mock data, not against the others' code.

---

## BEFORE THE WAVE LAUNCHES

Two things are frozen in writing or this session fails:

1. **The run config dict schema.** Already locked in 00-locked-spec.md.
   No agent adds a key. No agent renames a key.
2. **A style note.** Three parallel agents building UI with no shared
   state will produce three different-looking panes. That is a taste
   problem, not a context problem, and more tokens will not fix it.
   Whoever runs this session writes the style note first — fonts,
   spacing, control sizes, colours — or accepts three mismatched panes.

If the style note isn't written, run this session in series instead and
pay for the extra session.

---

## SEAMS

    in:   the file list and device string from Session 1
    out:  a complete, valid run config dict — see 00-locked-spec.md

The dict is the whole contract. Session 3 never reads this session's code
and this session never reads Session 3's.

---

## BUDGET

    3 agents, parallel
    ~90k session context, ~50k per agent

---

## DRIFT — HIGH. The riskiest session.

UI is subjective, so agents invent. Expected failures:

- adding controls that aren't in the flag whitelist
- "improving" the dict — extra keys, renamed keys, nested structures
- restyling each other's panes to match their own
- building a preset save/load because a node list obviously wants one
  (it is in NOT BUILDING)
- wiring a real demucs call because mock data feels incomplete

An agent that thinks the dict needs a change stops and asks Brandon.

---

## DONE WHEN

- "add output" produces a node; nodes collapse, expand, scroll, delete
- every whitelisted node-level flag has a control
- stem checkboxes match the selected model's stem names
- each node has a destination directory and a filename template
- a button prints the run config dict, and it validates against the
  schema in 00-locked-spec.md
- nothing calls demucs
