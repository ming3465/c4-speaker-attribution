#!/usr/bin/env python3
"""Can future consumers be predicted from the past? (Contribution 1)

STATUS: PILOT SKELETON (lexical C1-C3 prototype); the current C1-C3 implementation lives outside this repo. See docs/C4_RUNBOOK.md, 'Code status'.

C4 showed the oracle is worth having: 0.0% lost_at_write at a 0.25 budget where
every fixed policy loses 60-67%. That oracle reads gold. This script asks the
prerequisite question -- does a predictor that only sees the past recover any of
that signal -- before any GPU time is spent on the learned scorer.

Read the result as a gate, not a headline:
    lexical <= random   no usable signal in the text; rethink C1
    lexical >  random   signal exists; the learned scorer has something to beat

Example:
    python scripts/evaluation/run_consumer_prediction.py --thresholds 0.05 0.1 0.2
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.memory_tasks import load_pilot_bundle  # noqa: E402
from src.memory.consumer_prediction import (  # noqa: E402
    LexicalInterestPredictor,
    RandomConsumerPredictor,
    evaluate_predictor,
    evaluate_ranking,
    gold_consumers,
    split_questions,
    to_consumer_sets,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "data" / "pilot" / "c4")
    parser.add_argument("--corpus", default="corpus_10pct.jsonl")
    parser.add_argument("--train-share", type=float, default=0.5)
    parser.add_argument("--thresholds", type=float, nargs="+", default=[0.02, 0.05, 0.1, 0.2])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--rank-splits",
        type=int,
        default=10,
        help="Independent train/eval splits for the threshold-free ranking test.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "results" / "proposed" / "consumer_prediction",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    units, questions = load_pilot_bundle(args.bundle, args.corpus)
    train, evaluation = split_questions(
        questions, train_share=args.train_share, seed=args.seed
    )

    # Gold for grading comes from the eval split only. Building it from every
    # question would score the predictor on pairs it was fitted on.
    gold = gold_consumers(evaluation)
    participants = sorted({q.asker for q in questions})
    units_by_uid = {unit.uid: unit for unit in units}

    # Only units that are evidence for some eval question can be graded.
    graded_uids = {uid for uid, consumers in gold.items() if consumers}
    graded_units = [units_by_uid[uid] for uid in sorted(graded_uids) if uid in units_by_uid]

    print(
        f"{args.corpus}: {len(units)} units, {len(questions)} questions "
        f"({len(train)} train / {len(evaluation)} eval), "
        f"{len(participants)} participants"
    )
    print(f"gradable units (evidence for >=1 eval question): {len(graded_units)}")

    if not graded_units:
        print("no gradable units; nothing to report")
        return 1

    lexical = LexicalInterestPredictor()
    lexical.fit(train, units_by_uid)

    # Matched pair-rate control: the random predictor is given the same
    # expected number of positive pairs the lexical one produces, so a gain
    # cannot come from simply predicting more.
    reports = []
    for threshold in args.thresholds:
        lexical_scores = lexical.predict(graded_units, participants)
        lexical_sets = to_consumer_sets(lexical_scores, threshold=threshold)
        lexical_pairs = sum(len(v) for v in lexical_sets.values())
        rate = lexical_pairs / max(1, len(graded_units) * len(participants))

        random_predictor = RandomConsumerPredictor(rate=rate, seed=args.seed)
        random_sets = to_consumer_sets(
            random_predictor.predict(graded_units, participants), threshold=0.5
        )

        reports.append(
            evaluate_predictor(
                lexical_sets, gold, predictor="lexical_interest", threshold=threshold
            )
        )
        reports.append(
            evaluate_predictor(
                random_sets, gold, predictor="random_matched", threshold=threshold
            )
        )

    print()
    header = f"{'threshold':>9}  {'predictor':<18} {'P':>7} {'R':>7} {'F1':>7} {'pairs':>7}"
    print(header)
    print("-" * len(header))
    for report in reports:
        print(
            f"{report.threshold:>9.3f}  {report.predictor:<18} "
            f"{report.precision:>7.3f} {report.recall:>7.3f} {report.f1:>7.3f} "
            f"{report.predicted_pairs:>7}"
        )

    # Ranking is the verdict metric. A global threshold conflates ranking
    # quality with score calibration, and the lexical scores are near-uniform,
    # so the threshold table above understates the signal. Allocation only
    # needs relative order, which is what this measures.
    ranking_rows = []
    for seed in range(args.rank_splits):
        r_train, r_eval = split_questions(
            questions, train_share=args.train_share, seed=seed
        )
        r_gold = gold_consumers(r_eval)
        r_units = [
            units_by_uid[uid]
            for uid in sorted({u for u, c in r_gold.items() if c})
            if uid in units_by_uid
        ]
        if not r_units:
            continue
        r_lex = LexicalInterestPredictor()
        r_lex.fit(r_train, units_by_uid)
        ranking_rows.append(
            evaluate_ranking(
                r_lex.predict(r_units, participants),
                r_gold,
                predictor="lexical_interest",
                seed=seed,
            )
        )

    roster = len(participants)
    chance_mrr = sum(1.0 / k for k in range(1, roster + 1)) / roster
    chance_hit1 = 1.0 / roster
    mean_mrr = sum(r.mrr for r in ranking_rows) / len(ranking_rows)
    mean_hit1 = sum(r.hit_at_1 for r in ranking_rows) / len(ranking_rows)
    above = sum(r.mrr > chance_mrr for r in ranking_rows)

    print(f"\nranking over {len(ranking_rows)} independent splits (threshold-free):")
    print(f"  lexical MRR    = {mean_mrr:.4f}   chance = {chance_mrr:.4f}")
    print(f"  lexical hit@1  = {mean_hit1:.4f}   chance = {chance_hit1:.4f}")
    print(f"  splits above chance: {above}/{len(ranking_rows)}")
    print(
        "\nverdict: "
        + (
            "future-consumer signal is present (weak). The learned scorer has "
            "a real floor to beat."
            if above == len(ranking_rows) and mean_mrr > chance_mrr
            else "no consistent signal; do not spend GPU time on C1 yet."
        )
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_dir / "consumer_prediction.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(reports[0].as_row()))
        writer.writeheader()
        for report in reports:
            writer.writerow(report.as_row())

    json_path = args.out_dir / "summary.json"
    json_path.write_text(
        json.dumps(
            {
                "corpus": args.corpus,
                "units": len(units),
                "questions": len(questions),
                "train_questions": len(train),
                "eval_questions": len(evaluation),
                "participants": len(participants),
                "graded_units": len(graded_units),
                "reports": [r.as_row() for r in reports],
                "ranking": [r.as_row() for r in ranking_rows],
                "chance_mrr": round(chance_mrr, 4),
                "chance_hit_at_1": round(chance_hit1, 4),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {csv_path}")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
