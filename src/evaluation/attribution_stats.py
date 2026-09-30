"""Statistics shared by the headroom gate and the C4 analysis.

One implementation, so the gate's pass/fail decision and the reported tables
are computed identically.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from statistics import NormalDist, stdev

RESAMPLES = 2000
SEED = 20260923
Z_ALPHA = NormalDist().inv_cdf(0.975)   # two-sided alpha = .05
Z_POWER = NormalDist().inv_cdf(0.80)    # power = .80


def _bootstrap_means(items: list[tuple[str, float]], resamples: int, seed: int) -> list[float]:
    """Sorted means of `resamples` cluster-bootstrap draws."""
    clusters: dict[str, list[float]] = defaultdict(list)
    for cluster, value in items:
        clusters[cluster].append(value)
    keys = list(clusters)
    rng = random.Random(seed)
    means = []
    for _ in range(resamples):
        total = count = 0.0
        for _ in keys:
            values = clusters[keys[rng.randrange(len(keys))]]
            total += sum(values)
            count += len(values)
        means.append(total / count)
    return sorted(means)


def cluster_ci(items: list[tuple[str, float]], *, resamples: int = RESAMPLES,
               seed: int = SEED) -> tuple[float, float, float]:
    """Mean with a cluster-bootstrap 95% CI. items = (cluster_id, value).

    Clusters (questions or conversations) are resampled with replacement,
    because probes sharing a context are not independent.
    """
    if not items:
        return float("nan"), float("nan"), float("nan")
    means = _bootstrap_means(items, resamples, seed)
    point = sum(v for _, v in items) / len(items)
    return point, means[int(0.025 * resamples)], means[int(0.975 * resamples) - 1]


@dataclass(frozen=True)
class Sensitivity:
    """What one estimate can and cannot rule out, from the same draws as cluster_ci."""

    point: float
    lo95: float
    hi95: float
    lo90: float
    hi90: float
    se: float
    mde: float
    margin: float

    @property
    def significant(self) -> bool:
        """The 95% CI excludes zero."""
        return self.lo95 > 0 or self.hi95 < 0

    @property
    def equivalent(self) -> bool:
        """TOST at alpha .05: the 90% CI lies inside (-margin, +margin)."""
        return -self.margin < self.lo90 and self.hi90 < self.margin

    @property
    def reading(self) -> str:
        if self.significant:
            return "real but inside the margin" if self.equivalent else "effect"
        return "no effect beyond the margin" if self.equivalent else "inconclusive"


def sensitivity(items: list[tuple[str, float]], *, margin: float, resamples: int = RESAMPLES,
                seed: int = SEED) -> Sensitivity:
    """Smallest detectable effect and an equivalence verdict for one estimate.

    mde = (Z_ALPHA + Z_POWER) x cluster-bootstrap SE: the true effect found 80%
    of the time at two-sided alpha .05; smaller true effects are likely missed.
    The equivalence verdict is valid only if `margin` was fixed before the run.
    """
    if not items:
        nan = float("nan")
        return Sensitivity(nan, nan, nan, nan, nan, nan, nan, margin)
    means = _bootstrap_means(items, resamples, seed)
    point = sum(v for _, v in items) / len(items)
    se = stdev(means)
    return Sensitivity(point=point,
                       lo95=means[int(0.025 * resamples)], hi95=means[int(0.975 * resamples) - 1],
                       lo90=means[int(0.05 * resamples)], hi90=means[int(0.95 * resamples) - 1],
                       se=se, mde=(Z_ALPHA + Z_POWER) * se, margin=margin)


def mcnemar_exact(n01: int, n10: int) -> float:
    """Two-sided exact McNemar p-value on discordant pair counts."""
    n = n01 + n10
    if n == 0:
        return 1.0
    k = min(n01, n10)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)
