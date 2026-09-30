#!/usr/bin/env python3
"""Pilot tables for C4: compression-induced attribution failure.

STATUS: SUPERSEDED by the C4 v2 frozen-probe design (src/evaluation/attribution_frozen.py); kept only to reproduce the v1 pilot. See docs/C4_RUNBOOK.md, 'Code status'.

Reads the per-probe CSVs written by run_attribution_probe.py and produces the
tables that can actually be reported. The runner prints raw accuracy only;
this adds what a pilot needs to be read honestly:

  * bootstrap 95% CIs on every accuracy
  * the bindable split -- probes where the true author also appears, labelled,
    elsewhere in context. Only those are solvable by binding, and their share
    falls as the budget tightens, so the all-probe curve confounds binding
    loss with sample composition.
  * a context-presence baseline -- the expected accuracy of "pick uniformly
    among candidates who appear in the conversation". The reader was observed
    using exactly this heuristic, so beating 1/6 is not enough.
  * the counterfactual split -- does the reader follow the relabelled context
    (binding) or stick with the original author (content prior)?

    python scripts/evaluation/analyze_attribution.py
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.memory_tasks import load_pilot_bundle  # noqa: E402
from src.evaluation.attribution_probe import UNKNOWN, build_attribution_items  # noqa: E402

BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20260923
RANDOM_FLOOR = 1 / 6
MIN_CELL_N = 10  # below this a cell is printed but flagged as unreliable


# --------------------------------------------------------------------------
# io
# --------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results-dir", type=Path, default=ROOT / "results" / "proposed" / "attribution")
    p.add_argument("--tag", default="uniform_compression_qwen2.5-7b_ollama")
    p.add_argument("--policy", default="uniform_compression")
    p.add_argument("--bundle", type=Path, default=ROOT / "data" / "pilot" / "c4")
    p.add_argument("--corpus", default="corpus_10pct.jsonl")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out-dir", type=Path, default=ROOT / "results" / "comparisons" / "attribution")
    return p.parse_args()


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["budget"] = float(row["budget"])
        row["n_speakers"] = int(row["n_speakers"])
        row["correct"] = row["correct"] == "True"
        row["gold_in_context"] = row["gold_in_context"] == "True"
        row["candidate_list"] = row["candidates"].split("|") if row.get("candidates") else []
        row["answer"] = row["model_answer"].strip()
    return rows


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------

def bootstrap_ci(values: list[bool]) -> tuple[float, float, float]:
    """Mean and percentile 95% CI. Stdlib only -- no numpy in this env."""
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(values)
    means = sorted(
        sum(values[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    lo = means[int(0.025 * BOOTSTRAP_RESAMPLES)]
    hi = means[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]
    return sum(values) / n, lo, hi


def bootstrap_diff(a: list[bool], b: list[bool]) -> tuple[float, float, float]:
    """mean(a) - mean(b) with a 95% CI from independent resampling."""
    if not a or not b:
        return 0.0, 0.0, 0.0
    rng = random.Random(BOOTSTRAP_SEED + 1)
    diffs = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        ra = sum(a[rng.randrange(len(a))] for _ in a) / len(a)
        rb = sum(b[rng.randrange(len(b))] for _ in b) / len(b)
        diffs.append(ra - rb)
    diffs.sort()
    point = sum(a) / len(a) - sum(b) / len(b)
    return point, diffs[int(0.025 * BOOTSTRAP_RESAMPLES)], diffs[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]


def fmt(mean: float, lo: float, hi: float) -> str:
    return f"{mean*100:5.1f}% [{lo*100:4.1f}, {hi*100:4.1f}]"


# --------------------------------------------------------------------------
# baselines needing the rebuilt probes
# --------------------------------------------------------------------------

def presence_baseline(args, budgets: list[float]) -> dict[tuple[str, float], float]:
    """Expected accuracy of 'pick uniformly among candidates visible in context'.

    Rebuilt deterministically from the same seed as the run, then joined on
    (qid, budget). If no candidate is visible the heuristic guesses uniformly.
    """
    units, questions = load_pilot_bundle(args.bundle, args.corpus)
    expected: dict[tuple[str, float], float] = {}
    for budget in budgets:
        for item in build_attribution_items(
            units, questions, policy=args.policy, budget=budget, seed=args.seed
        ):
            visible = {s.get("speaker") for s in item.snippets if s.get("speaker") not in ("", UNKNOWN)}
            present = [c for c in item.candidates if c in visible]
            pool = present or item.candidates
            expected[(item.qid, budget)] = (1 / len(pool)) if item.gold_author in pool else 0.0
    return expected


# --------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------

def by(rows: list[dict], key) -> dict:
    groups: dict = defaultdict(list)
    for row in rows:
        groups[key(row)].append(row)
    return groups


def table_overall(rows, presence) -> tuple[list[str], dict]:
    lines = [
        "| Budget | n | Hit@1 [95% CI] | Valid answers | Presence baseline | Random |",
        "| ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    out = {}
    for budget, group in sorted(by(rows, lambda r: r["budget"]).items(), reverse=True):
        acc = bootstrap_ci([r["correct"] for r in group])
        valid = sum(r["answer"] in r["candidate_list"] for r in group) / len(group)
        pres = sum(presence.get((r["qid"], budget), 0.0) for r in group) / len(group)
        lines.append(f"| {budget} | {len(group)} | {fmt(*acc)} | {valid*100:.0f}% | {pres*100:.1f}% | {RANDOM_FLOOR*100:.1f}% |")
        out[budget] = {"n": len(group), "acc": acc, "valid": valid, "presence": pres}
    return lines, out


def table_bindable(rows) -> tuple[list[str], dict]:
    lines = [
        "| Budget | Bindable n | Bindable Hit@1 [95% CI] | Non-bindable n | Non-bindable Hit@1 [95% CI] |",
        "| ---: | ---: | --- | ---: | --- |",
    ]
    out = {}
    for budget, group in sorted(by(rows, lambda r: r["budget"]).items(), reverse=True):
        yes = [r["correct"] for r in group if r["gold_in_context"]]
        no = [r["correct"] for r in group if not r["gold_in_context"]]
        lines.append(f"| {budget} | {len(yes)} | {fmt(*bootstrap_ci(yes))} | {len(no)} | {fmt(*bootstrap_ci(no))} |")
        out[budget] = {"bindable": bootstrap_ci(yes), "n_bindable": len(yes),
                       "non_bindable": bootstrap_ci(no), "n_non_bindable": len(no)}
    return lines, out


def table_speakers(rows) -> list[str]:
    bindable = [r for r in rows if r["gold_in_context"]]
    budgets = sorted({r["budget"] for r in bindable}, reverse=True)
    lines = [
        "| Speakers in set | " + " | ".join(str(b) for b in budgets) + " |",
        "| ---: | " + " | ".join("---:" for _ in budgets) + " |",
    ]
    for count, group in sorted(by(bindable, lambda r: r["n_speakers"]).items()):
        cells = []
        for budget in budgets:
            vals = [r["correct"] for r in group if r["budget"] == budget]
            if not vals:
                cells.append("—")
                continue
            flag = "" if len(vals) >= MIN_CELL_N else "†"
            cells.append(f"{sum(vals)/len(vals)*100:.0f}% (n={len(vals)}){flag}")
        lines.append(f"| {count} | " + " | ".join(cells) + " |")
    return lines


def table_counterfactual(cf_rows, main_rows) -> tuple[list[str], dict]:
    original = {(r["qid"], r["budget"]): r["gold_author"] for r in main_rows}
    lines = [
        "| Budget | n | Follows relabel (binding) | Sticks with original (prior) | Other |",
        "| ---: | ---: | --- | --- | ---: |",
    ]
    out = {}
    for budget, group in sorted(by(cf_rows, lambda r: r["budget"]).items(), reverse=True):
        follow = [r["answer"] == r["gold_author"] for r in group]
        prior = [r["answer"] == original.get((r["qid"], budget)) for r in group]
        other = 1 - (sum(follow) + sum(prior)) / len(group)
        lines.append(f"| {budget} | {len(group)} | {fmt(*bootstrap_ci(follow))} | {fmt(*bootstrap_ci(prior))} | {other*100:.0f}% |")
        out[budget] = {"n": len(group), "follow": bootstrap_ci(follow), "prior": bootstrap_ci(prior)}
    return lines, out


def dose_response(rows, subset_label: str, keep) -> str:
    top = [r["correct"] for r in rows if r["budget"] == 1.0 and keep(r)]
    low = [r["correct"] for r in rows if r["budget"] == 0.1 and keep(r)]
    if not top or not low:
        # An empty side must not render as a measured zero effect.
        return f"- **{subset_label}**: n/a — needs both budget 1.0 (n={len(top)}) and 0.1 (n={len(low)})"
    point, lo, hi = bootstrap_diff(top, low)
    verdict = "CI excludes 0" if lo > 0 or hi < 0 else "CI includes 0 — not distinguishable from no effect"
    return f"- **{subset_label}**: Hit@1(1.0) − Hit@1(0.1) = {point*100:+.1f} pts [95% CI {lo*100:+.1f}, {hi*100:+.1f}] → {verdict}"


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    args = parse_args()
    main_rows = load_rows(args.results_dir / f"attribution_{args.tag}.csv")
    cf_rows = load_rows(args.results_dir / f"attribution_{args.tag}_counterfactual.csv")
    if not main_rows:
        print(f"no main-arm results for tag {args.tag}", file=sys.stderr)
        return 1

    budgets = sorted({r["budget"] for r in main_rows}, reverse=True)
    presence = presence_baseline(args, budgets)

    t1, s1 = table_overall(main_rows, presence)
    t2, s2 = table_bindable(main_rows)
    t3 = table_speakers(main_rows)
    doc = [
        "# C4 Pilot — Compression-Induced Attribution Failure",
        "",
        f"Reader `qwen2.5:7b` (local, ollama). Policy `{args.policy}`. GroupMemBench Finance, 10% pilot bundle.",
        "Forced-choice attribution over 6 candidates (true author + 5 corpus distractors) → random floor 16.7%.",
        f"Bootstrap 95% CIs, {BOOTSTRAP_RESAMPLES} resamples.",
        "",
        "## Table 1 — attribution accuracy vs compression budget (all probes)",
        "",
        *t1,
        "",
        "*Presence baseline* = expected accuracy of picking uniformly among candidates visible in the",
        "conversation. The reader was observed using this heuristic, so it is the bar to clear, not 16.7%.",
        "",
        "## Table 2 — bindable vs non-bindable probes",
        "",
        "Bindable = the true author also appears, labelled, elsewhere in the retrieved set. Only these can be",
        "solved by binding. Their share falls as the budget tightens, so Table 1 confounds binding loss with",
        "sample composition; this table removes that confound.",
        "",
        *t2,
        "",
        "## Dose-response (uncompressed vs 10% budget)",
        "",
        dose_response(main_rows, "All probes", lambda r: True),
        dose_response(main_rows, "Bindable only", lambda r: r["gold_in_context"]),
        "",
        "## Table 3 — bindable accuracy by speaker count × budget",
        "",
        f"† = n < {MIN_CELL_N}; directional only.",
        "",
        *t3,
    ]
    summary = {"overall": {str(k): v for k, v in s1.items()},
               "bindable": {str(k): v for k, v in s2.items()}}

    if cf_rows:
        t4, s4 = table_counterfactual(cf_rows, main_rows)
        doc += [
            "",
            "## Table 4 — counterfactual: relabel the true author's other snippets",
            "",
            "Evidence text byte-identical to the main probe; only the speaker labels on the true author's",
            "*other* snippets move from A to B, and the gold becomes B. Following the relabel = binding to",
            "context. Sticking with A = a content prior about A.",
            "",
            *t4,
        ]
        summary["counterfactual"] = {str(k): v for k, v in s4.items()}

    args.out_dir.mkdir(parents=True, exist_ok=True)
    md_path = args.out_dir / "attribution_pilot_tables.md"
    md_path.write_text("\n".join(doc) + "\n", encoding="utf-8")
    json_path = args.out_dir / "attribution_pilot_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n".join(doc))
    print(f"\nwrote {md_path}\nwrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
