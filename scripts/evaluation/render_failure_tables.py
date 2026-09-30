#!/usr/bin/env python3
"""Render Table 3 (failure-mode decomposition, per question category) from a
summary JSON produced by run_failure_decomposition.py."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUCKETS = ("lost_at_write", "not_retrieved", "answer_visible")
HEADERS = ("Lost at write time (%)", "Not retrieved (%)", "Answer visible to reader (%)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--budget", default="0.25")
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def render(summary: dict, budget: str) -> str:
    cell = summary["by_budget"][budget]
    settings = summary["settings"]
    lines = [
        f"# Table 3: Failure-Mode Decomposition ({summary['dataset']}"
        + (f" / {summary['domain']}" if summary.get("domain") else "")
        + ")",
        "",
        f"- Memory budget: {float(budget):.0%} of full-context words (matched across systems).",
        f"- Retrieval: BM25, top-{settings['top_k']}; formation threshold tau={settings['tau']}.",
        f"- Memory unit: {settings.get('chunk_size', 1)} message(s); compressor: {settings['compressor']}.",
        f"- Graded questions: {summary['questions_graded']} of "
        f"{summary['questions_with_evidence']} evidence-linked "
        "(questions whose answer is not recoverable from gold evidence even at "
        "full fidelity are excluded, so the table measures the memory system "
        "rather than the evidence labels).",
        "",
        "Buckets are mutually exclusive and assigned in order. Splitting "
        "`answer visible` into `correct` and `retrieved but misinterpreted` "
        "requires a reader model; see docs/FAILURE_DECOMPOSITION.md.",
        "",
    ]
    categories = sorted({c for policy in cell.values() for c in policy})
    for category in ["ALL"] + [c for c in categories if c != "ALL"]:
        rows = {p: v[category] for p, v in cell.items() if category in v}
        if not rows:
            continue
        n = int(next(iter(rows.values()))["n"])
        lines += [f"## {category} (n={n})", "", "| System | " + " | ".join(HEADERS) + " |",
                  "| --- | ---: | ---: | ---: |"]
        for policy, values in rows.items():
            lines.append(
                f"| {policy} | " + " | ".join(f"{values[b]:.1f}" for b in BUCKETS) + " |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    text = render(summary, args.budget)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
