#!/usr/bin/env python3
"""Build review.html from prelabels.csv, to check and correct the model's labels.

Open OUT_DIR/review.html in a browser. Frames are grouped by predicted label, low
confidence first. Click a label button on a frame to change it (changed frames get an
orange border), click the image for the full-size original. Progress is kept in the
browser; "Export labels.csv" saves the result.

Corrections live only in the browser until exported, so export often. Pass earlier exports
with --labels to carry their corrections into a new page.

--field adult reviews the adult column instead, exporting adults.csv. --files limits the
page to the frames named in a text file, one per line.

Usage:
    review.py OUT_DIR IMAGE_DIR [IMAGE_DIR ...] [--labels labels.csv ...]
              [--field label|adult] [--files LIST]
"""

import argparse
import csv
import html
import json
import sys
from pathlib import Path

FIELDS = {
    "label": ["in_bed", "child_up", "empty", "unclear"],
    "adult": ["none", "in_cot", "beside_cot"],
}
CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>Sleep Eval Review</title>
<style>
  body { font: 14px system-ui, sans-serif; margin: 0 16px 64px; background: #f6f6f4; color: #222; }
  header { position: sticky; top: 0; background: #f6f6f4; padding: 12px 0; z-index: 1;
           display: flex; gap: 16px; align-items: center; border-bottom: 1px solid #ddd; }
  h2 { margin: 24px 0 8px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
  .tile { background: #fff; border: 3px solid transparent; border-radius: 6px; padding: 4px; }
  .tile.changed { border-color: #e8890c; }
  .tile img { width: 100%; display: block; border-radius: 3px; cursor: zoom-in; }
  .meta { font-size: 11px; color: #666; margin: 4px 2px; overflow-wrap: anywhere; }
  .low { color: #b3261e; font-weight: 600; }
  .buttons { display: flex; gap: 4px; }
  .buttons button { flex: 1; font-size: 11px; padding: 4px 0; border: 1px solid #ccc;
                    background: #fafafa; border-radius: 4px; cursor: pointer; }
  .buttons button.on { background: #222; color: #fff; border-color: #222; }
</style>
<header>
  <strong>Sleep Eval Review</strong>
  <span id="count"></span>
  <button id="export">Export __FIELD__s.csv</button>
</header>
<main id="main"></main>
<script>
const LABELS = __LABELS__;
const FRAMES = __FRAMES__;
const FIELD = "__FIELD__";
const KEY = FIELD === "label" ? "sleep-eval-review" : "sleep-eval-review-" + FIELD;
// corrections from earlier exports, then any made in this browser since
let edits = __CORRECTIONS__;
try { Object.assign(edits, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
// drop corrections a relabel has since agreed with
FRAMES.forEach(f => { if (edits[f.file] === f[FIELD]) delete edits[f.file]; });

function save() {
  try { localStorage.setItem(KEY, JSON.stringify(edits)); } catch (e) {}
  document.getElementById("count").textContent = Object.keys(edits).length + " changed of " + FRAMES.length;
}

function tile(frame) {
  const div = document.createElement("div");
  div.className = "tile";
  const img = document.createElement("img");
  img.loading = "lazy";
  img.src = frame.thumb;
  img.onclick = () => window.open(frame.original, "_blank");
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.innerHTML = frame.meta;
  const buttons = document.createElement("div");
  buttons.className = "buttons";
  function render() {
    const current = edits[frame.file] || frame[FIELD];
    div.classList.toggle("changed", frame.file in edits);
    buttons.querySelectorAll("button").forEach(b => b.classList.toggle("on", b.dataset.label === current));
  }
  LABELS.forEach(label => {
    const b = document.createElement("button");
    b.textContent = label;
    b.dataset.label = label;
    b.onclick = () => {
      if (label === frame[FIELD]) delete edits[frame.file]; else edits[frame.file] = label;
      render(); save();
    };
    buttons.appendChild(b);
  });
  div.append(img, meta, buttons);
  render();
  return div;
}

const main = document.getElementById("main");
LABELS.forEach(label => {
  const frames = FRAMES.filter(f => f[FIELD] === label);
  if (!frames.length) return;
  const h = document.createElement("h2");
  h.textContent = "Predicted " + (FIELD === "label" ? "" : FIELD + " ") + label + " (" + frames.length + ")";
  const grid = document.createElement("div");
  grid.className = "grid";
  frames.forEach(f => grid.appendChild(tile(f)));
  main.append(h, grid);
});
save();

document.getElementById("export").onclick = () => {
  const other = FIELD === "label" ? "adult" : "label";
  const rows = [["file", FIELD, "predicted", other, "lighting"]];
  FRAMES.forEach(f => rows.push([f.file, edits[f.file] || f[FIELD], f[FIELD], f[other], f.lighting]));
  const blob = new Blob([rows.map(r => r.join(",")).join("\\n") + "\\n"], {type: "text/csv"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = FIELD + "s.csv";
  a.click();
};
</script>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("image_dirs", type=Path, nargs="+")
    parser.add_argument("--labels", type=Path, action="append", default=[],
                        help="an earlier export whose corrections to carry over (repeatable)")
    parser.add_argument("--field", choices=FIELDS, default="label", help="which column to review")
    parser.add_argument("--files", type=Path, help="only the frames listed in this file")
    args = parser.parse_args()

    missing = [str(d) for d in args.image_dirs if not d.is_dir()]
    if missing:
        sys.exit(f"no such image folder: {', '.join(missing)}")

    originals = {path.name: path.resolve() for image_dir in args.image_dirs for path in image_dir.glob("*.jpg")}
    csv_path = args.out_dir / "prelabels.csv"
    if not csv_path.exists():
        sys.exit(f"{csv_path} not found: run prelabel.py first")
    with csv_path.open() as f:
        rows = list(csv.DictReader(f))
    if args.files:
        keep = set(args.files.read_text().split())
        rows = [r for r in rows if r["file"] in keep]
    rows.sort(key=lambda r: (CONFIDENCE_ORDER.get(r["confidence"], 0), r["file"]))

    frames = []
    for row in rows:
        confidence = row["confidence"]
        if confidence == "low":
            confidence = '<span class="low">low</span>'
        meta = f'{html.escape(row["file"])}<br>{confidence} · adult {row["adult"]} · {row["lighting"]}<br>{html.escape(row["note"])}'
        original = originals.get(row["file"])
        frames.append({
            "file": row["file"],
            "label": row["label"],
            "adult": row["adult"],
            "lighting": row["lighting"],
            "thumb": f"thumbs/{row['file']}",
            "original": original.as_uri() if original else f"thumbs/{row['file']}",
            "meta": meta,
        })

    # only rows changed by hand: an unchanged row is just the old model's guess
    corrections = {}
    for labels in args.labels:
        with labels.open() as f:
            corrections.update({r["file"]: r[args.field] for r in csv.DictReader(f)
                                if args.field in r and r[args.field] != r["predicted"]})

    page = (PAGE.replace("__LABELS__", json.dumps(FIELDS[args.field]))
            .replace("__FIELD__", args.field)
            .replace("__FRAMES__", json.dumps(frames))
            .replace("__CORRECTIONS__", json.dumps(corrections)))
    out = args.out_dir / ("review.html" if args.field == "label" else f"review_{args.field}.html")
    out.write_text(page)
    print(f"wrote {out} ({len(frames)} frames, {len(corrections)} corrections carried over)")


if __name__ == "__main__":
    main()
