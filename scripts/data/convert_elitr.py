#!/usr/bin/env python3
"""Convert the ELITR Minuting Corpus (English) to the C4 utterance contract (JSONL).

    # see data/README.md: the old XMLUI bitstream URL is dead after DSpace 7
    curl -LO https://lindat.mff.cuni.cz/repository/server/api/core/bitstreams/76466f35-1bac-47bf-958b-c235b1fb4966/content
    unzip content -d data/raw/elitr
    python scripts/data/convert_elitr.py --root data/raw/elitr --out data/processed/elitr.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.elitr import ENGLISH, convert  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", type=Path, default=ROOT / "data" / "raw" / "elitr")
    p.add_argument("--out", type=Path, default=ROOT / "data" / "processed" / "elitr.jsonl")
    args = p.parse_args()
    if not (args.root / ENGLISH).is_dir() and not list(args.root.glob("*/meeting_*")):
        print(f"no {ENGLISH}/ folder under {args.root}; unzip the ELITR corpus there first", file=sys.stderr)
        return 2
    rows, dropped = convert(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    speakers = Counter(len({r["speaker"] for r in rows if r["conversation_id"] == m})
                       for m in {r["conversation_id"] for r in rows})
    meetings = sum(speakers.values())
    print(f"{meetings} meetings, {len(rows)} utterances -> {args.out}")
    print("speakers per meeting: " + ", ".join(f"{k}: {v}" for k, v in sorted(speakers.items())))
    if dropped:
        worst = ", ".join(f"{m} ({n})" for m, n in sorted(dropped.items(), key=lambda kv: -kv[1])[:3])
        print(f"dropped {sum(dropped.values())} unattributed line(s) before the first speaker marker "
              f"in {len(dropped)} meeting(s): {worst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
