#!/usr/bin/env python3
"""Convert ConvoKit's Supreme Court Oral Arguments to the C4 utterance contract (JSONL).

Research use only -- ConvoKit states no licence for this corpus. See data/README.md.

    mkdir -p data/raw/supreme
    for y in 2017 2018 2019; do
      curl -L -o "data/raw/supreme/supreme-$y.zip" \
        "https://zissou.infosci.cornell.edu/convokit/datasets/supreme-corpus/supreme-$y.zip"
    done
    python scripts/data/convert_supreme.py --years 2017 2018 2019
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.supreme import convert  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", type=Path, default=ROOT / "data" / "raw" / "supreme")
    p.add_argument("--out", type=Path, default=ROOT / "data" / "processed" / "supreme.jsonl")
    p.add_argument("--years", nargs="*", default=None,
                   help="Only these years, e.g. --years 2017 2018 2019 (default: every one present).")
    args = p.parse_args()
    if not args.root.is_dir() or not any(p.name.startswith("supreme-") for p in args.root.iterdir()):
        print(f"no supreme-<year> zip or folder under {args.root}; download one first", file=sys.stderr)
        return 2
    rows = convert(args.root, args.years)
    if not rows:
        print(f"no utterances for years {args.years}; check --years against what is under {args.root}",
              file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    speakers = Counter(len({r["speaker"] for r in rows if r["conversation_id"] == c})
                       for c in {r["conversation_id"] for r in rows})
    print(f"{sum(speakers.values())} arguments, {len(rows)} utterances -> {args.out}")
    print("speakers per argument: " + ", ".join(f"{k}: {v}" for k, v in sorted(speakers.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
