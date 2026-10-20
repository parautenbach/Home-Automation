#!/usr/bin/env python3
"""Run the production in-bed check over frames, to validate it against the hand labels.

Mirrors what Home Assistant sends: the same prompt and fields, and the frame cropped to the
bed and downscaled the way the proxy cameras do it. Writes OUT_DIR/prelabels.csv in the
format score.py reads (child_up in the hand labels counts as in_bed: score with --merge-up).

Usage:
    check.py OUT_DIR IMAGE_DIR [IMAGE_DIR ...] [--model claude-sonnet-5-5] [--workers 8]
"""

import argparse
import base64
import csv
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
from PIL import Image

from prelabel import PRICES, api_key

# keep in sync with the nursery bed check in home_assistant/packages/home.yaml
PROMPT = """This is a frame from a camera above a toddler's bed: infrared greyscale at night, \
colour with a lamp on. Is the child in the bed?
- in_bed: you can see part of her in the bed (head, hair, face, a hand or a foot) or a duvet \
or blanket is clearly raised over a body. She may be covered or not, can lie in any direction, \
including with her head at the end nearest the camera, can sit, kneel or stand, and may be \
motion-blurred.
- empty: no child in the bed. Made or rumpled bedding, blankets, pillows and plush toys are \
not a child.
- unclear: you can't tell, e.g. too dark or blocked.
An adult in or beside the bed is not the child. Give the evidence in a few words."""

SCHEMA = {
    "type": "object",
    "properties": {
        "bed": {"type": "string", "enum": ["in_bed", "empty", "unclear"]},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "evidence": {"type": "string"},
    },
    "required": ["bed", "confidence", "evidence"],
    "additionalProperties": False,
}

# keep in sync with the nursery bed proxy cameras in home_assistant/packages/surveillance.yaml
CROP_WIDTH = 1440  # of 1920: the right quarter is wall
WIDTH = 576

FIELDS = ["file", "label", "confidence", "note", "model", "input_tokens", "output_tokens"]


def frame(path):
    with Image.open(path) as image:
        image = image.convert("RGB")
        image = image.crop((0, 0, CROP_WIDTH * image.width // 1920, image.height))
        image.thumbnail((WIDTH, WIDTH))
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=85)
    return base64.standard_b64encode(buffer.getvalue()).decode()


def check(client, model, path):
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": frame(path)}},
                {"type": "text", "text": PROMPT},
            ],
        }],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"refused: {response.stop_details}")
    text = next(block.text for block in response.content if block.type == "text")
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"stopped on {response.stop_reason}: {text!r}")
    result = json.loads(text)
    return {
        "file": path.name,
        "label": result["bed"],
        "confidence": result["confidence"],
        "note": result["evidence"],
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("image_dirs", type=Path, nargs="+")
    parser.add_argument("--model", default="claude-sonnet-5-5", choices=PRICES)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    missing = [str(d) for d in args.image_dirs if not d.is_dir()]
    if missing:
        sys.exit(f"no such image folder: {', '.join(missing)}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_dir / "prelabels.csv"
    done = set()
    if csv_path.exists():
        with csv_path.open() as f:
            done = {row["file"] for row in csv.DictReader(f)}
    frames = sorted(p for d in args.image_dirs for p in d.glob("*.jpg") if p.name not in done)
    print(f"{len(done)} already checked, {len(frames)} to go", file=sys.stderr)
    if not frames:
        return

    client = anthropic.Anthropic(api_key=api_key())
    price_in, price_out = PRICES[args.model]
    tokens_in = tokens_out = failed = 0
    new_file = not csv_path.exists()
    with csv_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        with ThreadPoolExecutor(args.workers) as pool:
            futures = {pool.submit(check, client, args.model, path): path for path in frames}
            for i, future in enumerate(as_completed(futures), 1):
                try:
                    result = future.result()
                except Exception as e:  # a rerun picks up whatever failed
                    failed += 1
                    print(f"failed {futures[future].name}: {e}", file=sys.stderr)
                    continue
                writer.writerow(result)
                f.flush()
                tokens_in += result["input_tokens"]
                tokens_out += result["output_tokens"]
                if i % 50 == 0 or i == len(frames):
                    cost = tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out
                    print(f"{i}/{len(frames)}  ~${cost:.2f}, ~${cost / i:.4f} per check", file=sys.stderr)

    print(f"done: {len(frames) - failed} checked, {failed} failed", file=sys.stderr)


if __name__ == "__main__":
    main()
