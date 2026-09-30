"""Provenance-conditioned interpretation (Contribution 3).

The read-time half of the proposal. Given the same retrieved evidence, does
conditioning on *who said it and in what role* change how the model interprets
it? Unlike RISER, whose vectors encode reasoning skills, these encode
interpretation/disambiguation patterns tied to a conversational role.

C4 defines the only bucket where this claim can be tested: `answer_visible`
(evidence survived compression AND was retrieved). Splitting that bucket into
`correct` and `retrieved_but_misinterpreted` requires a reader model -- it is
listed as `pending` in configs/experiments/failure_decomposition.json.

    h' = h + lambda * g(query, provenance) * v_role

with `lambda` fixed initially, so the controller only has to learn *whether*
to intervene and *which* direction to use.

STATUS: interface only. This is the one contribution that genuinely needs a
GPU -- it reads and writes model hidden states, so there is no stdlib version.
Do not implement before the A100 is available and C4's reader pass exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class InterpretationVector:
    """One role-conditioned steering direction, applied at a single layer."""

    role: str
    layer: int
    direction: Sequence[float]
    provenance: str = "derived"

    def __post_init__(self) -> None:
        if not self.direction:
            raise ValueError("direction must be non-empty")


@dataclass
class InterventionDecision:
    """What the controller chose, kept auditable so ablations can replay it."""

    intervene: bool
    role: str | None
    strength: float
    reason: str


class ProvenanceConditionedInterpreter(Protocol):
    """Decides whether retrieved evidence needs role-conditioned reading."""

    def should_intervene(
        self,
        query: str,
        retrieved_provenance: Sequence[Any],
    ) -> InterventionDecision: ...

    def apply(
        self,
        hidden_states: Any,
        decision: InterventionDecision,
    ) -> Any: ...


@dataclass
class NoOpInterpreter:
    """Control arm: identical retrieved evidence, no intervention.

    The C3 experiment holds retrieval fixed and varies only interpretation, so
    this is the baseline every intervention is measured against.
    """

    name: str = "no_op"

    def should_intervene(self, query, retrieved_provenance) -> InterventionDecision:  # noqa: ARG002
        return InterventionDecision(
            intervene=False, role=None, strength=0.0, reason="control arm"
        )

    def apply(self, hidden_states, decision):  # noqa: ARG002
        return hidden_states


@dataclass
class RoleSteeringInterpreter:
    """The proposed intervention. Not implemented -- needs GPU + model internals.

    Build order once the A100 lands:
      1. C4 reader pass, to split `answer_visible` into correct vs
         misinterpreted. Without it there is no target metric.
      2. Derive per-role vectors from contrastive pairs (same content,
         different speaker role).
      3. Gate on (query, provenance); tune lambda last.
    """

    lambda_strength: float = 1.0
    name: str = "role_steering"

    def should_intervene(self, query, retrieved_provenance):  # noqa: ARG002
        raise NotImplementedError(
            "C3 requires a GPU and C4's reader pass. See module docstring."
        )

    def apply(self, hidden_states, decision):  # noqa: ARG002
        raise NotImplementedError
