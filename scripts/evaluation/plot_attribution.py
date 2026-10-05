#!/usr/bin/env python3
"""Paper-quality figures for the C4 attribution study.

Reads the `*_summary.json` files `analyze_attribution_frozen.py` already
writes, so a figure can never disagree with its table: every point, interval
and baseline here comes from the same numbers the tables were rendered from.
Nothing is retyped.

    uv run --group figures python scripts/evaluation/plot_attribution.py

Two figures, because the study makes two claims:

  dose_response   Hit@1 against compression budget on AMI, one line per run,
                  with chance and the frequency shortcut as reference lines.
                  Those two are label-only and compressor-independent, so they
                  are the honest things to draw across runs. The crossing below
                  the shortcut is the point: it is where the reader stops doing
                  the task. The lexical control is deliberately NOT drawn here
                  -- it is computed on the compressed text, so each compressor
                  has its own curve and overlaying one on another run's line
                  would be a comparison of two different things. It is in the
                  tables.
  cross_corpus    The paired change from budget 1.0, one line per corpus and
                  reader. The claim is about how much is LOST, so the loss is
                  what is plotted; accuracy levels would mix "how good the
                  reader is" into a figure about "how much it drops". Each
                  legend entry carries that corpus's mean words per turn, so
                  the explanatory variable is on the figure rather than left
                  to the caption.

Only runs whose CSV exists locally can appear. The AMI qwen2.5:14b word-drop
sweep -- the original main result -- was produced on a laptop and its CSV is
gitignored, so it is absent here and its numbers live in docs/C4_MAIN_STUDY.md.

matplotlib is a `figures` dependency group, not a runtime dependency: the
instrument itself still runs on the standard library alone.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = ROOT / "results" / "comparisons" / "attribution_v2"
DEFAULT_OUT = ROOT / "results" / "figures"

# attribution_frozen_uniform_compression_<model>_<corpus>_win…_summary.json
NAME = re.compile(r"uniform_compression_(?P<model>[^_]+)_(?P<corpus>[^_]+)_win")
CORPUS = {"ami": "AMI", "icsi": "ICSI", "elitr": "ELITR", "supreme": "Supreme Court"}
BUDGETS = ("1.0", "0.5", "0.25", "0.1")


def label_of(path: Path) -> tuple[str, str, str]:
    """(model, corpus, compressor) from the file name; the analyzer encodes all three."""
    match = NAME.search(path.name)
    if not match:
        raise ValueError(f"{path.name}: not an analyzer summary file name")
    model = match.group("model").replace("-", ":")
    corpus = CORPUS.get(match.group("corpus"), match.group("corpus"))
    compressor = "summary" if "summary-" in path.name else "word-drop"
    return model, corpus, compressor


def load(paths: list[Path]) -> list[dict]:
    runs = []
    for path in sorted(paths):
        model, corpus, compressor = label_of(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data.get("main"):
            continue                      # gate-only run: no sweep to plot
        runs.append({"model": model, "corpus": corpus, "compressor": compressor,
                     "stem": path.name, **data})
    return runs


def series(run: dict, key: str) -> tuple[list[float], list[float], list[float], list[float]]:
    """x positions, point, lower and upper error magnitudes, for budgets present."""
    xs, point, lo, hi = [], [], [], []
    for i, budget in enumerate(BUDGETS):
        cell = run["main"].get(budget)
        if not cell:
            continue
        value = cell[key]
        mid, low, high = (value if isinstance(value, list) else (value, value, value))
        xs.append(i)
        point.append(mid * 100)
        lo.append((mid - low) * 100)
        hi.append((high - mid) * 100)
    return xs, point, lo, hi


def dose_response(runs: list[dict], out: Path) -> Path | None:
    import matplotlib.pyplot as plt

    ami = [r for r in runs if r["corpus"] == "AMI"]
    if not ami:
        return None
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    reference = ami[0]["main"]["1.0"]
    for value, style, name in ((reference["chance"], ":", "chance"),
                               (reference["frequency_heuristic"], "--", "frequency shortcut")):
        ax.axhline(value * 100, color="0.45", ls=style, lw=1)
        ax.text(0.02, value * 100 + 0.4, f"{name} {value * 100:.1f}%", color="0.35", fontsize=8)

    for run, colour in zip(ami, ("#1f4e9c", "#5b8dd9", "#9bb7e0")):
        xs, point, lo, hi = series(run, "acc")
        ax.errorbar(xs, point, yerr=[lo, hi], marker="o", ms=4, lw=1.8, capsize=3,
                    color=colour, label=f"{run['model']}, {run['compressor']}")

    ax.set_xticks(range(len(BUDGETS)), BUDGETS)
    ax.set_xlabel("Compression budget (fraction of each statement's words kept)")
    ax.set_ylabel("Hit@1 (%)")
    ax.set_title("On AMI, compression takes the reader below a label-only shortcut", fontsize=11)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return save(fig, out / "dose_response")


def cross_corpus(runs: list[dict], out: Path) -> Path | None:
    import matplotlib.pyplot as plt

    drop = [r for r in runs if r["compressor"] == "word-drop" and r.get("paired")]
    if not drop:
        return None
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.axhline(0, color="0.3", lw=1)

    def curve(run: dict):
        """Budget 1.0 is the baseline, so its change is 0 by construction."""
        xs, point, lo, hi = [0], [0.0], [0.0], [0.0]
        for i, budget in enumerate(BUDGETS[1:], start=1):
            cell = run["paired"].get(budget)
            if not cell:
                continue
            mid, low, high = cell["delta"]
            xs.append(i)
            point.append(mid * 100)
            lo.append((mid - low) * 100)
            hi.append((high - mid) * 100)
        return xs, point, lo, hi

    order = sorted(drop, key=lambda r: curve(r)[1][-1])        # steepest fall first
    colours = ("#7a1f1f", "#c0392b", "#1f4e9c", "#5b8dd9", "#2e7d57", "#66aa88")
    for run, colour in zip(order, colours):
        xs, point, lo, hi = curve(run)
        ax.errorbar(xs, point, yerr=[lo, hi], marker="o", ms=4, lw=1.8, capsize=3,
                    color=colour,
                    label=f"{run['corpus']}, {run['model']} "
                          f"({run['main']['1.0']['target_words']:.0f} words/turn)")

    ax.set_xticks(range(len(BUDGETS)), BUDGETS)
    ax.set_xlabel("Compression budget (fraction of each statement's words kept)")
    ax.set_ylabel("Change in Hit@1 from uncompressed (pts)")
    ax.set_title("The more speaker evidence a turn carries, the more compression destroys", fontsize=11)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return save(fig, out / "cross_corpus")


def save(fig, stem: Path) -> Path:
    stem.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".pdf"):
        fig.savefig(stem.with_suffix(suffix), dpi=200, bbox_inches="tight")
    return stem.with_suffix(".png")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--summaries", type=Path, nargs="*", help="Analyzer *_summary.json files (default: all of them).")
    p.add_argument("--in-dir", type=Path, default=DEFAULT_IN)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()

    paths = args.summaries or sorted(args.in_dir.glob("*_summary.json"))
    if not paths:
        print(f"no *_summary.json under {args.in_dir}; run analyze_attribution_frozen.py first", file=sys.stderr)
        return 2
    runs = load(list(paths))
    if not runs:
        print("every summary is gate-only; there is no sweep to plot", file=sys.stderr)
        return 2

    written = [f for f in (dose_response(runs, args.out_dir), cross_corpus(runs, args.out_dir)) if f]
    for path in written:
        print(f"wrote {path} (+ .pdf)")
    print(f"from {len(runs)} swept run(s): " + ", ".join(f"{r['corpus']}/{r['model']}/{r['compressor']}" for r in runs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
