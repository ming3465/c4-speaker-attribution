#!/usr/bin/env python3
"""Structural statistics that decide what the failure decomposition can claim.

Reports evidence density (how much of the corpus is ever asked about), evidence
sharing (how much of an oracle policy's advantage is per-question memorisation),
and cross-consumer rate (how often the asker is NOT the author of the evidence,
which is the precondition for a future-consumer signal to exist at all).
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.memory_tasks import load_groupmembench, load_locomo  # noqa: E402


def report(name: str, units, questions) -> None:
    by_uid = {unit.uid: unit for unit in units}
    citations: Counter[str] = Counter()
    cross = same = unknown = 0
    per_category: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for question in questions:
        for uid in question.evidence_uids:
            citations[uid] += 1
            unit = by_uid.get(uid)
            if unit is None or not question.asker:
                unknown += 1
            elif unit.author == question.asker:
                same += 1
                per_category[question.category][1] += 1
            else:
                cross += 1
                per_category[question.category][0] += 1
    total_pairs = cross + same
    evidence_units = len(citations)
    shared = sum(1 for count in citations.values() if count > 1)
    print(f"\n### {name}")
    print(f"units={len(units)}  questions={len(questions)}  distinct evidence units={evidence_units}")
    print(f"evidence density: {evidence_units / max(len(units), 1):.2%} of the corpus is ever cited")
    print(f"evidence sharing: {shared}/{evidence_units} ({shared / max(evidence_units, 1):.1%}) "
          "of evidence units are cited by more than one question")
    if total_pairs:
        print(f"cross-consumer rate: {cross}/{total_pairs} ({cross / total_pairs:.1%}) "
              "of (question, evidence) pairs have asker != evidence author")
        print(f"{'category':<18}{'cross':>7}{'same':>7}{'cross %':>9}")
        for category in sorted(per_category):
            c, s = per_category[category]
            print(f"{category:<18}{c:>7}{s:>7}{c / max(c + s, 1):>8.0%}")
    else:
        print(f"cross-consumer rate: not measurable ({unknown} pairs have no asker id)")


def main() -> int:
    units, questions = load_groupmembench(
        ROOT / "data/raw/groupmembench/synthetic_domain_channels_rolevariants_Finance.json",
        ROOT / "data/raw/groupmembench/questions/Finance",
        ROOT / "data/raw/gmb_agent_sessions/finance/questions_enhanced.jsonl",
    )
    report("GroupMemBench / Finance", units, questions)
    report("LoCoMo", *load_locomo(ROOT / "data/raw/locomo/locomo10.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
