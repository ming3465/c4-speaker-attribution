#!/usr/bin/env python3
"""Convert the AMI manual annotations to the C4 utterance contract (JSONL).

    curl -LO https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
    unzip ami_public_manual_1.6.2.zip -d data/raw/ami
    python scripts/data/convert_ami.py --root data/raw/ami --out data/processed/ami.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.ami import convert  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", type=Path, default=ROOT / "data" / "raw" / "ami")
    p.add_argument("--out", type=Path, default=ROOT / "data" / "processed" / "ami.jsonl")
    args = p.parse_args()
    if not (args.root / "words").is_dir():
        print(f"no words/ folder under {args.root}; unzip the AMI annotations there first", file=sys.stderr)
        return 2
    rows = convert(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    speakers = Counter(len({r["speaker"] for r in rows if r["conversation_id"] == m})
                       for m in {r["conversation_id"] for r in rows})
    meetings = sum(speakers.values())
    print(f"{meetings} meetings, {len(rows)} utterances -> {args.out}")
    print("speakers per meeting: " + ", ".join(f"{k}: {v}" for k, v in sorted(speakers.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
