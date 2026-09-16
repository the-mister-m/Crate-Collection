# Redpen — convert.py

Target: [convert.py](../convert.py) — read whole, not edited.

Ordered by how likely it bites Brandon in real use.

---

## 1. Dropping two stems with the same filename silently loses one

`convert.py:466` — `dest = UPLOAD_DIR / Path(item.filename).name`

Stem workflows are full of `Vocals.wav`, `Kick.wav`, `Bass.wav` in different song
folders. Drop `SongA/Vocals.wav` and `SongB/Vocals.wav` in one gesture: the second
`item.save(dest)` overwrites the first in the staging dir. `saved` now holds the
same path twice. The batch converts it, then reports the second as
**SKIPPED — output already exists**.

Brandon reads that as "already done." One song's vocal never got converted and the
message doesn't say so.

Question: what should the staged name be so two same-named stems stay two files —
and should the results row say which source folder it came from?

(The native-picker path has the same collision but reports it honestly: two real
distinct sources, one output name, second skipped. That one is working as locked.)

## 2. Nothing in the browser handles a failed fetch — the UI just stops

No `try`/`catch` and no `res.ok` check anywhere in the page script.

- `convert.py:314` / `:319` — if `/pick-files` 500s, `r.paths` is undefined,
  `.length` throws, the click does nothing. No message.
- `convert.py:331` — dropping a **folder** (or a file the browser can't read)
  makes the upload throw; `drop.textContent` is left reading `staging…` forever.
- `convert.py:377` — worst one. If `/status/<id>` 404s (server restarted, job id
  gone), the body is `{error:...}`: `s.pct` is undefined → bar width becomes
  `"NaN%"`, `s.results.map` throws, the interval keeps firing every 250ms
  forever, and Convert stays disabled. Brandon's only recovery is a page reload,
  with no indication why.
- `convert.py:474` — `/estimate` has no guard. A `value` outside `VBR_KBPS`
  (0–9) is a `KeyError` → 500 → `.json()` throws → the estimate silently
  freezes on stale numbers.

Question: where's the one place a failed call should surface, so every one of
these ends up as red text in `#jobhint` instead of a frozen widget?

## 3. Filenames go into `innerHTML` unescaped — so does ffmpeg's error text

`convert.py:350`, `convert.py:386-388` — `${f.name}`, `${f.reason}`, `${r.error}`.

`#` and `'` are harmless here, so the `gangster's pardise` files are fine. `&` and
`<` are not. A stem named `Drums & Bass.wav` renders wrong; anything with `<`
eats the rest of the row.

The sharper edge is `f.reason`: that's raw ffmpeg stderr. Angle brackets in an
ffmpeg diagnostic will swallow the message. Loud failure becomes a blank cell —
the exact inversion of the locked requirement.

Question: does this list want `textContent` per cell, or one escape helper the
three interpolation sites share?

## 4. The AppleScript pickers can't tell cancel from failure

`convert.py:157-163` — `_osascript` returns `None` on any non-zero exit. User hit
Cancel (-128) and "System Events isn't permitted / script broke" are the same
value. `convert.py:315` and `:320` both treat falsy as "do nothing."

So if macOS ever denies the automation prompt, the button is inert and there is no
message anywhere. Untested path, and it's the single most likely source of a
"nothing happens when I click" report.

Also, untested and worth eyeballing in practice: `osascript` is a background app,
so `choose file` can open **behind** the browser window. `tell application
"System Events" to activate` (`:141`) activates System Events, but the dialog
belongs to osascript.

Question: is `-128` worth branching on so a real picker failure reaches the page,
and does the dialog actually come to the front on Brandon's machine?

## 5. Stems above 48 kHz kill the whole batch

`convert.py:106-109` — no `-ar`, so the source rate passes through. LAME tops out
at 48 kHz. A 88.2k or 96k session export fails every file with an ffmpeg sample-rate
error. Loud, at least — but it's a whole batch of red.

Question: should the encoder pin a rate when the source is above 48k, or should
the estimate table flag it before Brandon clicks Convert?

Related, same lines: `-map_metadata -1` drops all tags. Deliberate for stems?

---

## Races — `convert.py:480-537`

Job state itself is clean. `_JOBS_LOCK` covers every read and write, `/status`
snapshots under the lock and copies `results`, the `track` closure binds `job_id`
by default arg, and `pct = (index + file_pct) / total` is monotone because
`file_pct` is set to `1.0` before `index` advances and `index` ends at `len(paths)`
with `file_pct` at `0.0`. The 116.7% fix holds.

Two real ones:

**a. Two jobs, same output folder, same file → the "never overwrite" guarantee
breaks, and an existing file gets deleted.** `convert.py:95` checks
`out_path.exists()`; `convert.py:106+` writes it. Between those, a second job
passes the same check. Both encode to the same path. The loser hits
`convert.py:125-126` — `out_path.unlink()` — and deletes the file the winner is
producing. Trigger: two browser tabs, or reload mid-job and hit Convert again.
`#go` being disabled only guards one tab.

Question: what makes the no-overwrite promise hold at the filesystem rather than
at a check — `-n` on the ffmpeg call, a job-level lock on the output folder, or
just refusing a second job while one is running?

**b. `refresh()` responses can land out of order.** `convert.py:344` — toggling
mode/channels fast fires overlapping `/estimate` calls; a slow earlier response
overwrites a newer one and the live MB number is quietly wrong.

Question: worth a request counter, or is the estimate cheap enough to just debounce?

**c. Not a race, but adjacent:** `poll` (`convert.py:373`) is set without clearing a
prior interval, and `JOBS` is never pruned. Both only matter once (2) leaves an
interval alive.

---

## Shell / AppleScript injection — clean, no findings

Checked specifically because of the `#` and apostrophe filenames:

- `convert.py:140-154` — both scripts are constants. Nothing is interpolated into
  AppleScript. No injection surface.
- `convert.py:52`, `:111`, `:159` — all `subprocess` calls pass argument lists, no
  `shell=True`. Quotes, `#`, spaces, apostrophes all pass through untouched.
- `convert.py:466` — `Path(item.filename).name` strips traversal. Fine.
- Filenames starting with `-` are safe: the source is the value of `-i`, and the
  output path is always absolute (it comes from `POSIX path of` a chosen folder).

One theoretical gap: `convert.py:145` joins paths with `linefeed` and `:171` splits
on it. macOS permits `\n` in a filename. A stem named that way would split into two
garbage paths. I'd call it not worth fixing unless you've seen it.

---

## Smaller, non-blocking

- `convert.py:111-122` — `stderr=PIPE` is only drained after `proc.wait()`. If
  ffmpeg ever writes more than the pipe buffer (~64KB) to stderr, it blocks, stops
  emitting progress, and the `for line in proc.stdout` loop hangs forever with no
  timeout. `-loglevel error` makes it unlikely, not impossible. A hang is the
  quietest failure there is.
- `convert.py:460-469` — no extension filter. A dropped `.mp3` or `.aif` gets
  staged and estimated like a wav. Drop zone says "wav files"; nothing enforces it.
- `convert.py:466` — `item.filename` can be `None`; `Path(None)` is a `TypeError`
  → 500 → see finding (2).
- `convert.py:409` — `UPLOAD_DIR` is never cleaned. Grows across every session.
- `convert.py:412-416` — `_DURATIONS` is keyed by path and never invalidated.
  Re-drop an edited file to the same staged path and the estimate uses the old
  duration.
- `convert.py:60` — `float(raw)` is outside the `EngineError` guard. If ffprobe
  ever prints `N/A`, that's an uncaught `ValueError` → 500.
- `convert.py:315` / `:333` — picker and drag/drop each **replace** `paths`. They
  can't be combined, and a cancelled picker leaves the previous selection with no
  visual change. Locked req says both input paths exist; it doesn't say whether
  they add. Confirm which you meant.
- `convert.py:95` — the estimate table shows MB for files that will be skipped.
  Brandon sees "182 MB", clicks, gets six skips. The skip is loud, per spec; the
  estimate just didn't know.
- `convert.py:540-546` — `connect_ex` then `app.run` is a TOCTOU, and a port bound
  on a non-loopback interface reads as free. Vanishingly unlikely locally.

**Fine as built, confirmed by reading:** the never-overwrite check and its
single-job behavior, progress math, VBR/CBR/320 ceiling, mono/stereo plumbing
(`-ac`), the estimate formula and its mono VBR factor, `/convert` 400 on a bad
folder, job locking, tool-presence check at startup, and the absence of any shell
interpolation.

---

## Outside the code

Two things that have nothing to do with Python.

The tool's job is to be trusted with a folder of finished work. Every finding above
that actually matters is the same shape: the tool knows something went sideways and
doesn't say it out loud. Brandon already named this as the requirement. The gap
isn't that the tool fails — it's that the browser is where the truth goes to die,
and the browser is the untested half. Worth one manual pass through the ugly paths
with a deliberately broken file, just to watch what the page does.

Second: the strongest thing about this build is that the destructive operation was
designed out rather than guarded. It never overwrites because it never tries. The
one place that promise wobbles is the one place it reached for a cleanup
(`unlink`) instead. That's the pattern to keep — when something wants to delete, it
usually means the design got a little too clever a line earlier.

---

SESSION REVIEW — Stem Converter — [timestamps: ask Brandon]

EDITS
- [docs/redpen-review-convert.md](redpen-review-convert.md) — this review; only file written
- [convert.py](../convert.py) — read only, not modified

STRAY FILES
- none

GOALS DONE
- Full read of convert.py, all ~450 lines
- Defect hunt across untested paths: osascript pickers, drag/drop upload, browser JS
- Race audit of job/thread code
- Injection/quoting audit — clean, no findings
- Locked-requirement check — one wobble, the concurrent-job overwrite window

BRANDON'S TODOS
- Decide staged-filename scheme for same-named stems from different folders
- Decide where failed fetches surface in the UI
- Confirm whether picker and drag/drop should combine or replace
- Confirm the native dialog comes to the front on your machine
- Confirm `-map_metadata -1` (all tags stripped) is intended for stems

CLOSER REVIEW
- Gets copy of review, not a contract.
- Findings are questions, not approved changes — nothing here is authorized until Brandon says so — who: Brandon
- No edits to convert.py were made or requested — who: closer
