#!/usr/bin/env python3
"""
Generate public/timeline.html from image_records.csv.

Produces a self-contained HTML with:
  - Fixed left sidebar: live keyword / actor search, quick-filter chips
  - Scrollable vertical timeline: collapsible year sections, all dated entries
  - Lightbox viewer: zoomable image (scroll-wheel + drag), metadata panel
"""

import csv, json, re
from pathlib import Path

ROOT     = Path(__file__).parent.parent
CSV_PATH = ROOT / "data" / "image_records.csv"
OUT_PATH = ROOT / "public" / "timeline.html"

CHIPS = [
    ("Nygaard",      "Kristen Nygaard"),
    ("DEMOS",        "DEMOS"),
    ("EDB",          "EDB"),
    ("Regnesentral", "Regnesentral"),
    ("Bergo",        "Olav Terje Bergo"),
    ("NTNF",         "NTNF"),
    ("Aarset",       "Svein Aarset"),
    ("Skau",         "Leif Skau"),
]


def clean_box(name: str) -> str:
    name = name.strip()
    if not name:
        return ""
    if name == name.upper() and len(name) > 3:
        lowers = {"og", "i", "av", "fra", "til", "den", "det", "de", "nr"}
        name = " ".join(
            w if w in lowers else w.capitalize()
            for w in name.lower().split()
        )
    if re.fullmatch(r"\d+", name):
        name = "Box " + name
    name = re.sub(r"\s+-\s+", " – ", name)
    return name


def extract_entries() -> list[dict]:
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    entries = []
    for r in rows:
        if r.get("is_separator") == "Y":
            continue
        raw  = r.get("document_date", "").strip()
        desc = r.get("description", "").strip()
        if not raw or not desc:
            continue
        m = re.search(r"(196[5-9]|197[0-5])", raw)
        if not m:
            continue
        fp   = r.get("file_path", "")
        stem = Path(fp).stem if fp else Path(r.get("filename", "")).stem
        entries.append({
            "year": int(m.group(1)),
            "date": raw,
            "box":  clean_box(r.get("archival_box", "")),
            "desc": desc,           # full text for lightbox
            "stem": stem,           # filename stem → images/previews/<stem>.jpg
        })
    entries.sort(key=lambda e: (e["year"], e["date"]))
    return entries


def build_chips() -> str:
    return "\n        ".join(
        f'<button class="chip" data-term="{t}">{l}</button>'
        for t, l in CHIPS
    )


# ── HTML template ─────────────────────────────────────────────────────────────
# Substitution markers: __DATA_JSON__  __TOTAL__  __SPAN__  __CHIPS__

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NJMF — Archive Timeline 1969–1975</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;0,800;1,400;1,600&display=swap" rel="stylesheet">
  <style>
    :root {
      --ink:   #0f0f0e;
      --mid:   #808080;
      --faint: #d0d0ce;
      --rule:  #ebebea;
      --hl:    #f2efe6;
      --bg:    #ffffff;
      --img-bg:#f4f3f0;
      --lx:    52px;   /* timeline line x-position */
      --gap:   36px;   /* gap from line to content */
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      height: 100%;
      overflow: hidden;
      background: var(--bg);
      color: var(--ink);
      font-family: 'Playfair Display', 'Times New Roman', Georgia, serif;
      -webkit-font-smoothing: antialiased;
    }

    /* ── App layout ──────────────────────────────────────────────────── */

    .layout { display: flex; height: 100vh; }

    /* ── Sidebar ─────────────────────────────────────────────────────── */

    .sidebar {
      flex-shrink: 0;
      width: 268px;
      height: 100vh;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--ink);
      overflow: hidden;
    }

    .sb-hd {
      padding: 48px 36px 28px;
      border-bottom: 1px solid var(--rule);
      flex-shrink: 0;
    }

    .sb-eyebrow {
      font-size: 9px;
      letter-spacing: 0.36em;
      text-transform: uppercase;
      color: var(--mid);
      margin-bottom: 14px;
    }

    .sb-title {
      font-size: 54px;
      font-weight: 800;
      letter-spacing: 0.04em;
      line-height: 0.9;
      margin-bottom: 12px;
    }

    .sb-dates {
      font-size: 13px;
      font-style: italic;
      color: var(--mid);
    }

    .sb-search {
      padding: 22px 36px 18px;
      border-bottom: 1px solid var(--rule);
      flex-shrink: 0;
    }

    .search-row {
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 1px solid var(--ink);
      padding-bottom: 7px;
      margin-bottom: 14px;
    }

    #search {
      flex: 1;
      border: none;
      background: transparent;
      outline: none;
      font-family: inherit;
      font-size: 13px;
      font-style: italic;
      color: var(--ink);
      padding: 0;
      min-width: 0;
    }

    #search::placeholder { color: var(--faint); }

    #search-clear {
      background: none; border: none; cursor: pointer;
      color: var(--faint); font-size: 18px; line-height: 1;
      padding: 0; display: none; flex-shrink: 0;
    }

    #search-clear.show { display: block; }

    .chips { display: flex; flex-wrap: wrap; gap: 5px; }

    .chip {
      background: none;
      border: 1px solid var(--faint);
      font-family: inherit;
      font-size: 9px;
      letter-spacing: 0.16em;
      color: var(--mid);
      padding: 3px 8px;
      cursor: pointer;
      transition: border-color .12s, color .12s, background .12s;
      white-space: nowrap;
    }

    .chip:hover { border-color: var(--ink); color: var(--ink); }

    .chip.on { background: var(--ink); border-color: var(--ink); color: var(--bg); }

    .sb-ft {
      margin-top: auto;
      padding: 18px 36px;
      border-top: 1px solid var(--rule);
      flex-shrink: 0;
    }

    #entry-count { font-size: 10px; letter-spacing: 0.2em; color: var(--faint); }

    /* ── Main timeline ───────────────────────────────────────────────── */

    .main {
      flex: 1;
      height: 100vh;
      overflow-y: scroll;
      overflow-x: hidden;
      padding-left: calc(var(--lx) + var(--gap));
      padding-right: 60px;
      padding-bottom: 120px;
      background-color: var(--bg);
      background-image: linear-gradient(var(--ink), var(--ink));
      background-size: 1px auto;
      background-position: var(--lx) 0;
      background-repeat: repeat-y;
      background-attachment: local;
    }

    /* ── Year section ────────────────────────────────────────────────── */

    .yr { padding-top: 52px; }
    .yr.gone { display: none; }

    .yr-hd {
      position: relative;
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 2px;
    }

    .yr-hd::before {
      content: '';
      position: absolute;
      left: calc(-1 * var(--gap));
      top: 50%;
      width: var(--gap);
      height: 1px;
      background: var(--ink);
    }

    .yr-toggle {
      background: none; border: none; cursor: pointer;
      font-family: inherit;
      display: flex; align-items: center; gap: 10px;
      padding: 0; flex-shrink: 0;
    }

    .yr-arrow {
      font-size: 9px; color: var(--mid);
      display: inline-block;
      transition: transform .16s;
      margin-top: 1px;
    }

    .yr.collapsed .yr-arrow { transform: rotate(-90deg); }

    .yr-num {
      font-size: 24px; font-weight: 700;
      letter-spacing: -0.01em; line-height: 1;
    }

    .yr-rule { flex: 1; height: 1px; background: var(--rule); }

    .yr-ct {
      font-size: 9px; letter-spacing: 0.22em;
      color: var(--faint); white-space: nowrap;
    }

    .yr-body { padding-top: 2px; }
    .yr.collapsed .yr-body { display: none; }

    /* ── Entry ───────────────────────────────────────────────────────── */

    .en {
      position: relative;
      display: grid;
      grid-template-columns: 116px 1fr;
      gap: 0 18px;
      padding: 16px 0;
      border-bottom: 1px solid var(--rule);
      cursor: pointer;
      transition: background .1s;
    }

    .en:hover { background: var(--hl); margin: 0 -60px 0 calc(-1 * var(--gap));
                padding-left: var(--gap); padding-right: 60px; }

    .en.gone { display: none; }

    .en::before {
      content: '';
      position: absolute;
      left: calc(-1 * var(--gap));
      top: 28px;
      width: 9px;
      height: 1px;
      background: var(--faint);
      transition: background .1s;
    }

    .en:hover::before { background: var(--ink); }

    .en-left { padding-top: 1px; }

    .en-date {
      font-size: 10px; letter-spacing: 0.16em;
      color: var(--mid); line-height: 1.6; margin-bottom: 5px;
    }

    .en-box { font-size: 9px; letter-spacing: 0.13em; color: var(--faint); line-height: 1.6; }

    .en-desc {
      font-size: 13px; font-style: italic;
      font-weight: 400; line-height: 1.85; color: var(--ink);
    }

    mark { background: var(--hl); color: var(--ink); padding: 0 1px; }

    /* ── Terminus ────────────────────────────────────────────────────── */

    .terminus { position: relative; padding: 52px 0 80px; }

    .terminus::before {
      content: '';
      position: absolute;
      left: calc(-1 * var(--gap) - 3px);
      top: 63px;
      width: 7px; height: 7px;
      border-radius: 50%;
      background: var(--ink);
    }

    .t-label { font-size: 9px; letter-spacing: 0.3em; color: var(--faint); margin-bottom: 7px; }
    .t-text  { font-size: 19px; font-weight: 400; font-style: italic; }

    /* ── Lightbox ────────────────────────────────────────────────────── */

    #lb {
      position: fixed;
      inset: 0;
      z-index: 200;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      pointer-events: none;
      transition: opacity .22s;
    }

    #lb.open { opacity: 1; pointer-events: auto; }

    #lb-backdrop {
      position: absolute;
      inset: 0;
      background: rgba(10, 10, 9, 0.9);
    }

    #lb-panel {
      position: relative;
      z-index: 1;
      display: flex;
      width: min(1100px, 94vw);
      height: min(820px, 90vh);
      background: var(--bg);
      overflow: hidden;
    }

    /* Image area */
    #lb-img-area {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      background: var(--img-bg);
      position: relative;
      overflow: hidden;
    }

    #lb-img-wrap {
      flex: 1;
      overflow: hidden;
      position: relative;
      cursor: default;
      user-select: none;
    }

    #lb-img {
      position: absolute;
      top: 0; left: 0;
      transform-origin: 0 0;
      max-width: none;
      display: block;
      /* initial sizing handled by JS after load */
    }

    #lb-img.loading { display: none; }

    #lb-placeholder {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 10px;
      color: var(--faint);
    }

    #lb-placeholder .ph-icon {
      font-size: 36px;
      opacity: 0.4;
    }

    #lb-placeholder .ph-text {
      font-size: 11px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
    }

    #lb-spinner {
      width: 24px; height: 24px;
      border: 1.5px solid var(--faint);
      border-top-color: var(--mid);
      border-radius: 50%;
      animation: spin .7s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }

    #lb-zoom-bar {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 16px;
      border-top: 1px solid var(--rule);
      background: var(--bg);
    }

    .zb-btn {
      background: none; border: 1px solid var(--faint);
      cursor: pointer; font-family: inherit;
      font-size: 14px; color: var(--ink);
      width: 26px; height: 26px;
      display: flex; align-items: center; justify-content: center;
      transition: border-color .1s;
    }

    .zb-btn:hover { border-color: var(--ink); }

    #lb-zoom-pct {
      font-size: 10px; letter-spacing: 0.18em;
      color: var(--mid); min-width: 38px;
      text-align: center;
    }

    #lb-zoom-reset {
      margin-left: auto;
      font-size: 9px; letter-spacing: 0.2em;
      text-transform: uppercase;
      background: none; border: none; cursor: pointer;
      color: var(--faint); font-family: inherit;
      transition: color .1s;
    }

    #lb-zoom-reset:hover { color: var(--ink); }

    /* Metadata sidebar */
    #lb-meta {
      flex-shrink: 0;
      width: 280px;
      border-left: 1px solid var(--rule);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 40px 32px 32px;
    }

    #lb-close {
      position: absolute;
      top: 16px; right: 16px;
      z-index: 10;
      background: none; border: none;
      font-size: 22px; line-height: 1;
      color: var(--mid); cursor: pointer;
      transition: color .1s;
      padding: 4px 6px;
    }

    #lb-close:hover { color: var(--ink); }

    .lbm-label {
      font-size: 8.5px;
      letter-spacing: 0.34em;
      text-transform: uppercase;
      color: var(--faint);
      margin-bottom: 6px;
    }

    .lbm-val {
      font-size: 14px;
      font-weight: 400;
      line-height: 1.5;
      color: var(--ink);
      margin-bottom: 28px;
    }

    .lbm-val.italic { font-style: italic; }

    #lbm-desc {
      font-size: 13px;
      font-style: italic;
      font-weight: 400;
      line-height: 1.85;
      color: var(--mid);
      margin-bottom: 28px;
      flex: 1;
    }

    #lbm-file {
      font-size: 9px;
      letter-spacing: 0.16em;
      color: var(--faint);
      margin-top: auto;
      padding-top: 16px;
      border-top: 1px solid var(--rule);
    }
  </style>
</head>
<body>
<div class="layout">

  <!-- ── Sidebar ── -->
  <aside class="sidebar">
    <div class="sb-hd">
      <div class="sb-eyebrow">Archive Timeline</div>
      <h1 class="sb-title">NJMF</h1>
      <div class="sb-dates">__SPAN__</div>
    </div>
    <div class="sb-search">
      <div class="search-row">
        <input id="search" type="search" autocomplete="off" spellcheck="false"
               placeholder="Keyword or historical actor…">
        <button id="search-clear" title="Clear">&#215;</button>
      </div>
      <div class="chips" id="chips">__CHIPS__</div>
    </div>
    <div class="sb-ft">
      <div id="entry-count">__TOTAL__ entries</div>
    </div>
  </aside>

  <!-- ── Timeline ── -->
  <main class="main" id="main">
    <div id="tl-root"></div>
    <div class="terminus">
      <div class="t-label">The moment</div>
      <div class="t-text">DEMOS project &thinsp;&middot;&thinsp; 1975</div>
    </div>
  </main>

</div>

<!-- ── Lightbox ── -->
<div id="lb" aria-modal="true" role="dialog" aria-label="Document viewer">
  <div id="lb-backdrop"></div>
  <div id="lb-panel">

    <button id="lb-close" title="Close (Esc)">&#215;</button>

    <!-- Image -->
    <div id="lb-img-area">
      <div id="lb-img-wrap">
        <img id="lb-img" src="" alt="Archival document" draggable="false">
        <div id="lb-placeholder">
          <div id="lb-spinner"></div>
          <div class="ph-text">Loading preview</div>
        </div>
      </div>
      <div id="lb-zoom-bar">
        <button class="zb-btn" id="lb-zoom-out" title="Zoom out">&#8722;</button>
        <span id="lb-zoom-pct">100%</span>
        <button class="zb-btn" id="lb-zoom-in" title="Zoom in">&#43;</button>
        <button id="lb-zoom-reset">Reset zoom</button>
      </div>
    </div>

    <!-- Metadata -->
    <div id="lb-meta">
      <div class="lbm-label">Date</div>
      <div class="lbm-val" id="lbm-date"></div>

      <div class="lbm-label">Archival reference</div>
      <div class="lbm-val" id="lbm-box"></div>

      <div class="lbm-label">Description</div>
      <div id="lbm-desc"></div>

      <div id="lbm-file"></div>
    </div>

  </div>
</div>

<script>
const DATA  = __DATA_JSON__;
const TOTAL = __TOTAL__;

// ── Utilities ─────────────────────────────────────────────────────────

function esc(s) {
  return String(s || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function highlight(text, q) {
  if (!q) return esc(text);
  const lower = text.toLowerCase();
  const idx   = lower.indexOf(q.toLowerCase());
  if (idx === -1) return esc(text);
  return esc(text.slice(0, idx))
    + '<mark>' + esc(text.slice(idx, idx + q.length)) + '</mark>'
    + highlight(text.slice(idx + q.length), q);
}

// ── Render timeline ───────────────────────────────────────────────────

const byYear = {};
DATA.forEach(e => { (byYear[e.year] = byYear[e.year] || []).push(e); });
const years  = Object.keys(byYear).sort();

function render() {
  document.getElementById('tl-root').innerHTML = years.map(yr => {
    const ents = byYear[yr];
    const rows = ents.map((e, i) => {
      const preview = 'images/previews/' + e.stem + '.jpg';
      const snippet = e.desc.length > 200 ? e.desc.slice(0, 197) + '…' : e.desc;
      return `<article class="en" data-idx="${DATA.indexOf(e)}"
          data-s="${esc((e.date+' '+e.box+' '+e.desc).toLowerCase())}"
          title="Click to view document">
        <div class="en-left">
          <div class="en-date">${esc(e.date)}</div>
          <div class="en-box">${esc(e.box)}</div>
        </div>
        <div class="en-right">
          <div class="en-desc" data-orig="${esc(e.desc)}" data-snip="${esc(snippet)}">${esc(snippet)}</div>
        </div>
      </article>`;
    }).join('');

    return `<section class="yr" data-y="${yr}" id="yr${yr}">
      <div class="yr-hd">
        <button class="yr-toggle">
          <span class="yr-arrow">&#9662;</span>
          <span class="yr-num">${yr}</span>
        </button>
        <div class="yr-rule"></div>
        <span class="yr-ct" id="ct${yr}">${ents.length} entries</span>
      </div>
      <div class="yr-body">${rows}</div>
    </section>`;
  }).join('');

  document.querySelectorAll('.yr-toggle').forEach(btn => {
    btn.addEventListener('click', () => btn.closest('.yr').classList.toggle('collapsed'));
  });

  document.querySelectorAll('.en').forEach(el => {
    el.addEventListener('click', () => {
      const idx = parseInt(el.dataset.idx, 10);
      lbOpen(DATA[idx]);
    });
  });
}

// ── Filter ────────────────────────────────────────────────────────────

function filter(q) {
  const ql = q.toLowerCase().trim();
  let shown = 0;
  years.forEach(yr => {
    const sec  = document.getElementById('yr' + yr);
    let secVis = 0;
    sec.querySelectorAll('.en').forEach(el => {
      const match = !ql || (el.dataset.s || '').includes(ql);
      el.classList.toggle('gone', !match);
      if (match) secVis++;
      const d = el.querySelector('.en-desc');
      if (d) d.innerHTML = match
        ? highlight(d.dataset.orig.length > 200 ? d.dataset.orig.slice(0,197)+'…' : d.dataset.orig, ql)
        : esc(d.dataset.snip);
    });
    sec.classList.toggle('gone', secVis === 0);
    if (ql && secVis > 0) sec.classList.remove('collapsed');
    const ct = document.getElementById('ct' + yr);
    if (ct) ct.textContent = ql
      ? secVis + ' / ' + byYear[yr].length
      : byYear[yr].length + ' entries';
    shown += secVis;
  });
  document.getElementById('entry-count').textContent =
    ql ? shown + ' matching' : TOTAL + ' entries';
}

// ── Search events ─────────────────────────────────────────────────────

const inp = document.getElementById('search');
const clr = document.getElementById('search-clear');

inp.addEventListener('input', () => {
  clr.classList.toggle('show', inp.value.length > 0);
  filter(inp.value);
});

clr.addEventListener('click', () => {
  inp.value = '';
  clr.classList.remove('show');
  document.querySelectorAll('.chip.on').forEach(c => c.classList.remove('on'));
  filter('');
});

document.getElementById('chips').addEventListener('click', e => {
  const chip = e.target.closest('.chip');
  if (!chip) return;
  const wasOn = chip.classList.contains('on');
  document.querySelectorAll('.chip.on').forEach(c => c.classList.remove('on'));
  inp.value = wasOn ? '' : chip.dataset.term;
  if (!wasOn) chip.classList.add('on');
  clr.classList.toggle('show', inp.value.length > 0);
  filter(inp.value);
});

// ── Lightbox ──────────────────────────────────────────────────────────

const lb      = document.getElementById('lb');
const lbImg   = document.getElementById('lb-img');
const lbWrap  = document.getElementById('lb-img-wrap');
const lbPh    = document.getElementById('lb-placeholder');
const lbPct   = document.getElementById('lb-zoom-pct');

// Zoom state
let zScale = 1, zTx = 0, zTy = 0;
let dragging = false, dStartX, dStartY, dTx0, dTy0;

function zApply() {
  lbImg.style.transform = 'translate(' + zTx + 'px,' + zTy + 'px) scale(' + zScale + ')';
  lbPct.textContent = Math.round(zScale * 100) + '%';
  lbWrap.style.cursor = zScale > 1 ? (dragging ? 'grabbing' : 'grab') : 'default';
}

function zInit() {
  const w  = lbWrap.clientWidth, h = lbWrap.clientHeight;
  const iw = lbImg.naturalWidth,  ih = lbImg.naturalHeight;
  const fit = Math.min(w / iw, h / ih, 1);
  zScale = fit;
  zTx    = (w - iw * fit) / 2;
  zTy    = (h - ih * fit) / 2;
  zApply();
}

function zSet(newScale, cx, cy) {
  // cx, cy: zoom focal point in wrap-local coords (defaults to centre)
  const w = lbWrap.clientWidth, h = lbWrap.clientHeight;
  if (cx === undefined) { cx = w / 2; cy = h / 2; }
  const clamped = Math.max(0.25, Math.min(10, newScale));
  const ratio   = clamped / zScale;
  zTx    = cx * (1 - ratio) + zTx * ratio;
  zTy    = cy * (1 - ratio) + zTy * ratio;
  zScale = clamped;
  zApply();
}

function zReset() {
  zInit();
}

// Scroll to zoom
lbWrap.addEventListener('wheel', e => {
  e.preventDefault();
  const rect = lbWrap.getBoundingClientRect();
  zSet(zScale * (e.deltaY < 0 ? 1.15 : 0.87),
       e.clientX - rect.left, e.clientY - rect.top);
}, { passive: false });

// Drag to pan
lbWrap.addEventListener('mousedown', e => {
  if (zScale <= 1) return;
  dragging = true; dStartX = e.clientX; dStartY = e.clientY;
  dTx0 = zTx; dTy0 = zTy;
  zApply();
  e.preventDefault();
});

window.addEventListener('mousemove', e => {
  if (!dragging) return;
  zTx = dTx0 + (e.clientX - dStartX);
  zTy = dTy0 + (e.clientY - dStartY);
  zApply();
});

window.addEventListener('mouseup', () => { dragging = false; zApply(); });

// Zoom buttons
document.getElementById('lb-zoom-in').addEventListener('click',  () => zSet(zScale * 1.25));
document.getElementById('lb-zoom-out').addEventListener('click', () => zSet(zScale * 0.8));
document.getElementById('lb-zoom-reset').addEventListener('click', zReset);

function lbOpen(entry) {
  // Populate metadata
  document.getElementById('lbm-date').textContent = entry.date;
  document.getElementById('lbm-box').textContent  = entry.box || '—';
  document.getElementById('lbm-desc').textContent = entry.desc;
  document.getElementById('lbm-file').textContent = entry.stem;

  // Load image
  lbImg.classList.add('loading');
  lbPh.style.display = 'flex';
  lbPh.innerHTML = '<div id="lb-spinner"></div><div class="ph-text">Loading preview</div>';

  const src = 'images/previews/' + entry.stem + '.jpg';
  lbImg.onload = () => {
    lbImg.classList.remove('loading');
    lbPh.style.display = 'none';
    zInit();
  };
  lbImg.onerror = () => {
    lbPh.innerHTML = '<div class="ph-icon">&#8984;</div>'
      + '<div class="ph-text">Preview generating&thinsp;&mdash;&thinsp;check back shortly</div>';
  };
  lbImg.src = src;

  lb.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function lbClose() {
  lb.classList.remove('open');
  document.body.style.overflow = '';
  lbImg.src = '';
}

document.getElementById('lb-close').addEventListener('click', lbClose);
document.getElementById('lb-backdrop').addEventListener('click', lbClose);

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && lb.classList.contains('open')) lbClose();
});

// ── Init ──────────────────────────────────────────────────────────────
render();
</script>
</body>
</html>"""


def main() -> None:
    entries = extract_entries()
    total   = len(entries)
    years   = sorted(set(e["year"] for e in entries))
    span    = f"{min(years)} — {max(years)}" if years else "1969–1975"
    data_j  = json.dumps(entries, ensure_ascii=False).replace("</", "<\\/")

    print(f"Extracted {total} entries:")
    for yr in years:
        print(f"  {yr}: {sum(1 for e in entries if e['year'] == yr)}")

    html = (TEMPLATE
        .replace("__DATA_JSON__", data_j)
        .replace("__TOTAL__",     str(total))
        .replace("__SPAN__",      span)
        .replace("__CHIPS__",     build_chips())
    )
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Written: {OUT_PATH}")


if __name__ == "__main__":
    main()
