#!/usr/bin/env python3
"""Stem Converter -- wav to mp3 on a local server.

Wave 1: encode engine only. No server, no UI.
Run directly to self-test against one file.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import uuid
from collections import Counter
from pathlib import Path

from flask import Flask, Response, jsonify, request

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")

# LAME VBR average kbps, stereo source
VBR_KBPS = {0: 245, 1: 225, 2: 190, 3: 175, 4: 165,
            5: 130, 6: 115, 7: 100, 8: 85, 9: 65}

# CBR tiers offered in the UI -- 320 is the mp3 ceiling
CBR_KBPS = [128, 160, 192, 224, 256, 320]

# mono VBR settles below the stereo average; CBR does not
MONO_VBR_FACTOR = 0.6

# ffmpeg -progress emits out_time=HH:MM:SS.ffffff
_OUT_TIME = re.compile(r"^out_time=(\d+):(\d\d):(\d\d\.\d+)$")


class EngineError(RuntimeError):
    """Tooling missing or ffmpeg refused the job."""


def check_tools() -> None:
    """Raise if ffmpeg/ffprobe are not on PATH."""
    missing = [n for n, p in (("ffmpeg", FFMPEG), ("ffprobe", FFPROBE)) if not p]
    if missing:
        raise EngineError(f"not found on PATH: {', '.join(missing)}")


def probe_duration(src: Path) -> float:
    """Seconds of audio in src."""
    check_tools()
    proc = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(src)],
        capture_output=True, text=True,
    )
    raw = proc.stdout.strip()
    if proc.returncode != 0 or not raw:
        raise EngineError(f"cannot read duration: {src.name}")
    return float(raw)


def effective_kbps(mode: str, value: int, channels: int) -> float:
    """Average kbps a setting produces."""
    if mode == "cbr":
        return float(value)
    if mode == "vbr":
        kbps = VBR_KBPS[value]
        return kbps * MONO_VBR_FACTOR if channels == 1 else float(kbps)
    raise EngineError(f"unknown mode: {mode}")


def estimate_bytes(duration: float, mode: str, value: int, channels: int) -> int:
    """Predicted mp3 size in bytes."""
    return int(effective_kbps(mode, value, channels) * 1000 * duration / 8)


def _encode_flags(mode: str, value: int) -> list[str]:
    """ffmpeg quality flags for the chosen mode."""
    if mode == "cbr":
        return ["-b:a", f"{value}k"]
    return ["-q:a", str(value)]


def encode_one(src: Path, out_dir: Path, *, mode: str, value: int,
               channels: int, on_progress=None) -> dict:
    """Encode one wav to mp3. Same stem name, .mp3 extension.

    Returns a result record: status is ok, skipped, or failed.
    Never overwrites -- an existing output is skipped and reported.
    """
    check_tools()
    out_path = out_dir / (src.stem + ".mp3")

    def record(status: str, reason: str, size: int | None = None) -> dict:
        return {"src": str(src), "name": src.name, "out": str(out_path),
                "status": status, "reason": reason, "bytes": size}

    # fast path -- covers every normal rerun without burning an encode
    if out_path.exists():
        return record("skipped", "output already exists")

    try:
        duration = probe_duration(src)
    except EngineError as exc:
        return record("failed", str(exc))

    # encode beside the target, claim the name atomically at the end
    tmp_path = out_dir / f".{src.stem}.{uuid.uuid4().hex[:8]}.part"
    cmd = [FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
           "-progress", "pipe:1", "-i", str(src),
           "-codec:a", "libmp3lame", *_encode_flags(mode, value),
           "-ac", str(channels), "-map_metadata", "-1",
           "-f", "mp3", str(tmp_path)]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
    except OSError as exc:
        return record("failed", f"cannot run ffmpeg: {exc.strerror}")

    for line in proc.stdout:
        match = _OUT_TIME.match(line.strip())
        if match and on_progress and duration > 0:
            hrs, mins, secs = match.groups()
            done = int(hrs) * 3600 + int(mins) * 60 + float(secs)
            on_progress(min(done / duration, 1.0))

    proc.wait()
    stderr = proc.stderr.read().strip()

    if proc.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        return record("failed", stderr or "ffmpeg failed")

    # link fails if the name was taken while we encoded -- never clobbers
    try:
        os.link(tmp_path, out_path)
    except FileExistsError:
        return record("skipped", "output already exists")
    except OSError as exc:
        return record("failed", f"cannot write output: {exc.strerror}")
    finally:
        tmp_path.unlink(missing_ok=True)

    if on_progress:
        on_progress(1.0)

    return record("ok", "", out_path.stat().st_size)


# ---------------------------------------------------------------- pickers

_PICK_FILES = '''
tell application "System Events" to activate
set picked to choose file with prompt "Select WAV files" with multiple selections allowed
set out to ""
repeat with f in picked
    set out to out & POSIX path of f & linefeed
end repeat
return out
'''

_PICK_FOLDER = '''
tell application "System Events" to activate
set picked to choose folder with prompt "Choose output folder"
return POSIX path of picked
'''


def _osascript(script: str) -> str | None:
    """Run AppleScript. None when the user cancels."""
    proc = subprocess.run(["osascript", "-e", script],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def pick_files() -> list[str]:
    """Native multi-select file dialog. Empty list on cancel."""
    out = _osascript(_PICK_FILES)
    if not out:
        return []
    return [line for line in out.splitlines() if line.strip()]


def pick_folder() -> str | None:
    """Native folder dialog. None on cancel."""
    return _osascript(_PICK_FOLDER) or None


# ---------------------------------------------------------------- page

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>Stem Converter</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; padding:24px; background:#141417; color:#e8e8ea;
         font:14px/1.5 -apple-system, system-ui, sans-serif; }
  .wrap { max-width:760px; margin:0 auto; }
  h1 { font-size:18px; font-weight:600; margin:0 0 2px; letter-spacing:.2px; }
  .sub { color:#8a8a93; font-size:12px; margin-bottom:22px; }
  .card { background:#1c1c20; border:1px solid #2a2a30; border-radius:10px;
          padding:16px; margin-bottom:14px; }
  .lbl { font-size:11px; text-transform:uppercase; letter-spacing:.8px;
         color:#8a8a93; margin-bottom:8px; }
  button { background:#2a2a32; color:#e8e8ea; border:1px solid #3a3a44;
           border-radius:7px; padding:8px 14px; font-size:13px; cursor:pointer; }
  button:hover { background:#34343e; }
  button:disabled { opacity:.4; cursor:default; }
  button.go { background:#3d6fd8; border-color:#3d6fd8; font-weight:600; }
  button.go:hover { background:#4a7ce4; }
  #drop { border:1.5px dashed #3a3a44; border-radius:8px; padding:20px;
          text-align:center; color:#8a8a93; font-size:13px; margin-top:10px; }
  #drop.over { border-color:#3d6fd8; background:#1e2333; color:#c8d4f0; }
  .row { display:flex; gap:18px; flex-wrap:wrap; align-items:flex-end; }
  .grp { display:flex; gap:6px; }
  .grp button.on { background:#3d6fd8; border-color:#3d6fd8; }
  select { background:#2a2a32; color:#e8e8ea; border:1px solid #3a3a44;
           border-radius:7px; padding:8px 10px; font-size:13px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  td { padding:6px 4px; border-bottom:1px solid #26262c; }
  td.sz { text-align:right; color:#8a8a93; width:90px; font-variant-numeric:tabular-nums; }
  td.nm { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:0; }
  .total { display:flex; justify-content:space-between; padding-top:10px;
           font-weight:600; font-variant-numeric:tabular-nums; }
  .hint { color:#8a8a93; font-size:12px; }
  .path { font-family:ui-monospace, Menlo, monospace; font-size:12px;
          color:#c8c8d0; word-break:break-all; }
  .bar { height:5px; background:#2a2a32; border-radius:3px; overflow:hidden; margin-top:6px; }
  .bar i { display:block; height:100%; background:#3d6fd8; width:0; transition:width .15s; }
  .ok { color:#5fc58a; } .skip { color:#e0a03c; } .bad { color:#e5564a; }
  .err { background:#38181a; border:1px solid #6b2a2a; color:#f2a8a2;
         border-radius:7px; padding:9px 12px; font-size:13px; margin-top:10px; }
  .warn { background:#382c15; border:1px solid #6b5326; color:#e7c68a;
          border-radius:7px; padding:9px 12px; font-size:13px; margin-top:10px; }
  .res { padding:5px 0; border-bottom:1px solid #26262c; font-size:13px;
         display:flex; gap:10px; }
  .res span:first-child { flex:1; overflow:hidden; text-overflow:ellipsis;
                          white-space:nowrap; }
</style>
<div class="wrap">
  <h1>Stem Converter</h1>
  <div class="sub">wav &rarr; mp3 &middot; local &middot; never overwrites</div>

  <div class="card">
    <div class="lbl">Input</div>
    <button onclick="chooseFiles()">Choose Files&hellip;</button>
    <span class="hint" id="count">nothing selected</span>
    <div id="drop">or drag wav files here</div>
  </div>

  <div class="card">
    <div class="lbl">Quality</div>
    <div class="row">
      <div>
        <div class="hint" style="margin-bottom:6px">Mode</div>
        <div class="grp" id="mode">
          <button data-v="vbr" class="on" onclick="setMode('vbr')">VBR</button>
          <button data-v="cbr" onclick="setMode('cbr')">CBR</button>
        </div>
      </div>
      <div>
        <div class="hint" style="margin-bottom:6px">Setting</div>
        <select id="value" onchange="refresh()"></select>
      </div>
      <div>
        <div class="hint" style="margin-bottom:6px">Channels</div>
        <div class="grp" id="chan">
          <button data-v="1" onclick="setChan(1)">Mono</button>
          <button data-v="2" class="on" onclick="setChan(2)">Stereo</button>
        </div>
      </div>
      <div class="hint" id="kbps"></div>
    </div>
  </div>

  <div class="card">
    <div class="lbl">Output folder</div>
    <button onclick="chooseOutput()">Choose Folder&hellip;</button>
    <div class="path" id="outdir" style="margin-top:8px">not set</div>
  </div>

  <div class="card" id="estcard" hidden>
    <div class="lbl">Estimate</div>
    <table id="est"></table>
    <div class="total"><span id="tlabel"></span><span id="total"></span></div>
    <div class="warn" id="dupe" hidden></div>
  </div>

  <div class="card">
    <button class="go" id="go" onclick="convert()" disabled>Convert</button>
    <span class="hint" id="jobhint"></span>
    <div class="bar" id="barwrap" hidden><i id="bar"></i></div>
    <div class="err" id="err" hidden></div>
    <div id="results" style="margin-top:12px"></div>
  </div>
</div>
<script>
let paths = [], outDir = null, mode = 'vbr', chan = 2, poll = null, misses = 0;

function esc(s) {
  return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g,
    c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function showErr(msg) {
  const el = document.getElementById('err');
  el.textContent = msg || '';
  el.hidden = !msg;
}

async function api(path, opts) {
  try {
    const r = await fetch(path, opts);
    let body = null;
    try { body = await r.json(); } catch (_) {}
    if (!r.ok) throw new Error((body && body.error) || `server said HTTP ${r.status}`);
    showErr('');
    return body;
  } catch (e) {
    showErr(e.message || 'could not reach the converter');
    return null;
  }
}

const VBR = [[0,'V0  ~245k'],[1,'V1  ~225k'],[2,'V2  ~190k'],[3,'V3  ~175k'],
             [4,'V4  ~165k'],[5,'V5  ~130k'],[6,'V6  ~115k'],[7,'V7  ~100k'],
             [8,'V8  ~85k'],[9,'V9  ~65k']];
const CBR = [128,160,192,224,256,320].map(k => [k, k + 'k']);

function mb(b) { return (b / 1000000).toFixed(2) + ' MB'; }

function fillValues() {
  const sel = document.getElementById('value');
  const opts = mode === 'vbr' ? VBR : CBR;
  sel.innerHTML = opts.map(([v, t]) => `<option value="${v}">${t}</option>`).join('');
  sel.value = mode === 'vbr' ? 2 : 320;
}

function setMode(m) {
  mode = m;
  document.querySelectorAll('#mode button').forEach(b =>
    b.classList.toggle('on', b.dataset.v === m));
  fillValues(); refresh();
}

function setChan(c) {
  chan = c;
  document.querySelectorAll('#chan button').forEach(b =>
    b.classList.toggle('on', +b.dataset.v === c));
  refresh();
}

async function chooseFiles() {
  const r = await api('/pick-files', {method:'POST'});
  if (r && r.paths.length) { paths = r.paths; refresh(); }
}

async function chooseOutput() {
  const r = await api('/pick-output', {method:'POST'});
  if (r && r.path) {
    outDir = r.path;
    document.getElementById('outdir').textContent = r.path;
    refresh();
  }
}

const DROP_IDLE = 'or drag wav files here';
const drop = document.getElementById('drop');
drop.ondragover = e => { e.preventDefault(); drop.classList.add('over'); };
drop.ondragleave = () => drop.classList.remove('over');
drop.ondrop = async e => {
  e.preventDefault(); drop.classList.remove('over');
  const dropped = [...e.dataTransfer.files];
  if (!dropped.length) {
    showErr('nothing usable dropped — drop files, not folders');
    return;
  }
  const fd = new FormData();
  dropped.forEach(f => fd.append('files', f));
  drop.textContent = 'staging…';
  const r = await api('/upload', {method:'POST', body:fd});
  drop.textContent = DROP_IDLE;
  if (r && r.paths.length) { paths = r.paths; refresh(); }
  else if (r) showErr('nothing was staged — drop files, not folders');
};

async function refresh() {
  document.getElementById('count').textContent =
    paths.length ? `${paths.length} file${paths.length > 1 ? 's' : ''}` : 'nothing selected';
  document.getElementById('go').disabled = !(paths.length && outDir);
  document.getElementById('estcard').hidden = !paths.length;
  if (!paths.length) return;

  const value = +document.getElementById('value').value;
  const r = await api('/estimate', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({paths, mode, value, channels: chan})
  });
  if (!r) return;

  document.getElementById('est').innerHTML = r.files.map(f => {
    const note = f.error ? `<span class="bad">${esc(f.error)}</span>` : mb(f.bytes);
    const flag = f.dupe ? ' <span class="skip">dup name</span>' : '';
    return `<tr><td class="nm">${esc(f.name)}${flag}</td><td class="sz">${note}</td></tr>`;
  }).join('');

  const dupe = document.getElementById('dupe');
  dupe.hidden = !r.dupes;
  if (r.dupes) dupe.textContent =
    `${r.dupes} files share an output name — the first converts, the rest will skip`;

  document.getElementById('tlabel').textContent = `${r.files.length} files at ~${Math.round(r.kbps)} kbps`;
  document.getElementById('total').textContent = mb(r.total);
  document.getElementById('kbps').textContent = `~${Math.round(r.kbps)} kbps average`;
}

function stopPolling() {
  if (poll) { clearInterval(poll); poll = null; }
  document.getElementById('go').disabled = false;
}

async function convert() {
  const value = +document.getElementById('value').value;
  document.getElementById('go').disabled = true;
  document.getElementById('results').innerHTML = '';
  document.getElementById('barwrap').hidden = false;
  document.getElementById('bar').style.width = '0%';
  showErr('');
  misses = 0;

  const r = await api('/convert', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({paths, out_dir: outDir, mode, value, channels: chan})
  });
  if (!r || !r.job) { stopPolling(); return; }

  poll = setInterval(() => status(r.job), 250);
}

async function status(job) {
  const s = await api('/status/' + job);
  if (!s) {
    // tolerate a blip; give up loudly if the converter is really gone
    if (++misses >= 8) {
      stopPolling();
      showErr('lost contact with the converter — job stopped reporting');
    }
    return;
  }
  misses = 0;

  document.getElementById('bar').style.width = (s.pct * 100).toFixed(1) + '%';
  document.getElementById('jobhint').textContent = s.state === 'done'
    ? `${s.total} of ${s.total} done`
    : `${s.index + 1} of ${s.total} — ${s.current}`;

  document.getElementById('results').innerHTML = s.results.map(f => {
    const cls = f.status === 'ok' ? 'ok' : f.status === 'skipped' ? 'skip' : 'bad';
    const note = f.status === 'ok' ? mb(f.bytes) : esc(f.reason);
    return `<div class="res"><span>${esc(f.name)}</span>
            <span class="${cls}">${esc(f.status).toUpperCase()}</span>
            <span class="hint">${note}</span></div>`;
  }).join('');

  if (s.state === 'done') stopPolling();
}

setMode('vbr');
</script>
"""


# ---------------------------------------------------------------- app

app = Flask(__name__)

_DURATIONS: dict[str, float] = {}
JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
UPLOAD_DIR = Path(tempfile.gettempdir()) / "stem-converter-uploads"


def cached_duration(path: str) -> float:
    """Duration with a per-path cache -- probing is the slow part."""
    if path not in _DURATIONS:
        _DURATIONS[path] = probe_duration(Path(path))
    return _DURATIONS[path]


def describe(paths: list[str], mode: str, value: int, channels: int) -> dict:
    """Per-file and total size estimate for the current settings.

    Flags files whose output name collides -- only the first survives,
    the rest skip, so the warning belongs before the batch runs.
    """
    collisions = Counter(Path(p).stem + ".mp3" for p in paths)
    files, total = [], 0
    for path in paths:
        out_name = Path(path).stem + ".mp3"
        entry = {"path": path, "name": Path(path).name,
                 "dupe": collisions[out_name] > 1}
        try:
            duration = cached_duration(path)
            size = estimate_bytes(duration, mode, value, channels)
            entry.update(duration=duration, bytes=size, error="")
            total += size
        except EngineError as exc:
            entry.update(duration=0, bytes=0, error=str(exc))
        files.append(entry)
    return {"files": files, "total": total,
            "dupes": sum(1 for f in files if f["dupe"]),
            "kbps": effective_kbps(mode, value, channels)}


@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.get("/tools")
def tools():
    try:
        check_tools()
        return jsonify(ok=True, ffmpeg=FFMPEG)
    except EngineError as exc:
        return jsonify(ok=False, error=str(exc))


@app.post("/pick-files")
def route_pick_files():
    return jsonify(paths=pick_files())


@app.post("/pick-output")
def route_pick_output():
    return jsonify(path=pick_folder())


@app.post("/upload")
def route_upload():
    """Drag/drop path -- browser sends contents, we stage them on disk.

    Each file lands in its own cell so same-named files from different
    folders cannot overwrite each other before the encoder sees them.
    """
    batch = UPLOAD_DIR / uuid.uuid4().hex[:8]
    saved = []
    for index, item in enumerate(request.files.getlist("files")):
        name = Path(item.filename or "").name
        if not name:
            continue
        cell = batch / str(index)
        cell.mkdir(parents=True, exist_ok=True)
        dest = cell / name
        item.save(dest)
        saved.append(str(dest))
    return jsonify(paths=saved)


@app.post("/estimate")
def route_estimate():
    body = request.get_json(force=True)
    return jsonify(describe(body.get("paths", []), body.get("mode", "vbr"),
                            int(body.get("value", 2)),
                            int(body.get("channels", 2))))


def _run_job(job_id: str, paths: list[str], out_dir: Path, mode: str,
             value: int, channels: int) -> None:
    """Encode every file in order, recording progress as it goes."""
    for index, path in enumerate(paths):
        with _JOBS_LOCK:
            JOBS[job_id].update(index=index, current=Path(path).name, file_pct=0.0)

        def track(pct: float, _id=job_id) -> None:
            with _JOBS_LOCK:
                JOBS[_id]["file_pct"] = pct

        result = encode_one(Path(path), out_dir, mode=mode, value=value,
                            channels=channels, on_progress=track)

        with _JOBS_LOCK:
            JOBS[job_id]["results"].append(result)
            JOBS[job_id]["file_pct"] = 1.0

    with _JOBS_LOCK:
        JOBS[job_id].update(state="done", index=len(paths), current="",
                            file_pct=0.0)


@app.post("/convert")
def route_convert():
    body = request.get_json(force=True)
    paths = body.get("paths", [])
    out_dir = Path(body.get("out_dir", ""))

    if not paths:
        return jsonify(error="no files selected"), 400
    if not out_dir.is_dir():
        return jsonify(error="output folder is not a directory"), 400

    job_id = uuid.uuid4().hex[:12]
    with _JOBS_LOCK:
        JOBS[job_id] = {"total": len(paths), "index": 0, "current": "",
                        "file_pct": 0.0, "state": "running", "results": []}

    threading.Thread(
        target=_run_job, daemon=True,
        args=(job_id, paths, out_dir, body.get("mode", "vbr"),
              int(body.get("value", 2)), int(body.get("channels", 2))),
    ).start()

    return jsonify(job=job_id)


@app.get("/status/<job_id>")
def route_status(job_id: str):
    with _JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify(error="unknown job"), 404
        snapshot = dict(job, results=list(job["results"]))
    total = snapshot["total"] or 1
    snapshot["pct"] = (snapshot["index"] + snapshot["file_pct"]) / total
    return jsonify(snapshot)


def free_port(start: int = 5137, tries: int = 20) -> int:
    """First open port at or after start."""
    for port in range(start, start + tries):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise EngineError(f"no free port in {start}-{start + tries}")


if __name__ == "__main__":
    try:
        check_tools()
        port = free_port()
    except EngineError as exc:
        raise SystemExit(f"Stem Converter cannot start -- {exc}")
    print(f"Stem Converter  ->  http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
