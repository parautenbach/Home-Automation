#!/usr/bin/env python3
"""Pre-label nursery frames with a vision model, for human review.

Writes a downscaled thumbnail per frame (what the model saw, and what the review page
shows) and appends one row per frame to prelabels.csv. Rerunning skips frames that are
already in the CSV, so an interrupted run resumes.

Usage:
    prelabel.py OUT_DIR IMAGE_DIR [IMAGE_DIR ...] [--since 20250501] [--model claude-sonnet-5-5]
                [--width 768] [--workers 8] [--limit N] [--reference EMPTY.jpg ...]
"""

import argparse
import base64
import csv
import io
import json
import os
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
from PIL import Image

# $ per million tokens, input and output
PRICES = {"claude-haiku-4-5": (1.00, 5.00), "claude-sonnet-5-5": (2.00, 10.00)}

LABELS = ["in_bed", "child_up", "empty", "unclear"]

KEYCHAIN_SERVICE = "anthropic-api-key"

PROMPT = """The last image is a frame from a camera mounted above a toddler's bed. At night \
it's an infrared greyscale image; with a lamp on it's in colour. A timestamp and logo are \
overlaid.{reference}

Classify the child's state:
- in_bed: the child is in the bed, lying down in any position. She can lie in any direction, \
including with her head at the end nearest the camera, may be under the duvet, and may be \
motion-blurred. A lifted head, rolling over, turning around on hands and knees, propping \
up on an elbow, or leaning over to reach something (e.g. the bedside light) is still in_bed.
- child_up: the child is upright: sitting straight up, kneeling up or standing.
- empty: no child in the bed. A made bed, a smooth or rumpled duvet, pillows and plush toys \
are not a child.
- unclear: you can't tell, e.g. too dark, blurred or blocked.

Only say in_bed or child_up if you can point to part of her: head, hair, face, a hand or a \
foot, or a duvet clearly raised over a body shape. Name what you saw in the note. If you \
can't point to any of these, it's empty. Adults in or beside the bed don't change the label.

Also report whether an adult is visible: none, in_cot (lying or sitting in the bed) or \
beside_cot (leaning over, reaching in, standing next to it). The large grey or white padded \
shape in the bottom-left corner, outside the bed rail, is furniture, not a person. Only report \
an adult if you can see an adult's head, face, hand, arm or body."""

REFERENCE = """ The images before it are references of the same bed with no child in it, \
for comparison: bedding, pillows and toys move between frames, but compare the shapes."""

SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": LABELS},
        "adult": {"type": "string", "enum": ["none", "in_cot", "beside_cot"]},
        "lighting": {"type": "string", "enum": ["ir", "colour"]},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "note": {"type": "string"},
    },
    "required": ["label", "adult", "lighting", "confidence", "note"],
    "additionalProperties": False,
}

FIELDS = ["file", "label", "adult", "lighting", "confidence", "note", "model", "input_tokens", "output_tokens"]

# archive: camera.baby_monitor_profile000_20250510-211252.jpg, capture: 20261010-013000_periodic_...jpg
TIMESTAMP = re.compile(r"(\d{8})-\d{6}")


def frame_date(path):
    match = TIMESTAMP.search(path.name)
    return match.group(1) if match else None


def thumbnail(path, width, thumbs_dir):
    """Downscale once, keep it for the review page, return it base64-encoded."""
    thumb = thumbs_dir / path.name
    if not thumb.exists():
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((width, width))
            image.save(thumb, "JPEG", quality=85)
    return base64.standard_b64encode(thumb.read_bytes()).decode()


def image_block(data):
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}


def classify(client, model, path, width, thumbs_dir, references):
    data = thumbnail(path, width, thumbs_dir)
    prompt = PROMPT.format(reference=REFERENCE if references else "")
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [*map(image_block, references), image_block(data), {"type": "text", "text": prompt}],
        }],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"refused: {response.stop_details}")
    text = next(block.text for block in response.content if block.type == "text")
    result = json.loads(text)
    result.update(
        file=path.name,
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
    return result


def api_key():
    """ANTHROPIC_API_KEY if set, else the macOS keychain item anthropic-api-key."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        return subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        sys.exit(f"no API key: set ANTHROPIC_API_KEY or add keychain item {KEYCHAIN_SERVICE}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("image_dirs", type=Path, nargs="+")
    parser.add_argument("--since", default="20250501", help="skip frames before this date (YYYYMMDD)")
    parser.add_argument("--model", default="claude-sonnet-5-5", choices=PRICES)
    parser.add_argument("--width", type=int, default=768, help="long edge sent to the model")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, help="only this many new frames (for a trial run)")
    parser.add_argument("--reference", type=Path, action="append", default=[],
                        help="an image of the empty bed, sent with every frame (repeatable)")
    args = parser.parse_args()

    missing = [str(d) for d in args.image_dirs if not d.is_dir()]
    if missing:
        sys.exit(f"no such image folder: {', '.join(missing)}")

    thumbs_dir = args.out_dir / "thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    references = [thumbnail(path, args.width, thumbs_dir) for path in args.reference]
    csv_path = args.out_dir / "prelabels.csv"

    done = set()
    if csv_path.exists():
        with csv_path.open() as f:
            done = {row["file"] for row in csv.DictReader(f)}

    frames = sorted(
        path
        for image_dir in args.image_dirs
        for path in image_dir.glob("*.jpg")
        if (frame_date(path) or "") >= args.since and path.name not in done
    )
    if args.limit:
        frames = frames[: args.limit]
    print(f"{len(done)} already labelled, {len(frames)} to go", file=sys.stderr)
    if not frames:
        return

    client = anthropic.Anthropic(api_key=api_key())
    lock = threading.Lock()
    tokens_in = tokens_out = failed = 0
    new_file = not csv_path.exists()
    with csv_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        with ThreadPoolExecutor(args.workers) as pool:
            futures = {pool.submit(classify, client, args.model, path, args.width, thumbs_dir, references): path for path in frames}
            for i, future in enumerate(as_completed(futures), 1):
                path = futures[future]
                try:
                    result = future.result()
                except Exception as e:  # keep going; a rerun picks up whatever failed
                    failed += 1
                    print(f"failed {path.name}: {e}", file=sys.stderr)
                    continue
                with lock:
                    writer.writerow(result)
                    f.flush()
                    tokens_in += result["input_tokens"]
                    tokens_out += result["output_tokens"]
                if i % 50 == 0 or i == len(frames):
                    price_in, price_out = PRICES[args.model]
                    cost = tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out
                    print(f"{i}/{len(frames)}  ~${cost:.2f}", file=sys.stderr)

    print(f"done: {len(frames) - failed} labelled, {failed} failed", file=sys.stderr)


if __name__ == "__main__":
    main()
