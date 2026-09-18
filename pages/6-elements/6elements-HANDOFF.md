# HANDOFF — 6 Elements of Sound, worksheets + listening page

**Date:** 2026-09-17
**Owner:** Brandon
**State:** built, unapproved. Nothing here is finished until Brandon signs off on the
gap list at the bottom.

---

## WHAT THIS IS

Brandon teaches 7th grade. The first three weeks of the course train students to use six
vocabulary terms — **Pitch, Volume, Duration, Space, Timbre, Envelope** — so that by week
four they can describe what they hear in **split stems** of real songs, with FFTs on
screen alongside.

The teaching problem he named: *"my questions are vague enough for the kids to cop out."*
Students answer "idk" because describing a sound requires vocabulary they don't own yet.
Everything in these files exists to remove the cop-out.

---

## FILES

| File | What it is | State |
|---|---|---|
| [6elements.html](6elements.html) | Brandon's interactive page. Six sections, live Web Audio. **Not written by an agent — do not edit without asking.** | his |
| [6elements-worksheet-v1.md](6elements-worksheet-v1.md) | Paper worksheet for the interactive page | **2 known bugs, unfixed** |
| [6elements-worksheet-v1-KEY.md](6elements-worksheet-v1-KEY.md) | Answer key for the above | done |
| [6elements-listening.html](6elements-listening.html) | A/B listening page, 14 questions, synth only | built |
| [6elements-listening-week1.md](6elements-listening-week1.md) | Week 1 worksheet for the listening page | built |
| [6elements-listening-week1-KEY.md](6elements-listening-week1-KEY.md) | Answer key for the above | built |

---

## BRANDON'S SPECS — the source of truth

These came from him. Do not reinterpret them.

1. **Printable paper, computer screen.** They work on the machine, they write with a
   pencil. The screen makes sound and pictures; the paper holds thinking.
2. **Never leave a blank a shrug fits in.** Circle-one, word bank, direction, or number.
   Open response only at the end, after the small wins.
3. **Scaffold runs backwards from the obvious direction** — visuals go on at **full**
   strength in week 1 and get **taken away** later. Brandon corrected an earlier plan
   that had it the other way.
4. **Four dials, faded one at a time** — PICTURE, CHOICES, WORDS, SIGNAL. Never turn two
   down in the same week.
5. **Multiple questions per element**, at varying taxonomy rungs.
   `1 IDENTIFY · 2 DIRECTION · 3 RANK · 4 BUILD · 5 EXPLAIN · 6 JUDGE`
6. **The FFT never fully goes away** — students will have FFTs on the stems in week 4.
   What fades is the *help inside* the picture, not the picture.
7. **Do not design the stem workflow yet.** Explicitly out of scope.

---

## WHAT WAS VERIFIED IN BRANDON'S CODE

Two answers were checked against [6elements.html](6elements.html) rather than guessed:

- **Partials scale, they don't shift.** Each partial is `(i+1) × 100 × MASTER PITCH`, so
  raising master pitch multiplies them all and the spacing spreads. The *ratios* lock,
  which is why the timbre survives a pitch change. This is the biggest idea in the unit.
- **Panned echoes stay put.** The delay is mono and the panner sits in front of it, so a
  hard-left pan keeps the echoes hard left. Students expect ping-pong. Being wrong here
  is the lesson about signal flow order.

---

## KNOWN ISSUES — not fixed, awaiting Brandon

**In [6elements-worksheet-v1.md](6elements-worksheet-v1.md):**

1. **Question 6.3 is factually wrong.** It says two ADSR stages happen while the trigger
   is ON and two happen after. It is **three and one** — A, D, and S are all trigger-on,
   only R is after. Replacement wording is in the key.
2. **3.2 uses S for "sudden" and H for "held,"** which collides with **S = Sustain** in
   the Envelope section two pages later. Three fixes are laid out in the key. Brandon has
   not picked one.

**In [6elements-listening.html](6elements-listening.html):**

3. **The answers are readable in the page source.** Each bank entry carries
   `el:"TIMBRE"` and similar. Any student who opens View Source has the key.

---

## WHAT WAS STRIPPED, AND WHY

An earlier build shipped six things Brandon never asked for. The failure mode was
treating **unanswered questions as decisions to make** — he had said outright he wanted
to see the year plan before deciding, then said "build it," and that was read as
permission to resolve the open items. It was not. All six are out:

- VISUALS FULL/RAW/MIN switch — page is now hardcoded to the week-1 state
- Trap question (A and B identical)
- Keyboard shortcuts
- "Go back to question 7" item at the end of the worksheet
- Quick score sheet in the key
- A forced count of 12 questions

**On the count:** 12 was an agent's number. With the trap gone the bank sits at **14**,
which is what the spec produces by itself — 6 elements × 2 rungs, plus one EXPLAIN and
one JUDGE. It falls out rather than being chosen.

---

# OPEN — NEEDS BRANDON'S APPROVAL

Everything below was filled in without instruction. None of it is approved.

## The one to look at first

**The worksheet is ordered by rung, not by question number.** Part One is questions
**1, 3, 5, 7, 9, 11**; Part Two is **2, 4, 6, 8, 10, 12**. Students walk the screen
1→14 in order but their paper jumps around.

The reason: it groups all IDENTIFY questions under one instruction and all DIRECTION
questions under another. The cost: a 12-year-old hunting for question numbers, which is
the exact friction that makes them quit. **Fix is to renumber the bank** so Part One is
1–6 and Part Two is 7–12.

## Page — build decisions

| Gap | What was done |
|---|---|
| Visual design | Matched Brandon's `:root` tokens and panel/screw/screen classes |
| Navigation | One question at a time, prev/next — not all 14 on one page |
| What's on screen | Question number only. No question text, no answer choices |
| Spectrum source | Real `AnalyserNode`, not a drawn approximation |
| Spectrum axis | 0–4 kHz linear, so partials space evenly |
| Trace behavior | Peak-held and frozen, so A and B stay comparable after playing |
| **What "highlight" means** | Green shading wherever A and B differ. Brandon specified visuals-then-faded; he never specified what the highlight *is* |
| Button feedback | LED while playing, "HEARD" label after |
| Reverb / delay | Generated impulse response; delay 280 ms, 42% feedback |
| DEFAULT clip | 220 Hz, 5 partials, level 0.70, 1.2 s hold |

## Bank — content decisions

| Gap | What was done |
|---|---|
| The 14 clips' actual numbers | All agent-chosen. Brandon gave structure, not values |
| Q6 and Q12 reversed | Direction flipped from Q5/Q11 to catch pattern-guessers |
| Q5 / Q9 as a matched pair | Built to attack duration-vs-envelope from both sides |
| Ladder shape | 2 rungs per element + 1 explain + 1 judge |

## Worksheet

| Gap | What was done |
|---|---|
| Word bank placement | One table at the top. Brandon was asked this earlier and never answered |
| Header | Name / Period / Date |
| "idk is not an answer" | Printed in the instructions |
| Inline hints | Pointer lines under Q7, Q9, Q11 telling them where to look |

## Key

| Gap | What was done |
|---|---|
| "CREDIT IF" language | Agent framing for the opinion questions |
| Half-credit / no-credit bands | Invented on Q13 |
| Note length and tone | Brandon asked for notes; the ones written are long |

---

## OPEN QUESTIONS BRANDON HAS NOT ANSWERED

- How many weeks is the course, and what comes after stem analysis? The four-dial fade is
  only mapped through week 4.
- Which songs is he splitting? Knowing the stems changes which vocabulary gets drilled
  hardest in weeks 1–3.
- Envelope-drawing sheets — he said he's thinking about it. The reasoning: the FFT gives
  them **frequency**, an envelope graph gives them **time**, and drawing dodges the
  vocabulary problem entirely because a kid who can't say "slow attack" can still draw a
  slow ramp. Not started.
- Morse code for rhythmic duration — his idea, and it fits: dots and dashes are sudden
  and sustained with every other element held constant. Not started.

---

## FOR WHOEVER PICKS THIS UP

**Do not build ahead.** Brandon gates every decision and every action. A question he
hasn't answered is not an invitation to answer it — leave the hole and say it's open.

Do not edit [6elements.html](6elements.html). It's his.
