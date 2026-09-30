"""Shared fixtures for the C4 attribution tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.evaluation.failure_decomposition import MemoryUnit

ROOT = Path(__file__).resolve().parents[1]
PILOT_BUNDLE = ROOT / "data" / "pilot" / "c4"
PILOT_BUDGETS = (1.0, 0.75, 0.5, 0.25, 0.1)
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def unit(uid: str, author: str, text: str, *, group: str = "c1", order: int = 0) -> MemoryUnit:
    return MemoryUnit(uid=uid, group=group, text=text, author=author, role="", order=order)


@pytest.fixture(scope="session")
def pilot():
    """Pilot bundle, its stores at every budget, and the frozen probes (slow)."""
    from src.datasets.memory_tasks import load_pilot_bundle
    from src.evaluation.attribution_frozen import build_stores, freeze_probes

    if not (PILOT_BUNDLE / "corpus_10pct.jsonl").exists():
        pytest.skip("GroupMemBench pilot bundle not present (it has no licence, so it is not redistributed)")
    units, questions = load_pilot_bundle(PILOT_BUNDLE, "corpus_10pct.jsonl")
    stores = build_stores(units, questions, policy="uniform_compression", budgets=PILOT_BUDGETS)
    probes = freeze_probes(questions, units, stores[1.0])
    return {"units": units, "questions": questions, "stores": stores, "probes": probes}
