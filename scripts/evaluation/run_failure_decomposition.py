#!/usr/bin/env python3
"""Run the Contribution 4 failure-mode decomposition (Table 3).

Example:
    python scripts/evaluation/run_failure_decomposition.py --dataset groupmembench \
        --domain Finance --budgets 0.1 0.25 0.5 0.75
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.memory_tasks import (  # noqa: E402
    load_groupmembench,
    load_locomo,
    load_pilot_bundle,
)
from src.evaluation.failure_decomposition import (  # noqa: E402
    BUCKETS,
    POLICIES,
    BM25Index,
    MemoryQuestion,
    build_store,
    chunk_units,
    corpus_idf,
    decompose_question,
    salience_order,
    summarize,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("groupmembench", "locomo", "pilot"), default="groupmembench")
    parser.add_argument("--bundle", type=Path, default=ROOT / "data" / "pilot" / "c4")
    parser.add_argument("--corpus", default="corpus_10pct.jsonl", help="Corpus file inside --bundle.")
    parser.add_argument("--domain", default="Finance")
    parser.add_argument("--budgets", type=float, nargs="+", default=[0.1, 0.25, 0.5, 0.75])
    parser.add_argument("--policies", nargs="+", default=list(POLICIES))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--tau", type=float, default=0.65)
    parser.add_argument("--core-share", type=float, default=0.5)
    parser.add_argument("--compressor", choices=("salient", "prefix"), default="salient")
    parser.add_argument("--chunk-size", type=int, default=1, help="Messages per memory unit.")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "proposed" / "failure_decomposition")
    return parser.parse_args()


def load(args: argparse.Namespace):
    if args.dataset == "pilot":
        return load_pilot_bundle(args.bundle, args.corpus)
    if args.dataset == "locomo":
        return load_locomo(ROOT / "data" / "raw" / "locomo" / "locomo10.json")
    return load_groupmembench(
        ROOT / "data" / "raw" / "groupmembench" / f"synthetic_domain_channels_rolevariants_{args.domain}.json",
        ROOT / "data" / "raw" / "groupmembench" / "questions" / args.domain,
        ROOT / "data" / "raw" / "gmb_agent_sessions" / args.domain.lower() / "questions_enhanced.jsonl",
    )


def main() -> int:
    args = parse_args()
    units, questions = load(args)
    if args.chunk_size > 1:
        units, mapping = chunk_units(units, args.chunk_size)
        questions = [
            MemoryQuestion(
                q.qid, q.category, q.question, q.answer, q.asker,
                tuple(dict.fromkeys(mapping[u] for u in q.evidence_uids if u in mapping)),
            )
            for q in questions
        ]
        questions = [q for q in questions if q.evidence_uids]
    label = f"{args.dataset}/{args.domain}" if args.dataset == "groupmembench" else args.dataset
    if args.dataset == "pilot":
        label = f"pilot/{Path(args.corpus).stem}"
    print(f"{label}: {len(units)} units, {len(questions)} evidence-linked questions")

    idf = corpus_idf(units)
    salience = {unit.uid: salience_order(unit.text, idf) for unit in units}
    by_group: dict[str, list] = defaultdict(list)
    for unit in units:
        by_group[unit.group].append(unit)

    consumers: dict[str, set[str]] = defaultdict(set)
    for question in questions:
        for uid in question.evidence_uids:
            consumers[uid].add(question.asker)

    full = {unit.uid: unit.text for unit in units}
    full_index = BM25Index(full)
    baseline = {
        row["qid"]: row
        for row in (
            decompose_question(q, full, full_index, top_k=args.top_k, tau=args.tau)
            for q in questions
        )
    }
    eligible = {qid for qid, row in baseline.items() if row["bucket"] != "lost_at_write"}
    print(f"eligible (answer recoverable from gold evidence at full fidelity): {len(eligible)}/{len(questions)}")
    graded = [q for q in questions if q.qid in eligible]

    rows: list[dict] = []
    for budget in args.budgets:
        for policy in args.policies:
            stored: dict[str, str] = {}
            for group_units in by_group.values():
                stored |= build_store(
                    group_units,
                    policy=policy,
                    budget_fraction=budget,
                    salience=salience,
                    consumers_by_uid=consumers,
                    core_share=args.core_share,
                    compressor=args.compressor,
                )
            index = BM25Index(stored)
            stored_words = sum(len(text.split()) for text in stored.values())
            detail = [
                decompose_question(q, stored, index, top_k=args.top_k, tau=args.tau)
                for q in graded
            ]
            for row in detail:
                rows.append({"budget": budget, "policy": policy} | row)
            table = summarize(detail)
            print(
                f"  budget={budget:<5} {policy:<28} "
                + "  ".join(f"{b}={table['ALL'][b]:5.1f}%" for b in BUCKETS)
                + f"  stored_words={stored_words}"
            )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{args.dataset}_{args.domain}" if args.dataset == "groupmembench" else args.dataset
    if args.dataset == "pilot":
        tag = f"pilot_{Path(args.corpus).stem}"
    if args.chunk_size > 1:
        tag += f"_chunk{args.chunk_size}"
    detail_path = args.out_dir / f"decomposition_{tag}.csv"
    with detail_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["budget", "policy", "qid", "category", "bucket", "best_support",
                        "evidence_units", "surviving_units", "gold_in_topk"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = defaultdict(dict)
    for budget in args.budgets:
        for policy in args.policies:
            subset = [r for r in rows if r["budget"] == budget and r["policy"] == policy]
            summary[str(budget)][policy] = summarize(subset)
    summary_path = args.out_dir / f"summary_{tag}.json"
    summary_path.write_text(
        json.dumps(
            {
                "dataset": args.dataset,
                "domain": args.domain if args.dataset == "groupmembench" else None,
                "units": len(units),
                "questions_with_evidence": len(questions),
                "questions_graded": len(graded),
                "settings": {"top_k": args.top_k, "tau": args.tau,
                             "core_share": args.core_share, "compressor": args.compressor,
                             "chunk_size": args.chunk_size},
                "by_budget": summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {detail_path}\nwrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
