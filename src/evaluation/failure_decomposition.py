"""Failure-mode decomposition: formation vs retrieval vs interpretation.

Contribution 4 instrument. Given a memory store built under a fixed word
budget, every question is attributed to exactly one bucket, in this order:

1. lost_at_write   - no gold evidence unit still supports the answer after
                     write-time compression.
2. not_retrieved   - a supporting unit survived but is not in the top-k.
3. answer_visible  - a supporting unit survived and was retrieved. Splitting
                     this into `correct` and `retrieved_but_misinterpreted`
                     requires a reader model (see docs/FAILURE_DECOMPOSITION.md).
"""

from __future__ import annotations

import math
import re
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import zip_longest
from typing import Any, Callable, Iterable

TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_\-/:.]*")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does", "for",
    "from", "has", "have", "how", "in", "into", "is", "it", "its", "of", "on",
    "or", "so", "that", "the", "then", "this", "to", "was", "were", "what",
    "when", "where", "which", "who", "whom", "will", "with",
}

DATE_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")


def tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(str(text))
        if token.lower() not in STOPWORDS and len(token) > 1
    ]


def answer_tokens(answer: str) -> set[str]:
    """Answer content tokens, with date variants so `2025-07-14` also matches
    the `07-14` / `july 14` spellings that appear in message bodies."""
    tokens = set(tokenize(answer))
    for year, month, day in DATE_RE.findall(str(answer)):
        tokens |= {f"{month}-{day}", f"{month}/{day}", f"{year}-{month}"}
    return tokens


def _date_like(token: str) -> bool:
    return any(c.isdigit() for c in token) and any(c in "-/:." for c in token)


def answer_support(gold: set[str], text: str) -> float:
    """Fraction of answer content tokens visible in `text`.

    Matching is exact except for date-like tokens, where a substring match lets
    `07-14` count against `2025-07-14`. A general substring fallback would let
    `ai` match `email`, which inflates formation success.
    """
    if not gold:
        return 0.0
    seen = set(tokenize(text))
    hit = 0
    for token in gold:
        if token in seen:
            hit += 1
        elif _date_like(token) and any(token in candidate for candidate in seen):
            hit += 1
    return hit / len(gold)


@dataclass(frozen=True)
class MemoryUnit:
    uid: str
    group: str
    text: str
    author: str
    role: str
    order: int
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryQuestion:
    qid: str
    category: str
    question: str
    answer: str
    asker: str
    evidence_uids: tuple[str, ...]


# --------------------------------------------------------------------------
# write-time compression
# --------------------------------------------------------------------------

def corpus_idf(units: Iterable[MemoryUnit]) -> dict[str, float]:
    document_frequency: Counter[str] = Counter()
    total = 0
    for unit in units:
        total += 1
        document_frequency.update(set(tokenize(unit.text)))
    return {
        token: math.log((total + 1) / (count + 1)) + 1.0
        for token, count in document_frequency.items()
    }


def salience_order(text: str, idf: dict[str, float]) -> tuple[int, ...]:
    """Word positions sorted by IDF, highest first. Precomputed once per unit so
    that re-compressing at many budgets is cheap."""
    words = text.split()
    def weight(index: int) -> float:
        parts = tokenize(words[index])
        return idf.get(parts[0], 0.0) if parts else 0.0
    return tuple(sorted(range(len(words)), key=weight, reverse=True))


def compress(text: str, keep_words: int, order: tuple[int, ...], mode: str) -> str:
    """Keep `keep_words` words. `salient` approximates what a summariser would
    retain (highest-IDF content, original order); `prefix` is naive truncation."""
    words = text.split()
    if keep_words <= 0:
        return ""
    if keep_words >= len(words) or mode == "prefix":
        return " ".join(words[:keep_words])
    kept = sorted(order[:keep_words])
    return " ".join(words[i] for i in kept)


def chunk_units(
    units: list[MemoryUnit], size: int
) -> tuple[list[MemoryUnit], dict[str, str]]:
    """Merge consecutive units inside a group into coarser memory units.

    Retrieval granularity is a design choice, not a property of the benchmark:
    a single chat message is a much harder retrieval target than a thread-sized
    memory. Returns the new units plus a map from original uid to chunk uid so
    gold evidence pointers can be rewritten.
    """
    if size <= 1:
        return units, {unit.uid: unit.uid for unit in units}
    grouped: dict[str, list[MemoryUnit]] = defaultdict(list)
    for unit in units:
        grouped[unit.group].append(unit)
    chunked: list[MemoryUnit] = []
    mapping: dict[str, str] = {}
    for group, members in grouped.items():
        members.sort(key=lambda u: u.order)
        for start in range(0, len(members), size):
            block = members[start : start + size]
            uid = f"{block[0].uid}__chunk{size}"
            for member in block:
                mapping[member.uid] = uid
            chunked.append(
                MemoryUnit(
                    uid=uid,
                    group=group,
                    text=" ".join(m.text for m in block),
                    author=block[-1].author,
                    role=block[-1].role,
                    order=block[0].order,
                    meta={
                        "is_noise": all(m.meta.get("is_noise") for m in block),
                        "is_decision_point": any(
                            m.meta.get("is_decision_point") for m in block
                        ),
                    },
                )
            )
    return chunked, mapping


# --------------------------------------------------------------------------
# write policies: order units by claim on the residual (fidelity) budget
# --------------------------------------------------------------------------

def _tiebreak(unit: MemoryUnit) -> int:
    """Deterministic, order-independent tiebreak so that a policy with no
    opinion does not silently degenerate into a recency policy."""
    return zlib.crc32(unit.uid.encode())


def _by_score(units: list[MemoryUnit], score: Callable[[MemoryUnit], float]) -> list[MemoryUnit]:
    return sorted(units, key=lambda u: (-score(u), _tiebreak(u)))


def order_uniform(units: list[MemoryUnit], ctx: dict[str, Any]) -> list[MemoryUnit]:
    """Uniform compression spends its whole budget on equal shared cores, so no
    unit has a claim on residual detail."""
    return []


def order_recency(units: list[MemoryUnit], ctx: dict[str, Any]) -> list[MemoryUnit]:
    return sorted(units, key=lambda u: -u.order)


def order_speaker_partitioned(units: list[MemoryUnit], ctx: dict[str, Any]) -> list[MemoryUnit]:
    """Per-speaker stores of equal size: the residual budget is shared equally
    between speakers (round robin), newest first inside each speaker."""
    per_author: dict[str, list[MemoryUnit]] = defaultdict(list)
    for unit in sorted(units, key=lambda u: -u.order):
        per_author[unit.author].append(unit)
    queues = [per_author[author] for author in sorted(per_author)]
    ordered: list[MemoryUnit] = []
    for row in zip_longest(*queues):
        ordered.extend(unit for unit in row if unit is not None)
    return ordered


def order_amac_global_utility(units: list[MemoryUnit], ctx: dict[str, Any]) -> list[MemoryUnit]:
    def score(unit: MemoryUnit) -> float:
        if unit.meta.get("is_noise"):
            return -1.0
        return 2.0 if unit.meta.get("is_decision_point") else 1.0

    return _by_score(units, score)


def order_oracle_future_consumer(units: list[MemoryUnit], ctx: dict[str, Any]) -> list[MemoryUnit]:
    """Oracle upper bound: a unit that some *other* participant later asks about
    keeps high fidelity. Built once per group from every question in that group,
    never from the single question being graded."""
    consumers_by_uid = ctx["consumers_by_uid"]

    def score(unit: MemoryUnit) -> float:
        consumers = consumers_by_uid.get(unit.uid, set())
        if consumers - {unit.author}:
            return 3.0
        return 1.0 if consumers else 0.0

    return _by_score(units, score)


POLICIES: dict[str, Callable[[list[MemoryUnit], dict[str, Any]], list[MemoryUnit]]] = {
    "uniform_compression": order_uniform,
    "recency_window": order_recency,
    "speaker_partitioned_memory": order_speaker_partitioned,
    "amac_global_utility": order_amac_global_utility,
    "oracle_future_consumer": order_oracle_future_consumer,
}


def build_store(
    units: list[MemoryUnit],
    *,
    policy: str,
    budget_fraction: float,
    salience: dict[str, tuple[int, ...]],
    consumers_by_uid: dict[str, set[str]],
    core_share: float = 0.5,
    compressor: str = "salient",
) -> dict[str, str]:
    """Allocate a hard word budget across units and return stored text per uid.

    Every unit first receives an equal shared core; the remainder is spent as
    role-conditioned residual detail in policy order. Uniform compression has
    no residual claim, so it spends the whole budget on equal cores. Every
    policy therefore stores the same number of words.
    """
    total_words = sum(len(unit.text.split()) for unit in units)
    if budget_fraction >= 1.0:
        return {unit.uid: unit.text for unit in units}
    budget = int(total_words * budget_fraction)
    ranked = POLICIES[policy](units, {"consumers_by_uid": consumers_by_uid})
    share = 1.0 if not ranked else core_share

    stored: dict[str, int] = {}
    spent = 0
    core_words = max(1, int(budget * share / max(len(units), 1)))
    for unit in units:
        keep = min(core_words, len(unit.text.split()))
        stored[unit.uid] = keep
        spent += keep

    remaining = budget - spent
    for unit in ranked:
        if remaining <= 0:
            break
        extra = min(len(unit.text.split()) - stored[unit.uid], remaining)
        if extra > 0:
            stored[unit.uid] += extra
            remaining -= extra
    if remaining > 0:  # uniform: spread any rounding slack evenly
        for unit in units:
            if remaining <= 0:
                break
            extra = min(len(unit.text.split()) - stored[unit.uid], remaining, 2)
            stored[unit.uid] += extra
            remaining -= extra
    return {
        unit.uid: compress(unit.text, stored[unit.uid], salience[unit.uid], compressor)
        for unit in units
    }


# --------------------------------------------------------------------------
# retrieval
# --------------------------------------------------------------------------

class BM25Index:
    def __init__(self, docs: dict[str, str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.postings: dict[str, list[tuple[str, int]]] = defaultdict(list)
        self.length: dict[str, int] = {}
        for uid, text in docs.items():
            tokens = Counter(tokenize(text))
            self.length[uid] = sum(tokens.values())
            for token, count in tokens.items():
                self.postings[token].append((uid, count))
        self.n = max(len(docs), 1)
        self.avgdl = sum(self.length.values()) / self.n or 1.0

    def search(self, query: str, top_k: int) -> list[str]:
        scores: dict[str, float] = defaultdict(float)
        for token in set(tokenize(query)):
            posting = self.postings.get(token)
            if not posting:
                continue
            idf = math.log(1 + (self.n - len(posting) + 0.5) / (len(posting) + 0.5))
            for uid, count in posting:
                norm = 1 - self.b + self.b * self.length[uid] / self.avgdl
                scores[uid] += idf * count * (self.k1 + 1) / (count + self.k1 * norm)
        return [uid for uid, _ in sorted(scores.items(), key=lambda kv: -kv[1])[:top_k]]


# --------------------------------------------------------------------------
# decomposition
# --------------------------------------------------------------------------

def decompose_question(
    question: MemoryQuestion,
    stored: dict[str, str],
    index: BM25Index,
    *,
    top_k: int,
    tau: float,
) -> dict[str, Any]:
    gold = answer_tokens(question.answer)
    supports = {
        uid: answer_support(gold, stored.get(uid, ""))
        for uid in question.evidence_uids
    }
    surviving = {uid for uid, value in supports.items() if value >= tau}
    retrieved = index.search(question.question, top_k)
    hit = surviving & set(retrieved)
    if not surviving:
        bucket = "lost_at_write"
    elif not hit:
        bucket = "not_retrieved"
    else:
        bucket = "answer_visible"
    return {
        "qid": question.qid,
        "category": question.category,
        "bucket": bucket,
        "best_support": round(max(supports.values(), default=0.0), 4),
        "evidence_units": len(question.evidence_uids),
        "surviving_units": len(surviving),
        "gold_in_topk": len(set(question.evidence_uids) & set(retrieved)),
        "retrieved_uids": retrieved,
    }


BUCKETS = ("lost_at_write", "not_retrieved", "answer_visible")


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_category[row["category"]][row["bucket"]] += 1
        by_category["ALL"][row["bucket"]] += 1
    summary: dict[str, dict[str, float]] = {}
    for category, counts in by_category.items():
        total = sum(counts.values())
        summary[category] = {"n": total} | {
            bucket: round(100.0 * counts[bucket] / total, 1) for bucket in BUCKETS
        }
    return summary
