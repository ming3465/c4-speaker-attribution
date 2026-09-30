#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.evaluation.retrieval_proxy import (  # noqa: E402
    load_labels,
    score_retrieval,
    score_retrieval_multi_domain,
    write_csv,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase 0 retrieval-aware proxy comparison."
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
        "--raw-domain-file",
        type=Path,
        default=ROOT
        / "data"
        / "raw"
        / "groupmembench"
        / "synthetic_domain_channels_rolevariants_Finance.json",
        help="Raw GroupMemBench domain JSON.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data" / "raw" / "groupmembench",
        help="Raw GroupMemBench directory for --multi-domain mode.",
    )
    parser.add_argument(
        "--multi-domain",
        action="store_true",
        help="Group labels by domain and load matching raw files from --raw-dir.",
    )
    parser.add_argument("--domain", default="Finance", help="GroupMemBench domain.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "experiments" / "phase0_oracle_validation.json",
        help="Phase 0 experiment config JSON.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Retrieval top-k.")
    parser.add_argument(
        "--success-threshold",
        type=float,
        default=0.65,
        help="Answer-token coverage threshold for visible retrieval success.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=ROOT
        / "results"
        / "comparisons"
        / "phase_0_oracle_validation"
        / "retrieval_proxy_summary.json",
        help="Summary JSON output path.",
    )
    parser.add_argument(
        "--row-output",
        type=Path,
        default=ROOT
        / "results"
        / "comparisons"
        / "phase_0_oracle_validation"
        / "retrieval_proxy_rows.csv",
        help="Per-label CSV output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    policy = config["initial_compression_policy"]
    labels = load_labels(args.labels)
    if args.multi_domain:
        rows, summary = score_retrieval_multi_domain(
            raw_dir=args.raw_dir,
            labels=labels,
            shared_core_tokens=int(policy["shared_core_tokens"]),
            residual_tokens=int(policy["oracle_consumer_residual_tokens"]),
            top_k=args.top_k,
            success_threshold=args.success_threshold,
        )
        raw_source = str(args.raw_dir)
    else:
        rows, summary = score_retrieval(
            raw_domain_file=args.raw_domain_file,
            domain=args.domain,
            labels=labels,
            shared_core_tokens=int(policy["shared_core_tokens"]),
            residual_tokens=int(policy["oracle_consumer_residual_tokens"]),
            top_k=args.top_k,
            success_threshold=args.success_threshold,
        )
        raw_source = str(args.raw_domain_file)
    report = {
        "labels": str(args.labels),
        "raw_source": raw_source,
        "multi_domain": args.multi_domain,
        "label_count": len(labels),
        "top_k": args.top_k,
        "success_threshold": args.success_threshold,
        "policy": policy,
        "summary": summary,
        "caveat": (
            "This is a retrieval-aware lexical proxy over bootstrap labels. "
            "Queries are synthesized from decision-change metadata, not official "
            "GroupMemBench question rows."
        ),
    }
    write_json(args.summary_output, report)
    write_csv(args.row_output, rows)
    print(f"Scored {len(labels)} labels with top_k={args.top_k}")
    print(f"Wrote summary to {args.summary_output}")
    print(f"Wrote rows to {args.row_output}")
    for strategy, values in summary.items():
        print(
            f"{strategy}: recall@{args.top_k}={values['recall_at_k']}, "
            f"coverage={values['avg_answer_coverage_in_top_k']}, "
            f"success={values['retrieval_visible_success_rate']}, "
            f"avg_index_words={values['avg_indexed_word_count']}"
        )


if __name__ == "__main__":
    main()
