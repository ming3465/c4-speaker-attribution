"""Predicted-consumer-aware memory allocation (Contribution 1).

STATUS: PILOT SKELETON (lexical C1-C3 prototype); the current C1-C3 implementation lives outside this repo. See docs/C4_RUNBOOK.md, 'Code status'.

C4 established the headroom: `oracle_future_consumer` reaches 0.0% lost_at_write
at a 0.25 budget, where every fixed policy loses 60-67%. That oracle reads the
gold questions, so it is an upper bound, not a method.

This module replaces the oracle with predictors that only see the past. Each
predictor emits the same structure the oracle does -- uid -> set of participants
predicted to ask about that unit later -- so it drops straight into
`src.evaluation.failure_decomposition.build_store(consumers_by_uid=...)`
with no change to the C4 harness.

Predictors, weakest to strongest:

    RandomConsumerPredictor   lower-bound control; prediction carries no signal
    LexicalInterestPredictor  stdlib, no GPU; profiles each participant from
                              their own past questions and scores units by
                              idf-weighted overlap against that profile
    LearnedConsumerPredictor  the proposed pairwise scorer (needs torch + GPU)
    OracleConsumerPredictor   upper bound; reads gold. Grade against this.

The train/eval split matters. A participant's interest profile must be built
only from questions in the train split, or the lexical predictor leaks the
evaluation labels and quietly reports oracle numbers.
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol

from src.evaluation.failure_decomposition import MemoryQuestion, MemoryUnit, tokenize


# --------------------------------------------------------------------------
# shared types
# --------------------------------------------------------------------------

# uid -> participant -> probability that participant asks about the unit later
ConsumerScores = dict[str, dict[str, float]]

# uid -> set of participants, the shape build_store() consumes
ConsumerSets = dict[str, set[str]]


@dataclass
class PredictionReport:
    """How well predicted consumer sets match the gold ones."""

    predictor: str
    threshold: float
    precision: float
    recall: float
    f1: float
    predicted_pairs: int
    gold_pairs: int
    units_scored: int

    def as_row(self) -> dict[str, Any]:
        return {
            "predictor": self.predictor,
            "threshold": round(self.threshold, 3),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "predicted_pairs": self.predicted_pairs,
            "gold_pairs": self.gold_pairs,
            "units_scored": self.units_scored,
        }


class ConsumerPredictor(Protocol):
    """Scores, for each unit, how likely each participant is to need it later."""

    name: str

    def fit(
        self,
        train_questions: Iterable[MemoryQuestion],
        units_by_uid: dict[str, MemoryUnit],
    ) -> None: ...

    def predict(
        self,
        units: Iterable[MemoryUnit],
        participants: Iterable[str],
    ) -> ConsumerScores: ...


# --------------------------------------------------------------------------
# gold labels and split
# --------------------------------------------------------------------------

def gold_consumers(questions: Iterable[MemoryQuestion]) -> ConsumerSets:
    """uid -> participants who actually ask about that unit. The C4 oracle."""
    consumers: ConsumerSets = defaultdict(set)
    for question in questions:
        for uid in question.evidence_uids:
            consumers[uid].add(question.asker)
    return dict(consumers)


def split_questions(
    questions: list[MemoryQuestion],
    *,
    train_share: float = 0.5,
    seed: int = 0,
) -> tuple[list[MemoryQuestion], list[MemoryQuestion]]:
    """Deterministic split. Train builds interest profiles, eval grades them.

    Split by question, not by unit: the same unit may be evidence for several
    questions, and holding out units instead would leave participants with no
    profile at all.
    """
    ordered = sorted(questions, key=lambda q: q.qid)
    rng = random.Random(seed)
    rng.shuffle(ordered)
    cut = int(len(ordered) * train_share)
    return ordered[:cut], ordered[cut:]


def to_consumer_sets(scores: ConsumerScores, *, threshold: float) -> ConsumerSets:
    """Threshold scores into the set form build_store() expects.

    Multi-label on purpose: a unit may be needed by several participants, so
    this is a per-pair cutoff rather than an argmax over participants.
    """
    return {
        uid: {p for p, score in per_participant.items() if score >= threshold}
        for uid, per_participant in scores.items()
    }


# --------------------------------------------------------------------------
# predictors
# --------------------------------------------------------------------------

@dataclass
class OracleConsumerPredictor:
    """Upper bound. Reads gold, so it is a ceiling to measure against."""

    name: str = "oracle"
    _gold: ConsumerSets = field(default_factory=dict)

    def fit(self, train_questions, units_by_uid) -> None:  # noqa: ARG002
        raise NotImplementedError("Call fit_gold() with the full question set.")

    def fit_gold(self, all_questions: Iterable[MemoryQuestion]) -> None:
        self._gold = gold_consumers(all_questions)

    def predict(self, units, participants) -> ConsumerScores:  # noqa: ARG002
        return {
            unit.uid: {p: 1.0 for p in self._gold.get(unit.uid, set())}
            for unit in units
        }


@dataclass
class RandomConsumerPredictor:
    """Lower-bound control: same number of predicted pairs, no signal.

    Without this, a lexical gain cannot be separated from the gain of simply
    marking more units as important.
    """

    rate: float = 0.2
    seed: int = 0
    name: str = "random"

    def fit(self, train_questions, units_by_uid) -> None:  # noqa: ARG002
        return None

    def predict(self, units, participants) -> ConsumerScores:
        rng = random.Random(self.seed)
        roster = sorted(participants)
        return {
            unit.uid: {p: (1.0 if rng.random() < self.rate else 0.0) for p in roster}
            for unit in units
        }


@dataclass
class LexicalInterestPredictor:
    """Runnable today, no GPU: each participant is profiled by the words in the
    questions they asked in the train split; a unit scores high for a
    participant when its text overlaps that profile.

    This is the honest floor for "prediction is possible at all". If it beats
    RandomConsumerPredictor, future-consumer signal exists in the text; if it
    does not, the learned scorer needs to justify itself before any GPU time.
    """

    name: str = "lexical_interest"
    smoothing: float = 1.0
    _profiles: dict[str, Counter] = field(default_factory=dict)
    _idf: dict[str, float] = field(default_factory=dict)

    def fit(
        self,
        train_questions: Iterable[MemoryQuestion],
        units_by_uid: dict[str, MemoryUnit],
    ) -> None:
        train_questions = list(train_questions)

        # idf over the corpus so shared boilerplate does not dominate overlap
        document_frequency: Counter[str] = Counter()
        total = 0
        for unit in units_by_uid.values():
            total += 1
            document_frequency.update(set(tokenize(unit.text)))
        self._idf = {
            token: (total / (1 + df)) ** 0.5
            for token, df in document_frequency.items()
        }

        profiles: dict[str, Counter] = defaultdict(Counter)
        for question in train_questions:
            profiles[question.asker].update(tokenize(question.question))
            # what they previously needed is as informative as what they asked
            for uid in question.evidence_uids:
                unit = units_by_uid.get(uid)
                if unit is not None:
                    profiles[question.asker].update(tokenize(unit.text))
        self._profiles = dict(profiles)

    def predict(
        self,
        units: Iterable[MemoryUnit],
        participants: Iterable[str],
    ) -> ConsumerScores:
        roster = sorted(participants)
        scores: ConsumerScores = {}
        for unit in units:
            unit_tokens = set(tokenize(unit.text))
            if not unit_tokens:
                scores[unit.uid] = {p: 0.0 for p in roster}
                continue
            per_participant: dict[str, float] = {}
            for participant in roster:
                profile = self._profiles.get(participant)
                if not profile:
                    per_participant[participant] = 0.0
                    continue
                weight = sum(
                    self._idf.get(token, 1.0)
                    for token in unit_tokens
                    if token in profile
                )
                norm = sum(self._idf.get(token, 1.0) for token in unit_tokens)
                per_participant[participant] = weight / (norm + self.smoothing)
            scores[unit.uid] = per_participant
        return scores


@dataclass
class LearnedConsumerPredictor:
    """The proposed scorer: frozen LLM representations of (unit, context,
    candidate participant) into a small pairwise MLP with an independent
    sigmoid per pair (multi-label, not softmax over participants).

    Not implemented. Requires torch and a GPU, and should only be built after
    LexicalInterestPredictor demonstrates the signal exists.
    """

    name: str = "learned_pairwise"

    def fit(self, train_questions, units_by_uid) -> None:  # noqa: ARG002
        raise NotImplementedError(
            "C1 learned predictor not implemented. Needs torch + GPU; run "
            "LexicalInterestPredictor first to confirm the signal is there."
        )

    def predict(self, units, participants) -> ConsumerScores:  # noqa: ARG002
        raise NotImplementedError


# --------------------------------------------------------------------------
# grading
# --------------------------------------------------------------------------

def evaluate_predictor(
    predicted: ConsumerSets,
    gold: ConsumerSets,
    *,
    predictor: str,
    threshold: float,
) -> PredictionReport:
    """Pair-level precision/recall over (uid, participant) pairs.

    Graded only on units that carry at least one gold consumer; units no one
    ever asks about have no positive label and would otherwise inflate
    precision for a predictor that stays silent.
    """
    graded_uids = [uid for uid, consumers in gold.items() if consumers]

    true_positive = 0
    predicted_pairs = 0
    gold_pairs = 0
    for uid in graded_uids:
        gold_set = gold.get(uid, set())
        predicted_set = predicted.get(uid, set())
        true_positive += len(gold_set & predicted_set)
        predicted_pairs += len(predicted_set)
        gold_pairs += len(gold_set)

    precision = true_positive / predicted_pairs if predicted_pairs else 0.0
    recall = true_positive / gold_pairs if gold_pairs else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    return PredictionReport(
        predictor=predictor,
        threshold=threshold,
        precision=precision,
        recall=recall,
        f1=f1,
        predicted_pairs=predicted_pairs,
        gold_pairs=gold_pairs,
        units_scored=len(graded_uids),
    )


PREDICTORS = {
    "random": RandomConsumerPredictor,
    "lexical_interest": LexicalInterestPredictor,
    "learned_pairwise": LearnedConsumerPredictor,
}


# --------------------------------------------------------------------------
# threshold-free grading
# --------------------------------------------------------------------------

@dataclass
class RankReport:
    """Ranking quality, independent of any score threshold.

    A global cutoff conflates two things: whether the predictor ranks the right
    participant first, and whether its scores happen to be calibrated. This
    measures only the first, which is what allocation actually needs -- units
    compete for a fixed budget, so relative order is what matters.
    """

    predictor: str
    mrr: float
    hit_at_1: float
    hit_at_3: float
    units_scored: int
    participants: int

    def as_row(self) -> dict[str, Any]:
        return {
            "predictor": self.predictor,
            "mrr": round(self.mrr, 4),
            "hit_at_1": round(self.hit_at_1, 4),
            "hit_at_3": round(self.hit_at_3, 4),
            "units_scored": self.units_scored,
            "participants": self.participants,
        }


def evaluate_ranking(
    scores: ConsumerScores,
    gold: ConsumerSets,
    *,
    predictor: str,
    seed: int = 0,
) -> RankReport:
    """Rank participants per unit; ask where the true consumers land.

    Ties are broken randomly rather than by dict order. A predictor that
    returns identical scores for every participant would otherwise inherit the
    roster's alphabetical order and score like a real ranker.
    """
    rng = random.Random(seed)
    reciprocal_ranks: list[float] = []
    hits_1 = 0
    hits_3 = 0
    graded = 0
    roster_size = 0

    for uid, gold_consumers_for_unit in gold.items():
        if not gold_consumers_for_unit:
            continue
        per_participant = scores.get(uid)
        if not per_participant:
            continue
        roster_size = max(roster_size, len(per_participant))
        ordered = sorted(
            per_participant.items(),
            key=lambda item: (-item[1], rng.random()),
        )
        ranked = [participant for participant, _ in ordered]
        best = min(
            (ranked.index(c) + 1 for c in gold_consumers_for_unit if c in ranked),
            default=None,
        )
        if best is None:
            continue
        graded += 1
        reciprocal_ranks.append(1.0 / best)
        hits_1 += int(best <= 1)
        hits_3 += int(best <= 3)

    if not graded:
        return RankReport(predictor, 0.0, 0.0, 0.0, 0, roster_size)

    return RankReport(
        predictor=predictor,
        mrr=sum(reciprocal_ranks) / graded,
        hit_at_1=hits_1 / graded,
        hit_at_3=hits_3 / graded,
        units_scored=graded,
        participants=roster_size,
    )
