#!/usr/bin/env python3
"""Flatten every failure-decomposition summary JSON into one tidy CSV.

One row per (run, budget, policy, question category) so the numbers can be
pivoted, pasted into the paper, or diffed between runs.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUCKETS = ("lost_at_write", "not_retrieved", "answer_visible")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-dir", type=Path, default=ROOT / "results" / "proposed" / "failure_decomposition")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "pilot" / "c4" / "results_table3.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows: list[dict] = []
    for path in sorted(args.summary_dir.glob("summary_*.json")):
        summary = json.loads(path.read_text(encoding="utf-8"))
        run = path.stem.removeprefix("summary_")
        settings = summary["settings"]
        for budget, policies in summary["by_budget"].items():
            for policy, categories in policies.items():
                for category, values in categories.items():
                    rows.append({
                        "run": run,
                        "dataset": summary["dataset"],
                        "domain": summary.get("domain") or "",
                        "budget": budget,
                        "policy": policy,
                        "category": category,
                        "n": int(values["n"]),
                        **{bucket: values[bucket] for bucket in BUCKETS},
                        "top_k": settings["top_k"],
                        "tau": settings["tau"],
                        "chunk_size": settings.get("chunk_size", 1),
                        "questions_graded": summary["questions_graded"],
                        "questions_with_evidence": summary["questions_with_evidence"],
                    })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    runs = sorted({row["run"] for row in rows})
    print(f"wrote {args.out.relative_to(ROOT)}  {len(rows)} rows from {len(runs)} runs")
    for run in runs:
        print(f"  {run}: {sum(1 for r in rows if r['run'] == run)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
