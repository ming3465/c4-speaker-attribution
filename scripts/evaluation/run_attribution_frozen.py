#!/usr/bin/env python3
"""C4: does compressing a memory destroy who-said-what? (frozen probes)

Each probe is fixed once and re-rendered at every budget with only its text
compressed, so budgets are paired by probe_id. Design and history:
src/evaluation/attribution_frozen.py and docs/C4_RUNBOOK.md.

Order of operations: build probes -> run the uncompressed (budget 1.0) probes
-> headroom gate -> only if it passes, sweep the other budgets. A reader at
chance uncompressed can only produce a floor, not a dose-response.

    # GroupMemBench pilot (defaults reproduce the pilot exactly)
    PYTHONHASHSEED=0 python scripts/evaluation/run_attribution_frozen.py --controls
    PYTHONHASHSEED=0 python scripts/evaluation/run_attribution_frozen.py

    # any multi-party corpus in the utterance contract (AMI, ELITR, ...)
    PYTHONHASHSEED=0 python scripts/evaluation/run_attribution_frozen.py \
        --dataset utterances --utterances data/processed/ami.jsonl \
        --contexts window --window-size 10 --window-stride 5 --min-target-words 4

Rows are appended as they complete and the run resumes where it left off.
Exit codes: 0 ok, 1 invariant violations, 2 bad arguments / CSV schema
mismatch, 3 headroom gate failed.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.evaluation.attribution_compressors import (  # noqa: E402
    ALLOCATIONS,
    SummaryCompressor,
    WordDropCompressor,
)
from src.evaluation.attribution_frozen import (  # noqa: E402
    SCOPES,
    OllamaHTTPReader,
    StubReader,
    check_probe,
    frequency_baseline,
    grade,
    lexical_pick,
    probes_from_contexts,
    render_main,
    render_swap,
    retrieval_contexts,
    swap_partner,
    turn_taking_baseline,
    window_contexts,
)
from src.evaluation.attribution_gate import (  # noqa: E402
    DEFAULT_MARGIN,
    evaluate_gate,
    gate_record,
    write_gate,
)
from src.evaluation.failure_decomposition import corpus_idf  # noqa: E402
from src.evaluation.ollama_client import DEFAULT_BASE_URL, OllamaClient  # noqa: E402
from src.evaluation.run_manifest import build_manifest, utc_now, write_manifest  # noqa: E402

FIELDS = [
    "probe_id", "qid", "target_uid", "budget", "condition", "gold", "original_author",
    "partner", "roster", "n_speakers", "chance", "freq_baseline", "target_words",
    "model_answer", "named", "valid", "correct", "error", "latency_s",
    # appended after the pilot; absent from the pilot CSV (analysis falls back to qid)
    "cluster_id", "dataset", "contexts", "compressor", "scope",
    "turn_baseline", "lexical_pick", "lexical_correct",
]
PROGRESS_EVERY = 25
EXIT_INVARIANTS, EXIT_ARGS, EXIT_GATE = 1, 2, 3
# Deliberately pessimistic: English prose runs about 4 chars per token, so
# dividing by 3 over-counts and the warning fires before anything is truncated.
CHARS_PER_TOKEN = 3


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", choices=("groupmembench", "utterances"), default="groupmembench")
    p.add_argument("--bundle", type=Path, default=ROOT / "data" / "pilot" / "c4")
    p.add_argument("--corpus", default="corpus_10pct.jsonl")
    p.add_argument("--utterances", type=Path, help="Utterance-contract JSONL (--dataset utterances).")
    p.add_argument("--contexts", choices=("retrieval", "window"), default="retrieval")
    p.add_argument("--top-k", type=int, default=5, help="Retrieval context size.")
    p.add_argument("--window-size", type=int, default=10)
    p.add_argument("--window-stride", type=int, default=5)
    p.add_argument("--min-target-words", type=int, default=0,
                   help="Skip targets shorter than this (e.g. backchannels in meetings).")
    p.add_argument("--policy", default="uniform_compression")
    p.add_argument("--compressor", choices=("salient", "prefix", "summary"), default="salient")
    p.add_argument("--allocation", choices=ALLOCATIONS, default="pooled",
                   help="word-drop budget: pooled per conversation (pilot) or the same fraction of every message")
    p.add_argument("--summarizer-model", default="qwen2.5:7b")
    p.add_argument("--compress-scope", choices=SCOPES, default="both")
    p.add_argument("--budgets", type=float, nargs="+", default=[1.0, 0.75, 0.5, 0.25, 0.1])
    p.add_argument("--swap-budgets", type=float, nargs="*", default=[1.0, 0.25, 0.1],
                   help="Budgets at which to also run the label-swap counterfactual.")
    p.add_argument("--reader", choices=("ollama", "stub"), default="ollama")
    p.add_argument("--model", default="qwen2.5:7b")
    p.add_argument("--ollama-url", default=DEFAULT_BASE_URL, help="Point at a remote GPU box for larger models.")
    p.add_argument("--num-ctx", type=int, default=8192,
                   help="Reader context window. Ollama defaults to 4096 and truncates longer prompts "
                        "silently from the left, taking the instructions and roster with them. "
                        "--controls reports the longest prompt; raise this if it warns.")
    p.add_argument("--gate-margin", type=float, default=DEFAULT_MARGIN,
                   help="Required lower-CI lift over chance at budget 1.0. Declare before running.")
    p.add_argument("--skip-gate", action="store_true", help="Sweep even without headroom (explicit override).")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--limit", type=int, default=0, help="Cap the number of probes (0 = all).")
    p.add_argument("--controls", action="store_true", help="Print construction checks and exit.")
    p.add_argument("--out-dir", type=Path, default=ROOT / "results" / "proposed" / "attribution_v2")
    return p.parse_args()


def validate(args: argparse.Namespace) -> str | None:
    if args.dataset == "utterances" and (not args.utterances or not args.utterances.exists()):
        return "--dataset utterances needs --utterances pointing at an existing file"
    if args.contexts == "retrieval" and args.dataset != "groupmembench":
        return "--contexts retrieval needs questions; use --contexts window for utterance data"
    return None


def run_tag(args: argparse.Namespace) -> str:
    """Pilot defaults keep the legacy name, so the pilot CSV resumes in place."""
    model = "stub" if args.reader == "stub" else args.model
    parts = [f"{args.policy}_{model.replace(':', '-')}"]
    if args.dataset != "groupmembench":
        parts.append(args.utterances.stem)
    if args.contexts == "window":
        parts.append(f"win{args.window_size}s{args.window_stride}")
    if args.top_k != 5:
        parts.append(f"k{args.top_k}")
    if args.min_target_words:
        parts.append(f"min{args.min_target_words}")
    if args.compressor != "salient":
        parts.append(args.compressor if args.compressor != "summary"
                     else f"summary-{args.summarizer_model.replace(':', '-')}")
    if args.allocation != "pooled" and args.compressor != "summary":
        parts.append(args.allocation)
    if args.compress_scope != "both":
        parts.append(f"scope-{args.compress_scope}")
    return "_".join(parts)


def load_data(args):
    if args.dataset == "utterances":
        from src.datasets.utterances import load_utterances
        return load_utterances(args.utterances), [], [args.utterances]
    from src.datasets.memory_tasks import load_pilot_bundle
    units, questions = load_pilot_bundle(args.bundle, args.corpus)
    return units, questions, [args.bundle / args.corpus, args.bundle / "questions.jsonl"]


def build_probes(args, units, questions):
    if args.contexts == "retrieval":
        full = WordDropCompressor().compress(units, [1.0], questions=questions)[1.0]
        contexts = retrieval_contexts(questions, full, top_k=args.top_k)
    else:
        contexts = window_contexts(units, size=args.window_size, stride=args.window_stride)
    probes = probes_from_contexts(contexts, units, seed=args.seed, min_target_words=args.min_target_words)
    # Deterministic shuffle: an interrupted run then leaves a random, still
    # fully paired, subsample rather than a category- or meeting-biased prefix.
    random.Random(f"{args.seed}:probe-order").shuffle(probes)
    return probes[: args.limit] if args.limit else probes


def make_compressor(args, client: OllamaClient):
    if args.compressor == "summary":
        cache = ROOT / "results" / "cache" / f"summaries_{args.summarizer_model.replace(':', '-')}.jsonl"
        return SummaryCompressor(client, args.summarizer_model, cache)
    return WordDropCompressor(mode=args.compressor, policy=args.policy, allocation=args.allocation)


def plan(probes, stores, budgets, swap_budgets, scope, seed):
    """Gate jobs (budget 1.0, main arm) first; the rest probes-outer so any
    prefix of the sweep stays paired across budgets."""
    full = stores[1.0]
    gate, rest = [], []
    for probe in probes:
        partner = swap_partner(probe, seed=seed)
        for budget in budgets:
            main = render_main(probe, stores[budget], budget, full_store=full, scope=scope)
            (gate if budget == 1.0 else rest).append(main)
            if partner and budget in swap_budgets:
                rest.append(render_swap(probe, stores[budget], budget, partner, full_store=full, scope=scope))
    return gate, rest


def controls(jobs, num_ctx: int = 0) -> int:
    violations = [(j.probe.probe_id, j.budget, j.condition, v) for j in jobs for v in check_probe(j)]
    by_cell: dict = {}
    for j in jobs:
        by_cell.setdefault((j.condition, j.budget), []).append(j)
    print(f"{'arm':<6}{'budget':>7}{'probes':>8}{'chance':>9}{'freq':>8}{'turn':>8}{'target words':>14}")
    for (cond, budget), group in sorted(by_cell.items(), key=lambda kv: (kv[0][0], -kv[0][1])):
        chance = sum(1 / len(j.probe.roster) for j in group) / len(group)
        freq = sum(frequency_baseline(j) for j in group) / len(group)
        turn = sum(turn_taking_baseline(j) for j in group) / len(group)
        words = sum(len(j.target_text.split()) for j in group) / len(group)
        print(f"{cond:<6}{budget:>7}{len(group):>8}{chance:>9.3f}{freq:>8.3f}{turn:>8.3f}{words:>14.1f}")
    longest = max(len(j.prompt()) for j in jobs)
    estimate = longest // CHARS_PER_TOKEN
    print(f"\nlongest prompt: {longest} chars, at most ~{estimate} tokens")
    if num_ctx and estimate > num_ctx:
        print(f"  WARNING: that is over --num-ctx {num_ctx}. Ollama truncates from the left, "
              f"dropping the instructions and the roster. Raise --num-ctx.")
    print(f"invariant violations: {len(violations)}")
    for v in violations[:10]:
        print("  ", v)
    return EXIT_INVARIANTS if violations else 0


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def header_of(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as handle:
        return next(csv.reader(handle), [])


def row_for(job, answer: str, error: str, latency: float, extra: dict, idf: dict[str, float]) -> dict:
    correct, valid, named = grade(job, answer) if not error else (False, False, "")
    probe = job.probe
    lexical = lexical_pick(job, idf)
    return {
        "probe_id": probe.probe_id, "qid": probe.qid, "target_uid": probe.target_uid,
        "budget": job.budget, "condition": job.condition, "gold": job.gold,
        "original_author": probe.gold_author,
        "partner": job.gold if job.condition == "swap" else "",
        "roster": "|".join(probe.roster), "n_speakers": len(probe.roster),
        "chance": round(1 / len(probe.roster), 4),
        "freq_baseline": round(frequency_baseline(job), 4),
        "turn_baseline": round(turn_taking_baseline(job), 4),
        "lexical_pick": lexical, "lexical_correct": lexical == job.gold,
        "target_words": len(job.target_text.split()),
        "model_answer": answer, "named": named, "valid": valid, "correct": correct,
        "error": error, "latency_s": round(latency, 2),
        "cluster_id": probe.cluster_id or probe.qid, **extra,
    }


def run(jobs, reader, out_path: Path, extra: dict, label: str, idf: dict[str, float]) -> int:
    finished = {(r["probe_id"], r["budget"], r["condition"]) for r in read_rows(out_path)}
    todo = [j for j in jobs if (j.probe.probe_id, str(j.budget), j.condition) not in finished]
    print(f"[{label}] {len(jobs)} jobs, {len(jobs) - len(todo)} already done, {len(todo)} to run -> {out_path}")
    if not todo:
        return 0
    if out_path.exists() and header_of(out_path) != FIELDS:
        print(f"CSV schema differs from this runner's ({out_path}); write to a new --out-dir.", file=sys.stderr)
        return EXIT_ARGS
    new_file = not out_path.exists()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    correct = 0
    with out_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for position, job in enumerate(todo, start=1):
            start = time.monotonic()
            try:
                answer, error = reader.answer(job.prompt(), choices=job.probe.roster), ""
            except Exception as exc:  # noqa: BLE001 - recorded per row, never silent
                answer, error = "", f"{type(exc).__name__}: {exc}"
            row = row_for(job, answer, error, time.monotonic() - start, extra, idf)
            writer.writerow(row)
            handle.flush()
            correct += row["correct"]
            if position % PROGRESS_EVERY == 0 or position == len(todo):
                print(f"[{label}] progress {position}/{len(todo)} | running acc {correct / position:.3f}", flush=True)
    return 0


def gate_rows(out_path: Path) -> list[dict]:
    return [{**r, "correct": r["correct"] == "True", "cluster_id": r.get("cluster_id") or r["qid"]}
            for r in read_rows(out_path) if r["condition"] == "main" and float(r["budget"]) == 1.0]


def main() -> int:
    args = parse_args()
    problem = validate(args)
    if problem:
        print(problem, file=sys.stderr)
        return EXIT_ARGS
    started = utc_now()
    budgets = sorted(set(args.budgets) | {1.0}, reverse=True)
    units, questions, dataset_files = load_data(args)
    idf = corpus_idf(units)     # for the lexical attributor column
    probes = build_probes(args, units, questions)
    client = OllamaClient(args.ollama_url)
    compressor = make_compressor(args, client)
    needed = {uid for p in probes for uid in p.context_uids}
    stores = compressor.compress(units, budgets, questions=questions, only_uids=needed)
    gate_jobs, sweep_jobs = plan(probes, stores, budgets, set(args.swap_budgets), args.compress_scope, args.seed)
    print(f"{len(probes)} frozen probes from {len({p.qid for p in probes})} contexts, "
          f"{len({p.cluster_id for p in probes})} clusters")

    code = controls(gate_jobs + sweep_jobs, args.num_ctx)
    if args.controls or code:
        return code

    tag = run_tag(args)
    out = args.out_dir / f"attribution_frozen_{tag}.csv"
    reader = (StubReader() if args.reader == "stub"
              else OllamaHTTPReader(args.model, args.ollama_url, num_ctx=args.num_ctx))
    digest = ""
    if args.reader == "ollama":
        try:
            digest = client.model_digest(args.model)
        except OSError:
            digest = ""
    manifest = build_manifest(root=ROOT, args=vars(args), dataset_files=dataset_files,
                              model=reader.model, model_digest=digest, started_utc=started)
    manifest_path = args.out_dir / f"attribution_frozen_{tag}.manifest.json"
    write_manifest(manifest_path, {**manifest, "status": "running"})
    extra = {"dataset": args.dataset, "contexts": args.contexts,
             "compressor": args.compressor, "scope": args.compress_scope}

    code = run(gate_jobs, reader, out, extra, "gate", idf)
    if code:
        return code
    result = evaluate_gate(gate_rows(out), margin=args.gate_margin)
    write_gate(args.out_dir / f"attribution_frozen_{tag}.gate.json", result)
    print(f"[gate] {'PASS' if result.passed else 'FAIL'}: acc {result.accuracy:.3f}, chance {result.chance:.3f}, "
          f"frequency {result.frequency:.3f}, turn-taking {result.turn_taking:.3f}, "
          f"lift {result.lift:+.3f} [{result.lift_lo:+.3f}, {result.lift_hi:+.3f}] vs margin {result.margin:+.3f}, "
          f"lead over best heuristic {result.over_heuristic:+.3f} (lower {result.over_heuristic_lo:+.3f}) "
          f"-- {result.reason}")

    if not result.passed and not args.skip_gate:
        print("[gate] no headroom: the sweep would measure a floor. Stopping (use --skip-gate to override).",
              file=sys.stderr)
        status, code = "stopped_at_gate", EXIT_GATE
    else:
        code = run(sweep_jobs, reader, out, extra, "sweep", idf)
        status = "complete" if code == 0 else "failed"
    write_manifest(manifest_path, {
        **manifest, "status": status, "finished_utc": utc_now(), "rows": len(read_rows(out)),
        "gate": gate_record(result),
        "summary_generated": getattr(compressor, "generated", 0),
        "summary_clipped": getattr(compressor, "clipped", 0),
    })
    return code


if __name__ == "__main__":
    raise SystemExit(main())
