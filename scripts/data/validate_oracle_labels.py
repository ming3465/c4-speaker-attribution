#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.evaluation.oracle_labels import (  # noqa: E402
    load_jsonl,
    validate_oracle_labels,
    write_validation_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Phase 0 oracle labels.")
    parser.add_argument("--input", type=Path, required=True, help="Oracle label JSONL.")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT
        / "results"
        / "comparisons"
        / "phase_0_oracle_validation"
        / "oracle_label_validation.json",
        help="Where to write validation issues.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_jsonl(args.input)
    issues = validate_oracle_labels(records)
    write_validation_report(issues, args.report)
    print(f"Validated {len(records)} rows")
    print(f"Found {len(issues)} issues")
    print(f"Wrote report to {args.report}")
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
