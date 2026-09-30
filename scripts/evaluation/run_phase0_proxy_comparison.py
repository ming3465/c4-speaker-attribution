#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.evaluation.proxy_allocation import (  # noqa: E402
    load_labels,
    score_labels,
    write_csv,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase 0 proxy comparison for memory allocation strategies."
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=ROOT
        / "data"
        / "processed"
        / "groupmembench"
        / "oracle_labels.bootstrap.jsonl",
        help="Oracle label JSONL.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "experiments" / "phase0_oracle_validation.json",
        help="Phase 0 experiment config JSON.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=ROOT
        / "results"
        / "comparisons"
        / "phase_0_oracle_validation"
        / "proxy_summary.json",
        help="Summary JSON output path.",
    )
    parser.add_argument(
        "--row-output",
        type=Path,
        default=ROOT
        / "results"
        / "comparisons"
        / "phase_0_oracle_validation"
        / "proxy_rows.csv",
        help="Per-label CSV output path.",
    )
    parser.add_argument(
        "--success-threshold",
        type=float,
        default=0.65,
        help="Answer-token coverage threshold for proxy formation success.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    policy = config["initial_compression_policy"]
    labels = load_labels(args.labels)
    rows, summary = score_labels(
        labels,
        shared_core_tokens=int(policy["shared_core_tokens"]),
        residual_tokens=int(policy["oracle_consumer_residual_tokens"]),
        success_threshold=args.success_threshold,
    )
    report = {
        "labels": str(args.labels),
        "label_count": len(labels),
        "success_threshold": args.success_threshold,
        "policy": policy,
        "summary": summary,
        "caveat": (
            "This is a deterministic proxy over bootstrap labels, not a final "
            "LLM benchmark. It measures whether gold answer terms are visible "
            "to the future consumer under each allocation strategy."
        ),
    }
    write_json(args.summary_output, report)
    write_csv(args.row_output, rows)
    print(f"Scored {len(labels)} labels")
    print(f"Wrote summary to {args.summary_output}")
    print(f"Wrote rows to {args.row_output}")
    for strategy, values in summary.items():
        print(
            f"{strategy}: coverage={values['avg_answer_coverage']}, "
            f"success={values['formation_success_rate']}, "
            f"avg_words={values['avg_stored_word_count']}"
        )


if __name__ == "__main__":
    main()
