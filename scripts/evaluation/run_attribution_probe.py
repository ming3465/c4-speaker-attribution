#!/usr/bin/env python3
"""Does compression destroy who-said-what? (Contribution 4, re-scoped)

STATUS: SUPERSEDED by the C4 v2 frozen-probe design (src/evaluation/attribution_frozen.py); kept only to reproduce the v1 pilot. See docs/C4_RUNBOOK.md, 'Code status'.

WhenLoss (arXiv 2605.24579) owns write-vs-retrieval decomposition, but its
benchmarks are single- or two-party so it cannot ask this. When several
people's compressed statements are retrieved together, can the reader still
recover the source?

    python scripts/evaluation/run_attribution_probe.py --backend stub --limit 20
    python scripts/evaluation/run_attribution_probe.py --backend ollama \
        --model qwen2.5:7b --controls --limit 100
    python scripts/evaluation/run_attribution_probe.py --backend ollama \
        --model qwen2.5:7b --budgets 1.0 0.75 0.5 0.25 0.1

Budget 1.0 is the sanity control. If uncompressed attribution is not near the
ceiling, the probe is malformed and nothing else in the output means anything.
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
from src.evaluation.reader_pass import OllamaReader, StubReader  # noqa: E402
from src.evaluation.attribution_probe import (  # noqa: E402
    UNKNOWN,
    build_attribution_items,
    build_counterfactual,
    elimination_solvable_rate,
    grade,
    majority_baseline,
    name_in_text_rate,
    random_floor,
    shuffle_labels,
    summarize,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, default=ROOT / "data" / "pilot" / "c4")
    p.add_argument("--corpus", default="corpus_10pct.jsonl")
    p.add_argument("--policy", default="uniform_compression", choices=list(POLICIES))
    p.add_argument("--budgets", type=float, nargs="+", default=[1.0, 0.75, 0.5, 0.25, 0.1])
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--tau", type=float, default=0.65)
    p.add_argument("--backend", choices=("stub", "ollama"), default="ollama")
    p.add_argument("--model", default="qwen2.5:7b")
    p.add_argument("--timeout-seconds", type=int, default=180)
    p.add_argument("--limit", type=int, default=0, help="Cap probes per budget.")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--controls", action="store_true", help="Run leakage controls and stop.")
    p.add_argument("--counterfactual", action="store_true", help="Run the counterfactual arm.")
    p.add_argument("--out-dir", type=Path, default=ROOT / "results" / "proposed" / "attribution")
    return p.parse_args()


class StubAttributionReader:
    """Offline plumbing check: always answers the first candidate.

    Scores near the random floor by construction. It verifies the prompt,
    grading and table code run end to end -- it is not a result.
    """

    name = "stub"

    def answer(self, item) -> str:
        return item.candidates[0] if item.candidates else UNKNOWN


def run(items, backend, *, progress_label: str) -> list[dict]:
    rows = []
    total = len(items)
    for position, item in enumerate(items, start=1):
        try:
            raw = backend.answer(item)
            error = ""
        except Exception as exc:  # noqa: BLE001 - recorded per row, never silent
            raw, error = "", f"{type(exc).__name__}: {exc}"
        correct = grade(item, raw) if not error else False
        rows.append({
            "qid": item.qid, "budget": item.budget, "condition": item.condition,
            "n_speakers": item.n_speakers, "n_candidates": len(item.candidates),
            "gold_in_context": item.gold_in_context,
            "candidates": "|".join(item.candidates),
            "gold_author": item.gold_author, "model_answer": raw,
            "correct": correct, "error": error,
        })
        print(f"  {progress_label} {position}/{total}", end="\r", flush=True)
    print()
    return rows


class PromptAdapter:
    """Bridges AttributionItem to the reader_pass backends, which expect .prompt()."""

    def __init__(self, backend):
        self.backend = backend
        self.name = getattr(backend, "name", "backend")

    def answer(self, item):
        class _Shim:
            def __init__(self, text): self._t = text
            def prompt(self): return self._t
        return self.backend.answer(_Shim(item.prompt()))


def main() -> int:
    args = parse_args()
    units, questions = load_pilot_bundle(args.bundle, args.corpus)

    # ---- controls: cheap, deterministic, no model calls ----
    if args.controls:
        print(f"leakage controls | policy={args.policy}\n")
        print(f"{'budget':>7}{'probes':>8}{'random':>9}{'majority':>10}{'name-txt':>10}{'elimin.':>9}{'leaks':>7}")
        print("-" * 60)
        for budget in args.budgets:
            items = build_attribution_items(
                units, questions, policy=args.policy, budget=budget,
                top_k=args.top_k, tau=args.tau, seed=args.seed)
            leaks = sum(not i.verify_no_leak() for i in items)
            print(f"{budget:>7}{len(items):>8}{random_floor(items):>9.3f}"
                  f"{majority_baseline(items):>10.3f}{name_in_text_rate(items):>10.3f}"
                  f"{elimination_solvable_rate(items):>9.3f}{leaks:>7}")
        print("\nAll four must hold before the headline table means anything:")
        print("  leaks = 0, name-in-text low, eliminable ~ 0, model > majority")
        print("\nNote: majority is the baseline to beat, not random -- the gold-author")
        print("distribution is skewed and majority rises as the budget tightens.")
        return 0

    if args.backend == "ollama":
        if not shutil.which("ollama"):
            print("ollama not on PATH", file=sys.stderr)
            return 2
        backend = PromptAdapter(OllamaReader(model=args.model, timeout_seconds=args.timeout_seconds))
        reader_name = f"ollama/{args.model}"
    else:
        backend = StubAttributionReader()
        reader_name = "stub"

    print(f"policy={args.policy} reader={reader_name}")
    all_rows: list[dict] = []
    per_budget: dict[float, dict] = {}

    for budget in args.budgets:
        items = build_attribution_items(
            units, questions, policy=args.policy, budget=budget,
            top_k=args.top_k, tau=args.tau, seed=args.seed)
        if args.counterfactual:
            # Counterfactuals exist only for bindable probes (the true author
            # must appear elsewhere for there to be a label to move).
            items = [
                cf for cf in (build_counterfactual(i, seed=args.seed) for i in items)
                if cf is not None
            ]
        if args.limit:
            items = items[: args.limit]
        if not items:
            continue

        print(f"\n-- budget {budget}: {len(items)} probes "
              f"(random floor {random_floor(items):.3f})")
        rows = run(items, backend, progress_label=f"b={budget}")
        all_rows.extend(rows)
        summary = summarize(rows)
        summary["random_floor"] = round(random_floor(items), 4)
        summary["majority"] = round(majority_baseline(items), 4)
        per_budget[budget] = summary
        print(f"   accuracy {summary['accuracy']*100:.1f}%  "
              f"(floor {summary['random_floor']*100:.1f}%)")

    if not per_budget:
        print("no probes built")
        return 1

    # ---- Table 1 ----
    print("\n" + "=" * 62)
    print("TABLE 1  attribution accuracy vs compression budget")
    print(f"{'budget':>7}{'Hit@1':>9}{'random':>9}{'majority':>10}{'n':>6}")
    print("-" * 62)
    for budget in sorted(per_budget, reverse=True):
        s = per_budget[budget]
        print(f"{budget:>7}{s['accuracy']*100:>8.1f}%{s['random_floor']*100:>8.1f}%"
              f"{s['majority']*100:>9.1f}%{s['n']:>6}")

    # ---- Table 2 ----
    counts = sorted({r["n_speakers"] for r in all_rows})
    budgets_desc = sorted(per_budget, reverse=True)
    print("\nTABLE 2  accuracy by speaker count x budget  (the headline)")
    header = f"{'speakers':>9}" + "".join(f"{b:>9}" for b in budgets_desc) + f"{'drop':>9}"
    print(header)
    print("-" * len(header))
    for count in counts:
        cells, first, last = [], None, None
        for budget in budgets_desc:
            sub = [r["correct"] for r in all_rows if r["n_speakers"] == count and r["budget"] == budget]
            if sub:
                acc = sum(sub) / len(sub)
                cells.append(f"{acc*100:>8.1f}%")
                if first is None:
                    first = acc
                last = acc
            else:
                cells.append(f"{'-':>9}")
        drop = f"{(first-last)*100:>+8.1f}" if first is not None and last is not None else f"{'-':>9}"
        print(f"{count:>9}" + "".join(cells) + drop)
    print("\nClaim lives in the last column: the drop should steepen as speaker count rises.")

    if args.backend == "stub":
        print("\nreminder: stub backend -- plumbing only, not a result.")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{args.policy}_{args.model.replace(':','-')}_{args.backend}" + \
          ("_counterfactual" if args.counterfactual else "")
    csv_path = args.out_dir / f"attribution_{tag}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(all_rows[0]))
        w.writeheader(); w.writerows(all_rows)
    json_path = args.out_dir / f"summary_{tag}.json"
    json_path.write_text(json.dumps(
        {"policy": args.policy, "reader": reader_name,
         "counterfactual": args.counterfactual,
         "by_budget": {str(k): v for k, v in per_budget.items()}}, indent=2), encoding="utf-8")
    print(f"\nwrote {csv_path}\nwrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
