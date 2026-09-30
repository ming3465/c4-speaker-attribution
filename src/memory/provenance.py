"""Provenance-preserving compression (Contribution 2).

STATUS: PILOT SKELETON (lexical C1-C3 prototype); the current C1-C3 implementation lives outside this repo. See docs/C4_RUNBOOK.md, 'Code status'.

The claim is about *metadata surviving compression*, not about storage layout.
A compressed unit keeps who said it, in what role, in what channel, and when,
even after its content has been reduced to a fraction of the original words.

This is deliberately NOT partitioning. Splitting memory into per-speaker stores
is prior art (Collaborative Memory, arXiv 2505.18279; MuPPET, arXiv 2606.23217)
and appears in this project as the `speaker_partitioned_memory` baseline that
C4 already runs. C2 is the weaker, more defensible claim: one shared store, but
provenance is a first-class field that compression is not allowed to drop.

Status: interface + metrics implemented; the compressor itself currently
delegates to C4's salience ordering. Swap in the learned compressor once C1's
allocation signal is trained.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from src.evaluation.failure_decomposition import MemoryUnit, tokenize


@dataclass(frozen=True)
class Provenance:
    """The fields that must survive compression intact."""

    author: str
    role: str
    group: str
    order: int
    timestamp: Any = None

    @classmethod
    def from_unit(cls, unit: MemoryUnit) -> "Provenance":
        return cls(
            author=unit.author,
            role=unit.role,
            group=unit.group,
            order=unit.order,
            timestamp=unit.meta.get("timestamp"),
        )

    def is_intact(self) -> bool:
        """Provenance counts as preserved only if the source is identifiable."""
        return bool(self.author) and bool(self.role)


@dataclass
class ProvenanceUnit:
    """A compressed unit that carries its own source.

    `fidelity` is the share of original words retained, so a unit's content
    cost and its provenance cost can be reported separately -- the point of C2
    is that provenance is nearly free while content is not.
    """

    uid: str
    text: str
    provenance: Provenance
    fidelity: float
    original_words: int

    @property
    def stored_words(self) -> int:
        return len(self.text.split())

    @property
    def provenance_words(self) -> int:
        """Word cost of carrying provenance inline, for budget accounting."""
        return len(f"{self.provenance.author} {self.provenance.role}".split())


def compress_with_provenance(
    units: Iterable[MemoryUnit],
    *,
    fidelity: float,
    salience: dict[str, tuple[int, ...]] | None = None,
) -> list[ProvenanceUnit]:
    """Reduce content to `fidelity` of its words, keeping provenance whole.

    `salience` reuses C4's per-unit token ordering when provided; without it
    this degrades to a prefix cut, which is the weaker compressor C4 exposes
    as `--compressor prefix`.
    """
    if not 0.0 <= fidelity <= 1.0:
        raise ValueError(f"fidelity must be in [0, 1], got {fidelity}")

    compressed: list[ProvenanceUnit] = []
    for unit in units:
        words = unit.text.split()
        keep = max(1, int(round(len(words) * fidelity))) if words else 0

        if salience and unit.uid in salience:
            order = [i for i in salience[unit.uid] if i < len(words)][:keep]
            kept = [words[i] for i in sorted(order)]
        else:
            kept = words[:keep]

        compressed.append(
            ProvenanceUnit(
                uid=unit.uid,
                text=" ".join(kept),
                provenance=Provenance.from_unit(unit),
                fidelity=fidelity,
                original_words=len(words),
            )
        )
    return compressed


def provenance_retention(units: Iterable[ProvenanceUnit]) -> dict[str, float]:
    """The C2 headline metric: does the source survive compression?

    `content_retained` should fall with the budget while `provenance_retained`
    stays at 1.0. If provenance also falls, C2 is not implemented correctly --
    the whole claim is that these two curves come apart.
    """
    units = list(units)
    if not units:
        return {"provenance_retained": 0.0, "content_retained": 0.0, "units": 0}

    intact = sum(u.provenance.is_intact() for u in units)
    stored = sum(u.stored_words for u in units)
    original = sum(u.original_words for u in units)
    overhead = sum(u.provenance_words for u in units)

    return {
        "provenance_retained": intact / len(units),
        "content_retained": stored / original if original else 0.0,
        "provenance_overhead": overhead / stored if stored else 0.0,
        "units": len(units),
    }


def role_confusion(units: Iterable[ProvenanceUnit]) -> dict[str, int]:
    """Units whose content survived but whose role did not.

    These are the cases that produce the interpretation failures C3 targets:
    the text is readable but the reader cannot tell who it came from.
    """
    counts: dict[str, int] = {"recoverable": 0, "orphaned": 0}
    for unit in units:
        has_content = bool(tokenize(unit.text))
        if has_content and not unit.provenance.is_intact():
            counts["orphaned"] += 1
        elif has_content:
            counts["recoverable"] += 1
    return counts
