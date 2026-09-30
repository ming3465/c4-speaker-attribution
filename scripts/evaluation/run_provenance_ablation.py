#!/usr/bin/env python3
"""Does the reader actually need to know who is talking? (replacement for C4)

STATUS: PILOT SKELETON (lexical C1-C3 prototype); the current C1-C3 implementation lives outside this repo. See docs/C4_RUNBOOK.md, 'Code status'.

WhenLoss (arXiv 2605.24579) already decomposes memory failures into write-side
and retrieval-side gaps, so that instrument is taken. What its setting cannot
ask is this one: every benchmark it uses is a single user talking to an
assistant, so "who said it" and "who is asking" carry no information.

This is the multi-party question. Four conditions over identical questions,
identical evidence and an identical reader -- only the identity information
changes:

    baseline      speaker+role shown, true asker shown
    no_speaker    speaker+role stripped from snippets
    wrong_asker   a different real participant named as the asker
    neither       both removed

Read the result as a gate on the rest of the project:
    scores flat        -> identity is decorative; C2 and C3 have no foundation
    scores drop        -> provenance is load-bearing, and that is the opening claim

Example:
    python scripts/evaluation/run_provenance_ablation.py --model qwen2.5:7b
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.memory_tasks import load_pilot_bundle  # noqa: E402
from src.evaluation.failure_decomposition import POLICIES  # noqa: E402
from src.evaluation.reader_pass import (  # noqa: E402
    OllamaReader,
    StubReader,
    build_reader_items,
    judge_lexical,
    run_reader_pass,
    summarize,
)

CONDITIONS = {
    "baseline":    dict(hide_provenance=False, swap_asker=False),
    "no_speaker":  dict(hide_provenance=True,  swap_asker=False),
    "wrong_asker": dict(hide_provenance=False, swap_asker=True),
    "neither":     dict(hide_provenance=True,  swap_asker=True),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "data" / "pilot" / "c4")
    parser.add_argument("--corpus", default="corpus_10pct.jsonl")
    parser.add_argument("--policy", default="oracle_future_consumer", choices=list(POLICIES))
    parser.add_argument("--budget", type=float, default=0.25)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--tau", type=float, default=0.65)
    parser.add_argument("--backend", choices=("stub", "ollama"), default="ollama")
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--out-dir", type=Path, default=ROOT / "results" / "proposed" / "provenance_ablation"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    units, questions = load_pilot_bundle(args.bundle, args.corpus)

    if args.backend == "ollama":
        if not shutil.which("ollama"):
            print("ollama not on PATH", file=sys.stderr)
            return 2
        backend = OllamaReader(model=args.model, timeout_seconds=args.timeout_seconds)
        reader_name = f"ollama/{args.model}"
    else:
        backend = StubReader()
        reader_name = "stub"

    print(f"policy={args.policy} budget={args.budget} reader={reader_name}")

    results: dict[str, dict] = {}
    all_rows: list[dict] = []

    for name, knobs in CONDITIONS.items():
        items = build_reader_items(
            units, questions,
            policy=args.policy, budget=args.budget,
            top_k=args.top_k, tau=args.tau,
            swap_seed=args.seed, **knobs,
        )
        if knobs["hide_provenance"] and knobs["swap_asker"]:
            # "neither" also removes the asker line entirely
            for item in items:
                item.shown_asker = ""
        if args.limit:
            items = items[: args.limit]

        print(f"\n-- {name}: {len(items)} questions")
        rows = run_reader_pass(
            items, backend,
            judge=lambda gold, got: judge_lexical(gold, got, tau=args.tau),
            on_progress=lambda d, t: print(f"   {d}/{t}", end="\r", flush=True),
        )
        for row in rows:
            row["condition"] = name
        all_rows.extend(rows)
        results[name] = summarize(rows)
        print(f"   correct {results[name]['correct']}/{len(items)} "
              f"({results[name]['correct_share']*100:.1f}%)")

    base = results["baseline"]["correct_share"]
    print("\n" + "=" * 62)
    print(f"{'condition':<14}{'correct':>9}{'share':>9}{'vs baseline':>14}")
    print("-" * 62)
    for name in CONDITIONS:
        r = results[name]
        delta = (r["correct_share"] - base) * 100
        mark = "" if name == "baseline" else f"{delta:+.1f} pts"
        print(f"{name:<14}{r['correct']:>9}{r['correct_share']*100:>8.1f}%{mark:>14}")

    worst = min(results[n]["correct_share"] for n in CONDITIONS)
    swing = (base - worst) * 100
    print("=" * 62)
    print(f"largest drop from baseline: {swing:.1f} points")
    print(
        "\nverdict: "
        + (
            "identity information changes the answer -- provenance is load-bearing."
            if swing >= 5.0
            else "no meaningful effect. Identity may be decorative here; C2/C3 "
                 "need a stronger justification than this pilot provides."
        )
    )
    n = results["baseline"]["answer_visible_items"]
    print(f"\nn = {n} questions per condition. With n this small, a swing under "
          f"~{100/max(n,1)*2:.0f} points is within noise -- treat as directional only.")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{args.policy}_budget{args.budget}_{args.model.replace(':','-')}"
    csv_path = args.out_dir / f"ablation_{tag}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    json_path = args.out_dir / f"summary_{tag}.json"
    json_path.write_text(json.dumps(
        {"policy": args.policy, "budget": args.budget, "reader": reader_name,
         "conditions": results}, indent=2), encoding="utf-8")
    print(f"\nwrote {csv_path}\nwrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
