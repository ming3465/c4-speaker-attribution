#!/usr/bin/env python3
"""Tables for C4 v2 (frozen probes): does compression destroy who-said-what?

Reads the per-row CSV from run_attribution_frozen.py. Everything needed is in
the CSV; nothing is rebuilt (v1's analysis rebuilt probes in a new process,
which the audit showed is hash-seed dependent).

Statistics:
  * cluster bootstrap by qid -- a question contributes several probes that
    share one retrieved context, so probes are not independent
  * paired dose-response vs budget 1.0 on the same probe_ids, with an exact
    McNemar test on the discordant pairs
  * swap arm: follow (answers the swapped-in B, i.e. binding) vs prior (answers
    the original author A, i.e. a content prior), and binding index =
    follow - prior per probe

    python scripts/evaluation/analyze_attribution_frozen.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.evaluation.attribution_gate import DEFAULT_MARGIN  # noqa: E402
from src.evaluation.attribution_stats import RESAMPLES, cluster_ci, mcnemar_exact, sensitivity  # noqa: E402
from src.evaluation.run_manifest import read_manifest  # noqa: E402

DEFAULT_CSV = (ROOT / "results" / "proposed" / "attribution_v2"
               / "attribution_frozen_uniform_compression_qwen2.5-7b.csv")
ROSTER_BUCKET = 5


def sidecar(csv_path: Path, kind: str) -> Path:
    """<stem>.manifest.json / <stem>.gate.json written by the runner."""
    return csv_path.with_name(f"{csv_path.stem}.{kind}.json")


def header_lines(csv_path: Path, rows: list[dict], probes: int, contexts: int) -> list[str]:
    if csv_path.resolve() == DEFAULT_CSV.resolve():  # pilot: keep the published header verbatim
        return [
            f"{probes} frozen probes from {contexts} questions; {len(rows)} graded rows. Reader `qwen2.5:7b`, "
            "temperature 0, via the ollama HTTP API. Policy `uniform_compression`, GroupMemBench Finance 10% pilot bundle.",
            "Each probe is fixed from budget-1.0 retrieval; only the text of the same messages is compressed at each budget.",
            "Roster = the speakers visible in the conversation (2–4), so chance = 1/|roster|. "
            f"Cluster bootstrap by question, {RESAMPLES} resamples.",
        ]
    first = rows[0] if rows else {}
    clusters = len({r["cluster"] for r in rows})
    return [
        f"{probes} frozen probes from {contexts} contexts in {clusters} clusters; {len(rows)} graded rows. "
        f"Dataset `{first.get('dataset', '?')}`, contexts `{first.get('contexts', '?')}`, "
        f"compressor `{first.get('compressor', '?')}`, scope `{first.get('scope', '?')}`.",
        "Each probe is fixed once; only the text of the same messages is compressed at each budget. "
        "Roster = the speakers visible in the context, so chance = 1/|roster|. "
        f"Cluster bootstrap by conversation/question, {RESAMPLES} resamples. Full configuration under Provenance.",
    ]


def provenance_lines(csv_path: Path) -> list[str]:
    manifest = read_manifest(sidecar(csv_path, "manifest"))
    gate = read_manifest(sidecar(csv_path, "gate"))
    if not manifest and not gate:
        return []
    lines = ["", "## Provenance", ""]
    with csv_path.open(encoding="utf-8") as handle:
        legacy = "cluster_id" not in next(csv.reader(handle), [])
    if legacy:
        lines.append("- **These rows predate run manifests** (legacy schema). The manifest below records the most "
                     "recent invocation against this CSV (a resume/verification), not the original generation.")
    if manifest:
        dirty = " (dirty tree)" if manifest.get("git_dirty") else ""
        lines += [
            f"- Status `{manifest.get('status')}`, rows {manifest.get('rows')}, "
            f"started {manifest.get('started_utc')}, finished {manifest.get('finished_utc')}",
            f"- Git `{manifest.get('git_commit')}`{dirty}; Python {manifest.get('python')}; "
            f"PYTHONHASHSEED={manifest.get('pythonhashseed')}",
            f"- Reader `{manifest.get('model')}` digest `{(manifest.get('model_digest') or '')[:12]}`",
        ]
        lines += [f"- Dataset `{d['path']}` sha256 `{d['sha256'][:12]}`" for d in manifest.get("dataset", [])]
        if manifest.get("summary_generated") or manifest.get("summary_clipped"):
            lines.append(f"- Summaries generated {manifest.get('summary_generated')}, "
                         f"clipped to budget {manifest.get('summary_clipped')}")
    if gate:
        verdict = "PASS" if gate.get("passed") else "FAIL"
        lines.append(f"- Headroom gate **{verdict}**: lift {gate['lift']*100:+.1f} pts "
                     f"[{gate['lift_lo']*100:+.1f}, {gate['lift_hi']*100:+.1f}] vs margin "
                     f"{gate['margin']*100:+.1f}; {gate['reason']}")
    return lines


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    p.add_argument("--out-dir", type=Path, default=ROOT / "results" / "comparisons" / "attribution_v2")
    p.add_argument("--margin", type=float, default=DEFAULT_MARGIN,
                   help="equivalence margin for Table 5; declare it before the run")
    p.add_argument("--score", choices=("model", "lexical"), default="model",
                   help="whose answers to score: the LLM reader, or the lexical attributor recorded on every row")
    return p.parse_args()


def as_lexical(rows: list[dict]) -> list[dict]:
    """The same rows with the lexical attributor's answer in place of the reader's."""
    return [{**r, "correct": r["lexical_correct"], "valid": True, "named": r["lexical_pick"]} for r in rows]


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for r in rows:
        r["budget"] = float(r["budget"])
        r["correct"] = r["correct"] == "True"
        r["valid"] = r["valid"] == "True"
        r["chance"] = float(r["chance"])
        r["freq_baseline"] = float(r["freq_baseline"])
        r["n_speakers"] = int(r["n_speakers"])
        r["target_words"] = int(r["target_words"])
        # independence unit: conversation for windows, question for retrieval;
        # the pilot CSV predates cluster_id, so fall back to qid
        r["cluster"] = r.get("cluster_id") or r["qid"]
        r["turn_baseline"] = float(r["turn_baseline"]) if r.get("turn_baseline") else None
        r["lexical_correct"] = r["lexical_correct"] == "True" if r.get("lexical_correct") else None
    return [r for r in rows if not r["error"]]


def pct(point: float, lo: float, hi: float, signed: bool = False) -> str:
    s = "+" if signed else ""
    return f"{point*100:{s}.1f}% [{lo*100:{s}.1f}, {hi*100:{s}.1f}]"


# --------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------

def has_turn_baseline(rows: list[dict]) -> bool:
    """Rows written before the turn-taking heuristic existed (the pilot) lack it."""
    return bool(rows) and all(r["turn_baseline"] is not None for r in rows)


def table_main(main: list[dict]) -> tuple[list[str], dict]:
    turn_col = has_turn_baseline(main)
    lex_col = bool(main) and all(r["lexical_correct"] is not None for r in main)
    lines = ["| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | "
             + ("Turn-taking heuristic | " if turn_col else "") + ("Lexical attributor | " if lex_col else "")
             + "Hit@1 − chance [95% CI] | Valid |",
             "| ---: | ---: | ---: | --- | ---: | ---: | " + ("---: | " if turn_col else "")
             + ("---: | " if lex_col else "") + "--- | ---: |"]
    out = {}
    for b in sorted({r["budget"] for r in main}, reverse=True):
        g = [r for r in main if r["budget"] == b]
        acc = cluster_ci([(r["cluster"], float(r["correct"])) for r in g])
        lift = cluster_ci([(r["cluster"], float(r["correct"]) - r["chance"]) for r in g])
        chance = sum(r["chance"] for r in g) / len(g)
        freq = sum(r["freq_baseline"] for r in g) / len(g)
        turn = sum(r["turn_baseline"] for r in g) / len(g) if turn_col else None
        lexical = sum(r["lexical_correct"] for r in g) / len(g) if lex_col else None
        words = sum(r["target_words"] for r in g) / len(g)
        valid = sum(r["valid"] for r in g) / len(g)
        lines.append(f"| {b} | {len(g)} | {words:.1f} | {pct(*acc)} | {chance*100:.1f}% | {freq*100:.1f}% "
                     + (f"| {turn*100:.1f}% " if turn_col else "")
                     + (f"| {lexical*100:.1f}% " if lex_col else "")
                     + f"| {pct(*lift, signed=True)} | {valid*100:.0f}% |")
        out[str(b)] = {"n": len(g), "acc": acc, "lift_over_chance": lift, "chance": chance,
                       "frequency_heuristic": freq, "turn_taking_heuristic": turn, "lexical_attributor": lexical,
                       "valid": valid, "target_words": words}
    return lines, out


def paired_by_budget(main: list[dict]) -> dict[float, list[tuple[dict, dict]]]:
    """(row at 1.0, row at b) for every probe present at both, per budget b, highest first."""
    by_probe: dict[str, dict[float, dict]] = defaultdict(dict)
    for r in main:
        by_probe[r["probe_id"]][r["budget"]] = r
    out = {}
    for b in sorted({r["budget"] for r in main if r["budget"] != 1.0}, reverse=True):
        pairs = [(v[1.0], v[b]) for v in by_probe.values() if 1.0 in v and b in v]
        if pairs:
            out[b] = pairs
    return out


def table_paired(main: list[dict]) -> tuple[list[str], dict]:
    lines = ["| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |",
             "| ---: | ---: | ---: | ---: | --- | ---: | ---: |"]
    out = {}
    for b, pairs in paired_by_budget(main).items():
        diff = cluster_ci([(top["cluster"], float(low["correct"]) - float(top["correct"])) for top, low in pairs])
        lost = sum(top["correct"] and not low["correct"] for top, low in pairs)
        gained = sum(low["correct"] and not top["correct"] for top, low in pairs)
        p = mcnemar_exact(lost, gained)
        a_top = sum(t["correct"] for t, _ in pairs) / len(pairs)
        a_low = sum(l["correct"] for _, l in pairs) / len(pairs)
        lines.append(f"| {b} | {len(pairs)} | {a_top*100:.1f}% | {a_low*100:.1f}% | {pct(*diff, signed=True)} "
                     f"| {lost} / {gained} | {p:.3g} |")
        out[str(b)] = {"n": len(pairs), "delta": diff, "lost": lost, "gained": gained, "mcnemar_p": p}
    return lines, out


def table_roster(main: list[dict]) -> list[str]:
    budgets = sorted({r["budget"] for r in main}, reverse=True)
    lines = ["| Speakers (roster) | Chance | " + " | ".join(f"b={b}" for b in budgets) + " |",
             "| ---: | ---: | " + " | ".join("---:" for _ in budgets) + " |"]
    bucket = lambda n: min(n, ROSTER_BUCKET)  # noqa: E731 - rosters of 5+ pooled
    for size in sorted({bucket(r["n_speakers"]) for r in main}):
        members = [r for r in main if bucket(r["n_speakers"]) == size]
        cells = []
        for b in budgets:
            g = [r for r in members if r["budget"] == b]
            cells.append(f"{sum(r['correct'] for r in g)/len(g)*100:.0f}% (n={len(g)})" if g else "—")
        label = f"{size}+" if size == ROSTER_BUCKET else str(size)
        chance = sum(r["chance"] for r in members) / len(members) * 100
        lines.append(f"| {label} | {chance:.0f}% | " + " | ".join(cells) + " |")
    return lines


def table_swap(swap: list[dict], main: list[dict]) -> tuple[list[str], dict]:
    main_by = {(r["probe_id"], r["budget"]): r for r in main}
    lines = ["| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |",
             "| ---: | ---: | --- | --- | --- | ---: | ---: |"]
    out = {}
    for b in sorted({r["budget"] for r in swap}, reverse=True):
        g = [r for r in swap if r["budget"] == b]
        follow = cluster_ci([(r["cluster"], float(r["named"] == r["gold"])) for r in g])
        prior = cluster_ci([(r["cluster"], float(r["named"] == r["original_author"])) for r in g])
        index = cluster_ci([(r["cluster"], float(r["named"] == r["gold"]) - float(r["named"] == r["original_author"]))
                            for r in g])
        chance = sum(r["chance"] for r in g) / len(g)
        base = [main_by[(r["probe_id"], b)]["correct"] for r in g if (r["probe_id"], b) in main_by]
        base_acc = sum(base) / len(base) if base else float("nan")
        lines.append(f"| {b} | {len(g)} | {pct(*follow)} | {pct(*prior)} | {pct(*index, signed=True)} "
                     f"| {chance*100:.1f}% | {base_acc*100:.1f}% |")
        out[str(b)] = {"n": len(g), "follow": follow, "prior": prior, "binding_index": index,
                       "chance": chance, "main_acc_same_probes": base_acc}
    return lines, out


def table_sensitivity(main: list[dict], margin: float) -> tuple[list[str], dict]:
    """What the headline numbers can and cannot rule out (same draws as Tables 1-2)."""
    checks = [("Hit@1 − chance at b=1.0",
               [(r["cluster"], float(r["correct"]) - r["chance"]) for r in main if r["budget"] == 1.0])]
    checks += [(f"Δ Hit@1, b={b} vs 1.0", [(t["cluster"], float(l["correct"]) - float(t["correct"])) for t, l in pairs])
               for b, pairs in paired_by_budget(main).items()]
    lines = [f"| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power "
             f"| Reading (margin ±{margin*100:.0f} pts) |",
             "| --- | ---: | --- | --- | ---: | --- |"]
    out = {}
    for label, items in checks:
        if not items:
            continue
        s = sensitivity(items, margin=margin)
        clusters = len({c for c, _ in items})
        lines.append(f"| {label} | {len(items)} ({clusters}) | {pct(s.point, s.lo95, s.hi95, signed=True)} "
                     f"| [{s.lo90*100:+.1f}, {s.hi90*100:+.1f}] | {s.mde*100:.1f} pts | {s.reading} |")
        out[label] = {**asdict(s), "clusters": clusters, "reading": s.reading}
    return lines, out


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    args = parse_args()
    if not args.csv.exists():
        print(f"missing {args.csv}", file=sys.stderr)
        return 1
    rows = load(args.csv)
    lexical = args.score == "lexical"
    if lexical:
        if not rows or any(r["lexical_correct"] is None for r in rows):
            print(f"{args.csv} has no lexical attributor column (rows older than it)", file=sys.stderr)
            return 2
        rows = as_lexical(rows)
    main_rows = [r for r in rows if r["condition"] == "main"]
    swap_rows = [r for r in rows if r["condition"] == "swap"]
    probes = len({r["probe_id"] for r in main_rows})
    questions = len({r["qid"] for r in main_rows})

    t1, s1 = table_main(main_rows)
    t2, s2 = table_paired(main_rows)
    t3 = table_roster(main_rows)
    t4, s4 = table_swap(swap_rows, main_rows)
    t5, s5 = table_sensitivity(main_rows, args.margin)
    doc = [
        "# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)",
        "",
        *header_lines(args.csv, rows, probes, questions),
        *(["", "**Scored: the lexical TF-IDF attributor recorded on each row, not the LLM reader.** It needs no "
                "model, so this is its own dose-response over the same frozen probes."] if lexical else []),
        "",
        "## Table 1 — attribution accuracy by budget",
        "",
        *t1,
        "",
        "*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change "
        "with the budget, so it is constant; it is the non-binding strategy to beat.",
        *(["",
           "*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before "
           "and after the statement. Also label-only and constant across budgets; on conversation windows it "
           "beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the "
           "speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same "
           "compressed text the reader sees; a non-LLM reference for the same dose-response."]
          if has_turn_baseline(main_rows) else []),
        "",
        "## Table 2 — paired dose-response (same probes, 1.0 vs b)",
        "",
        *t2,
        "",
        "Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.",
        "",
        "## Table 3 — accuracy by number of speakers in the conversation",
        "",
        *t3,
        "",
        "## Table 4 — label-swap counterfactual (binding vs prior)",
        "",
        "Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. "
        "Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. "
        "Following the swap = binding the statement to its author's other messages. Answering A = a content prior "
        "about A that survives the relabel. Binding index = follow − prior.",
        "",
        *t4,
        "",
        "## Table 5 — what the data can rule out",
        "",
        *t5,
        "",
        "*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided "
        "α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. "
        "*Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside "
        "±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The "
        "equivalence reading is valid only if the margin was fixed before the run.",
        *provenance_lines(args.csv),
    ]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    legacy = args.csv.resolve() == DEFAULT_CSV.resolve()
    stem = args.csv.stem + ("_lexical" if lexical else "")
    md = args.out_dir / ("attribution_v2_tables.md" if legacy and not lexical else f"{stem}_tables.md")
    md.write_text("\n".join(doc) + "\n", encoding="utf-8")
    js = args.out_dir / ("attribution_v2_summary.json" if legacy and not lexical else f"{stem}_summary.json")
    js.write_text(json.dumps({"probes": probes, "questions": questions, "main": s1,
                              "paired": s2, "swap": s4, "sensitivity": s5}, indent=2), encoding="utf-8")
    print("\n".join(doc))
    print(f"\nwrote {md}\nwrote {js}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
