"""Headroom gate: refuse a compression sweep that can only measure a floor.

The GroupMemBench pilot swept five budgets and found a flat curve -- because
the reader was at chance even uncompressed (lift +3.4 pts [-0.8, +7.4]). A flat
curve from a floor says nothing about compression. The gate runs the
uncompressed (budget 1.0) probes first and only allows the sweep when the
reader demonstrably attributes above chance AND demonstrably beats the
label-only heuristics (frequency; turn-taking on conversation windows), which
compression cannot touch.

The margin must be declared before the run (WhenLoss-style pre-declared
decision rule), not chosen after seeing the numbers.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from src.evaluation.attribution_stats import cluster_ci

DEFAULT_MARGIN = 0.05


@dataclass(frozen=True)
class GateResult:
    passed: bool
    n: int
    accuracy: float
    chance: float
    frequency: float
    lift: float
    lift_lo: float
    lift_hi: float
    margin: float
    reason: str
    turn_taking: float = float("nan")
    over_heuristic: float = float("nan")       # Hit@1 minus the stronger label-only heuristic
    over_heuristic_lo: float = float("nan")


def _heuristics(rows: list[dict]) -> dict[str, list[float]]:
    """Per-row expected accuracy of each label-only heuristic the rows record."""
    out = {"frequency": [float(r["freq_baseline"]) for r in rows]}
    turns = [r.get("turn_baseline") for r in rows]
    if all(t not in (None, "") for t in turns):
        out["turn-taking"] = [float(t) for t in turns]
    return out


def evaluate_gate(rows: Iterable[dict], *, margin: float = DEFAULT_MARGIN) -> GateResult:
    """rows: budget-1.0 main-arm rows with correct, chance, freq_baseline, cluster_id,
    and turn_baseline where recorded (rows older than it lack the column).

    PASS iff the lower 95% bound of (Hit@1 - chance) exceeds `margin` AND the
    lower 95% bound of (Hit@1 - the stronger label-only heuristic) exceeds 0:
    there is room to fall, and the reader demonstrably uses more than labels.
    """
    rows = list(rows)
    nan = float("nan")
    if not rows:
        return GateResult(False, 0, nan, nan, nan, nan, nan, nan, margin, "no budget-1.0 rows")
    n = len(rows)
    clusters = [str(r["cluster_id"]) for r in rows]
    correct = [float(bool(r["correct"])) for r in rows]
    accuracy = sum(correct) / n
    chance = sum(float(r["chance"]) for r in rows) / n
    lift, lo, hi = cluster_ci([(c, x - float(r["chance"])) for c, x, r in zip(clusters, correct, rows)])
    per_row = _heuristics(rows)
    means = {name: sum(values) / n for name, values in per_row.items()}
    best = max(means, key=means.get)
    gap, gap_lo, _ = cluster_ci([(c, x - h) for c, x, h in zip(clusters, correct, per_row[best])])
    reasons = []
    if not lo > margin:
        reasons.append(f"lift lower bound {lo:+.3f} does not exceed margin {margin:+.3f}")
    if not gap_lo > 0:
        reasons.append(f"accuracy {accuracy:.3f} does not clearly beat the {best} heuristic {means[best]:.3f} "
                       f"(lower bound of the lead {gap_lo:+.3f})")
    passed = not reasons
    reason = "headroom confirmed" if passed else "; ".join(reasons)
    return GateResult(passed, n, accuracy, chance, means["frequency"], lift, lo, hi, margin, reason,
                      means.get("turn-taking", nan), gap, gap_lo)


def gate_record(result: GateResult) -> dict:
    """The result as strict JSON (NaN -> null)."""
    return {k: None if isinstance(v, float) and math.isnan(v) else v for k, v in asdict(result).items()}


def write_gate(path: Path, result: GateResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(gate_record(result), indent=2), encoding="utf-8")
