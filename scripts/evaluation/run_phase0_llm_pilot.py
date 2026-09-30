#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.evaluation.llm_pilot import (  # noqa: E402
    DEFAULT_PILOT_STRATEGIES,
    answer_prompt,
    judge_prompt,
    load_jsonl_labels,
    parse_judgments,
    retrieved_context_for_strategy,
    run_codex_exec,
    select_stratified_labels,
    summarize_judged_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a real LLM Phase 0 pilot.")
    parser.add_argument(
        "--labels",
        type=Path,
        default=ROOT
        / "data"
        / "processed"
        / "groupmembench"
        / "oracle_labels.bootstrap_all_domains.jsonl",
        help="Bootstrap oracle labels JSONL.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data" / "raw" / "groupmembench",
        help="Raw GroupMemBench domain JSON directory.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "experiments" / "phase0_oracle_validation.json",
        help="Phase 0 experiment config JSON.",
    )
    parser.add_argument("--sample-size", type=int, default=4)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=list(DEFAULT_PILOT_STRATEGIES),
        help="Allocation strategies to evaluate.",
    )
    parser.add_argument(
        "--codex-path",
        type=Path,
        default=Path("/Users/rjustyn1/.local/bin/codex"),
        help="Codex CLI path used as the LLM runner.",
    )
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT
        / "results"
        / "comparisons"
        / "phase_0_oracle_validation"
        / "llm_pilot",
    )
    return parser.parse_args()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    policy = config["initial_compression_policy"]
    labels = select_stratified_labels(load_jsonl_labels(args.labels), args.sample_size)

    output_rows: list[dict] = []
    for label in labels:
        for strategy in args.strategies:
            context = retrieved_context_for_strategy(
                raw_dir=args.raw_dir,
                label=label,
                strategy=strategy,
                shared_core_tokens=int(policy["shared_core_tokens"]),
                residual_tokens=int(policy["oracle_consumer_residual_tokens"]),
                top_k=args.top_k,
            )
            prompt = answer_prompt(label, context)
            model_answer = run_codex_exec(
                codex_path=args.codex_path,
                model=args.model,
                cwd=ROOT,
                prompt=prompt,
                timeout_seconds=args.timeout_seconds,
            )
            output_rows.append(
                {
                    "row_id": f"{label['label_id']}::{strategy}",
                    "label_id": label["label_id"],
                    "domain": label["domain"],
                    "strategy": strategy,
                    "question": context["query"],
                    "question_asker": label["question_asker"],
                    "question_asker_role": label["question_asker_role"],
                    "gold_answer": label["answer"],
                    "model_answer": model_answer,
                    "gold_evidence_retrieved": context["gold_evidence_retrieved"],
                    "retrieved_ids": " ".join(
                        snippet["msg_node"] for snippet in context["snippets"]
                    ),
                }
            )
            print(f"Answered {output_rows[-1]['row_id']}")

    judgment_text = run_codex_exec(
        codex_path=args.codex_path,
        model=args.model,
        cwd=ROOT,
        prompt=judge_prompt(output_rows),
        timeout_seconds=args.timeout_seconds,
    )
    judgments = parse_judgments(judgment_text)
    judgment_by_id = {
        judgment["row_id"]: judgment for judgment in judgments.get("judgments", [])
    }
    for row in output_rows:
        judgment = judgment_by_id.get(row["row_id"], {})
        row["judge_correct"] = bool(judgment.get("correct", False))
        row["judge_rationale"] = str(judgment.get("rationale", "missing judgment"))

    summary = {
        "model": args.model,
        "sample_size": len(labels),
        "strategy_count": len(args.strategies),
        "prediction_count": len(output_rows),
        "top_k": args.top_k,
        "labels": str(args.labels),
        "summary": summarize_judged_rows(output_rows),
        "caveat": (
            "This is a real LLM answer-generation pilot over bootstrap questions "
            "derived from decision-change metadata. It is not an official "
            "GroupMemBench benchmark."
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "predictions.jsonl", output_rows)
    write_csv(args.output_dir / "predictions.csv", output_rows)
    (args.output_dir / "judge_raw.txt").write_text(judgment_text, encoding="utf-8")
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary["summary"], indent=2))
    print(f"Wrote pilot outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
