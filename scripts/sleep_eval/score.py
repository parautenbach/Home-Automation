#!/usr/bin/env python3
"""Score model labels against hand labels.

Prints a confusion matrix per prelabels.csv, over the frames it shares with the hand
labels, and the two errors that matter most: a child present called empty, and an empty
bed called occupied.

--merge-up counts child_up as in_bed, for the in-bed/empty check.

Usage:
    score.py LABELS_CSV PRELABELS_CSV [PRELABELS_CSV ...] [--merge-up]
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

LABELS = ["in_bed", "child_up", "empty", "unclear"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("labels", type=Path)
    parser.add_argument("prelabels", type=Path, nargs="+")
    parser.add_argument("--merge-up", action="store_true", help="count child_up as in_bed")
    args = parser.parse_args()
    merge = {"child_up": "in_bed"} if args.merge_up else {}

    with args.labels.open() as f:
        truth = {row["file"]: merge.get(row["label"], row["label"]) for row in csv.DictReader(f)}

    for path in args.prelabels:
        with path.open() as f:
            predicted = {row["file"]: row for row in csv.DictReader(f) if row["file"] in truth}
        pairs = Counter((truth[file], merge.get(row["label"], row["label"])) for file, row in predicted.items())
        right = sum(n for (t, p), n in pairs.items() if t == p)
        print(f"\n{path}: {right}/{len(predicted)} right")
        print("truth \\ model".ljust(14) + "".join(label.rjust(10) for label in LABELS))
        for t in LABELS:
            print(t.ljust(14) + "".join(str(pairs[t, p]).rjust(10) for p in LABELS))

        missed = [(file, truth[file], row["confidence"]) for file, row in predicted.items()
                  if row["label"] == "empty" and truth[file] in ("in_bed", "child_up")]
        print(f"child called empty: {len(missed)}")
        for file, label, confidence in sorted(missed):
            print(f"  {file} ({label}, {confidence} confidence)")
        phantom = sum(n for (t, p), n in pairs.items() if t == "empty" and p in ("in_bed", "child_up"))
        print(f"empty called occupied: {phantom}")


if __name__ == "__main__":
    main()
