#!/usr/bin/env python3
"""Complete Table 3 by splitting `answer_visible` (Contribution 4).

STATUS: PILOT (C4 v0 reader pass over the original failure decomposition, which WhenLoss published first); C4 v1 still imports build_reader_items. See docs/C4_RUNBOOK.md, 'Code status'.

C4 leaves 'answer_visible' unsorted: the evidence survived and was retrieved,
but nobody checked whether the model read it correctly. This asks a reader
model each such question and splits the bucket into `correct` and
`retrieved_but_misinterpreted` -- the second being the only bucket that can
support the C3 interpretation claim.

Validate the plumbing first, for free:
    python scripts/evaluation/run_reader_pass.py --backend stub --limit 20

Then run the real reader (uses the `codex` CLI, same as the Phase 0 pilot):
    python scripts/evaluation/run_reader_pass.py --backend codex --limit 40

The stub is a pipeline test, not a result. It answers by copying the retrieved
snippets, so it reproduces C4's own lexical criterion by construction.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.memory_tasks import load_pilot_bundle  # noqa: E402
from src.evaluation.failure_decomposition import POLICIES  # noqa: E402
from src.evaluation.reader_pass import (  # noqa: E402
    CodexReader,
    CommandReader,
    OllamaReader,
    StubReader,
    build_reader_items,
    judge_lexical,
    run_reader_pass,
    summarize,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "data" / "pilot" / "c4")
    parser.add_argument("--corpus", default="corpus_10pct.jsonl")
    parser.add_argument("--policy", default="oracle_future_consumer", choices=list(POLICIES))
    parser.add_argument("--budget", type=float, default=0.25)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--tau", type=float, default=0.65)
    parser.add_argument(
        "--backend",
        choices=("stub", "codex", "ollama", "command"),
        default="stub",
    )
    parser.add_argument(
        "--command",
        default="",
        help='For --backend command: a CLI taking the prompt on stdin, e.g. "./azure_wrapper.sh".',
    )
    parser.add_argument("--model", default="gpt-5.6-sol", help="Reader model for --backend codex.")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Cap the number of questions sent to the reader (0 = all). "
             "Start small: every item is one model call.",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=ROOT / "results" / "proposed" / "reader_pass"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    units, questions = load_pilot_bundle(args.bundle, args.corpus)
    items = build_reader_items(
        units,
        questions,
        policy=args.policy,
        budget=args.budget,
        top_k=args.top_k,
        tau=args.tau,
    )
    print(
        f"{args.policy} @ budget={args.budget}: "
        f"{len(items)} questions in the answer_visible bucket"
    )
    if not items:
        print("nothing to split")
        return 1

    if args.limit:
        items = items[: args.limit]
        print(f"limited to {len(items)} (every item is one model call)")

    if args.backend == "ollama":
        if not shutil.which("ollama"):
            print("ollama not on PATH.", file=sys.stderr)
            return 2
        backend = OllamaReader(model=args.model, timeout_seconds=args.timeout_seconds)
        print(f"reader: ollama ({args.model}) -- needs `ollama serve` running")
    elif args.backend == "command":
        if not args.command:
            print("--backend command requires --command", file=sys.stderr)
            return 2
        backend = CommandReader(command=args.command, timeout_seconds=args.timeout_seconds)
        print(f"reader: command ({args.command})")
    elif args.backend == "codex":
        codex_path = shutil.which("codex")
        if not codex_path:
            print(
                "codex CLI not found on PATH. Install it, or run --backend stub "
                "to validate the pipeline without it.",
                file=sys.stderr,
            )
            return 2
        backend = CodexReader(
            codex_path=Path(codex_path),
            model=args.model,
            cwd=ROOT,
            timeout_seconds=args.timeout_seconds,
        )
        print(f"reader: codex ({args.model})")
    else:
        backend = StubReader()
        print("reader: stub -- PLUMBING TEST ONLY, these numbers are not a result")

    def progress(done: int, total: int) -> None:
        if args.backend == "codex" or done == total:
            print(f"  {done}/{total}", end="\r", flush=True)

    rows = run_reader_pass(
        items,
        backend,
        judge=lambda gold, got: judge_lexical(gold, got, tau=args.tau),
        on_progress=progress,
    )
    print()

    summary = summarize(rows)
    total = summary["answer_visible_items"]
    print(f"\nanswer_visible split ({total} questions):")
    print(f"  correct                       {summary['correct']:>4}  "
          f"({summary['correct_share'] * 100:.1f}%)")
    print(f"  retrieved_but_misinterpreted  {summary['retrieved_but_misinterpreted']:>4}  "
          f"({(1 - summary['correct_share']) * 100:.1f}%)")
    if summary["errors"]:
        print(f"  errors (counted as misinterpreted) {summary['errors']}")

    print("\nby category:")
    for category, counts in summary["by_category"].items():
        n = counts["correct"] + counts["retrieved_but_misinterpreted"]
        print(f"  {category:<18} correct={counts['correct']:>3}/{n:<3} "
              f"misinterpreted={counts['retrieved_but_misinterpreted']:>3}")

    if args.backend == "stub":
        print(
            "\nreminder: --backend stub only proves the pipeline runs. "
            "Re-run with --backend codex for a real split."
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    # Model goes in the filename: two readers on the same policy/budget are
    # different results, and without this the second run silently overwrites
    # the first.
    model_tag = re.sub(r"[^A-Za-z0-9.]+", "-", args.model) if args.backend in ("ollama", "codex") else args.backend
    tag = f"{args.policy}_budget{args.budget}_{args.backend}_{model_tag}"
    csv_path = args.out_dir / f"reader_{tag}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    json_path = args.out_dir / f"summary_{tag}.json"
    json_path.write_text(
        json.dumps(
            {
                "policy": args.policy,
                "budget": args.budget,
                "backend": args.backend,
                "model": args.model if args.backend == "codex" else None,
                "is_plumbing_test_only": args.backend == "stub",
                **summary,
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
