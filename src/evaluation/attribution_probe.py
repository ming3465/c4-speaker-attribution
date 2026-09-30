"""Compression-induced attribution failure (Contribution 4, re-scoped).

STATUS: SUPERSEDED by the C4 v2 frozen-probe design (src/evaluation/attribution_frozen.py); kept only to reproduce the v1 pilot. See docs/C4_RUNBOOK.md, 'Code status'.

WhenLoss (arXiv 2605.24579) decomposes memory failures into write-side and
retrieval-side gaps, so that instrument is taken. Its benchmarks are single- or
two-party, which makes one question unaskable there: when several people's
compressed statements are retrieved together, can the reader still tell who
said what?

That is a *binding* failure, distinct from content loss. A snippet can retain
its answer tokens and still lose the link to its source. C2 measures whether
the speaker label survives as metadata (it trivially does, since it is stored
separately). This measures whether the reader can recover the source from the
compressed text itself.

Design mirrors 2b: hold everything fixed, vary one thing, report against a
stated random floor.

    independent variable   compression budget
    stratifier             number of distinct speakers in the retrieved set
    metric                 Hit@1 attribution accuracy
    floor                  1 / |candidates|

The counterfactual arm is the direct analogue of 2b's: identical statement
text, reassigned gold speaker, so content cannot disambiguate and only
surviving provenance can.
"""
from __future__ import annotations

import random
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

from src.evaluation.failure_decomposition import MemoryQuestion, MemoryUnit
from src.evaluation.reader_pass import build_reader_items

UNKNOWN = "UNKNOWN"


# --------------------------------------------------------------------------
# items
# --------------------------------------------------------------------------

@dataclass
class AttributionItem:
    """One probe: a statement, a candidate roster, and the visible evidence.

    `snippets` never contains the target's speaker label -- that is the whole
    point. If it leaks in, the task degenerates to string matching and every
    number below is meaningless. `verify_no_leak()` checks this.
    """

    qid: str
    budget: float
    target_text: str
    gold_author: str
    gold_role: str
    candidates: list[str]
    snippets: list[dict[str, str]]
    n_speakers: int
    is_counterfactual: bool = False
    condition: str = "main"
    # True when the gold author also appears, labelled, in another visible
    # snippet. Only these probes are solvable by binding; the rest can only be
    # answered from content priors. The bindable share itself falls as the
    # budget tightens, so accuracy must be compared within this subset or the
    # budget effect is confounded with sample composition.
    gold_in_context: bool = False

    def prompt(self) -> str:
        lines = []
        for index, snippet in enumerate(self.snippets, start=1):
            speaker = snippet.get("speaker") or UNKNOWN
            # Render the blinded label as "?" rather than the UNKNOWN sentinel:
            # with a word there, the reader copies it as its answer (observed on
            # 6/8 probes), which scores as failure for a reason unrelated to
            # binding and drags accuracy below the random floor.
            shown = "?" if speaker == UNKNOWN else speaker
            lines.append(f"[{index}] ({shown}) {snippet['text']}")
        context = "\n".join(lines)
        roster = ", ".join(self.candidates)
        return f"""You are identifying the author of a statement from a group conversation.

Rules:
- Answer with exactly one name from the candidate list.
- You must choose one name even if you are unsure; give your best guess.
- Reply with the name only, no explanation and no markdown.

Candidates:
{roster}

Conversation snippets:
{context}

Statement:
{self.target_text}

Who said the statement?
"""

    def verify_no_leak(self) -> bool:
        """The gold speaker must not be attached to the target snippet."""
        target = self.target_text.strip()
        for snippet in self.snippets:
            if snippet["text"].strip() == target:
                if (snippet.get("speaker") or UNKNOWN) != UNKNOWN:
                    return False
        return True


# --------------------------------------------------------------------------
# construction
# --------------------------------------------------------------------------

def build_attribution_items(
    units: list[MemoryUnit],
    questions: list[MemoryQuestion],
    *,
    policy: str,
    budget: float,
    top_k: int = 5,
    tau: float = 0.65,
    seed: int = 0,
    n_candidates: int = 6,
) -> list[AttributionItem]:
    """Build one probe per question at a given compression budget.

    Built from every graded question, not only the `answer_visible` subset:
    whether the memory question was answerable is irrelevant to whether the
    reader can attribute a retrieved snippet. Restricting to answer_visible
    would also bias the sample toward well-preserved evidence, which is exactly
    the confound this experiment is trying to measure.
    """
    rng = random.Random(seed)
    units_by_uid = {unit.uid: unit for unit in units}
    all_authors = sorted({u.author for u in units if u.author})

    # Reuse the reader pass's store construction and retrieval verbatim so the
    # evidence here is identical to what the reader pass sees.
    reader_items = build_reader_items(
        units, questions, policy=policy, budget=budget, top_k=top_k, tau=tau,
        all_questions=True,
    )

    items: list[AttributionItem] = []
    for reader_item in reader_items:
        snippets = [s for s in reader_item.snippets if s.get("text", "").strip()]
        speakers = [s.get("speaker", "") for s in snippets if s.get("speaker")]
        if len(snippets) < 2 or not speakers:
            continue

        # pick a target snippet that actually carries a speaker
        candidates_idx = [i for i, s in enumerate(snippets) if s.get("speaker")]
        target_idx = rng.choice(candidates_idx)
        target = snippets[target_idx]

        # blind the target's speaker; leave the others visible as context
        visible = []
        for i, s in enumerate(snippets):
            visible.append(
                {"text": s["text"], "speaker": UNKNOWN if i == target_idx else s.get("speaker", "")}
            )

        # Candidate roster must NOT be "the speakers present in this set". If it
        # were, blinding one snippet would leave exactly one unlabelled name and
        # the probe would be solvable by pure elimination without reading
        # anything -- measured at 39-50% of probes, and worsening as the budget
        # tightens, which would manufacture a spurious trend. Draw distractors
        # from the whole corpus instead so elimination carries no information.
        # Fixed roster size also pins the random floor at 1/n_candidates,
        # matching the 16.67% floor used in the 2a/2b studies.
        pool = [a for a in all_authors if a != target["speaker"]]
        picker = random.Random(f"{seed}:{reader_item.qid}:{budget}")
        distractors = picker.sample(pool, min(n_candidates - 1, len(pool)))
        roster = sorted([target["speaker"], *distractors])
        items.append(
            AttributionItem(
                qid=reader_item.qid,
                budget=budget,
                target_text=target["text"],
                gold_author=target["speaker"],
                gold_role=target.get("role", ""),
                candidates=roster,
                snippets=visible,
                n_speakers=len({v["speaker"] for v in visible if v["speaker"] and v["speaker"] != UNKNOWN} | {target["speaker"]}),
                gold_in_context=any(v["speaker"] == target["speaker"] for v in visible),
            )
        )
    return items


def build_counterfactual(item: AttributionItem, *, seed: int = 0) -> AttributionItem | None:
    """Relabel the true author's other snippets as a different candidate.

    Every word of evidence is byte-identical to the original probe; only the
    speaker labels on the gold author's *other* snippets change, from A to B,
    and the gold answer becomes B. A reader that binds the target to its
    same-speaker context follows the relabel and answers B. A reader relying
    on content priors about A (topic, vocabulary, role) still answers A.
    Direct analogue of the 2b counterfactual: content fixed, provenance varied.

    Only defined for bindable probes -- if A appears nowhere else, there is no
    label to move. Returns None for those.
    """
    if not item.gold_in_context:
        return None
    rng = random.Random(f"{seed}:{item.qid}:{item.budget}")
    others = [c for c in item.candidates if c != item.gold_author]
    if not others:
        return None
    new_author = rng.choice(others)
    relabelled = [
        {**s, "speaker": new_author} if s.get("speaker") == item.gold_author else dict(s)
        for s in item.snippets
    ]
    return AttributionItem(
        qid=item.qid,
        budget=item.budget,
        target_text=item.target_text,
        gold_author=new_author,
        gold_role=item.gold_role,
        candidates=item.candidates,
        snippets=relabelled,
        n_speakers=item.n_speakers,
        is_counterfactual=True,
        condition="counterfactual",
        gold_in_context=True,
    )


# --------------------------------------------------------------------------
# grading
# --------------------------------------------------------------------------

def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "", str(text).strip().lower())


def names_in_answer(answer: str, names: Iterable[str]) -> set[str]:
    """Names that appear in the answer as whole tokens.

    Whole-token, not substring: a substring test credits "User_13", "User_12"
    or "User_10" as a mention of "User_1". That produced 4 false positives in
    the v1 run -- 3 of them at budget 0.5, where they manufactured the only
    rise in the curve.
    """
    return {
        name for name in names
        if name and re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", answer, re.IGNORECASE)
    }


def grade(item: AttributionItem, answer: str) -> bool:
    """Correct iff the answer names the gold author and no other candidate.

    Tolerates "User_5 said it" style replies; rejects answers naming several
    candidates. Matching is whole-token (see names_in_answer).
    """
    if not answer:
        return False
    return names_in_answer(answer, item.candidates) == {item.gold_author}


# --------------------------------------------------------------------------
# baselines and controls
# --------------------------------------------------------------------------

def elimination_solvable_rate(items: Iterable[AttributionItem]) -> float:
    """Fraction of probes where the gold is the only candidate not already
    visible as a label. Those are answerable without reading the text at all.

    Must stay near 1/n_candidates. A high rate means the roster is leaking the
    answer through set difference rather than the model recovering provenance.
    """
    items = list(items)
    if not items:
        return 0.0
    hits = 0
    for item in items:
        seen = {s.get("speaker") for s in item.snippets if s.get("speaker") and s.get("speaker") != UNKNOWN}
        remaining = [c for c in item.candidates if c not in seen]
        if len(remaining) == 1 and remaining[0] == item.gold_author:
            hits += 1
    return hits / len(items)


def random_floor(items: Iterable[AttributionItem]) -> float:
    """Mean 1/|candidates|. Not a fixed constant -- roster size varies by item."""
    items = list(items)
    if not items:
        return 0.0
    return sum(1.0 / max(len(i.candidates), 1) for i in items) / len(items)


def majority_baseline(items: Iterable[AttributionItem]) -> float:
    """Always answer the globally most frequent speaker.

    If one participant dominates the corpus this can beat the random floor, and
    a model that has merely learned the prior would look informative without it.
    """
    items = list(items)
    if not items:
        return 0.0
    top = Counter(i.gold_author for i in items).most_common(1)[0][0]
    return sum(i.gold_author == top for i in items) / len(items)


def name_in_text_rate(items: Iterable[AttributionItem]) -> float:
    """Fraction of probes whose gold speaker is named in the visible text.

    These are answerable by string matching rather than by memory, so a high
    rate invalidates the headline number.
    """
    items = list(items)
    if not items:
        return 0.0
    hits = 0
    for item in items:
        blob = normalise(" ".join(s["text"] for s in item.snippets))
        if normalise(item.gold_author) and normalise(item.gold_author) in blob:
            hits += 1
    return hits / len(items)


def shuffle_labels(items: list[AttributionItem], *, seed: int = 0) -> list[AttributionItem]:
    """Permute gold speakers across probes. Accuracy must fall to the floor."""
    rng = random.Random(seed)
    golds = [i.gold_author for i in items]
    rng.shuffle(golds)
    return [
        AttributionItem(
            qid=i.qid, budget=i.budget, target_text=i.target_text,
            gold_author=g, gold_role=i.gold_role, candidates=i.candidates,
            snippets=i.snippets, n_speakers=i.n_speakers,
            is_counterfactual=i.is_counterfactual, condition="shuffled",
            gold_in_context=i.gold_in_context,
        )
        for i, g in zip(items, golds)
    ]


# --------------------------------------------------------------------------
# summary
# --------------------------------------------------------------------------

def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    correct = sum(r["correct"] for r in rows)
    by_speakers: dict[int, list[bool]] = {}
    for row in rows:
        by_speakers.setdefault(row["n_speakers"], []).append(row["correct"])
    return {
        "n": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "errors": sum(bool(r.get("error")) for r in rows),
        "by_speaker_count": {
            k: {"n": len(v), "accuracy": round(sum(v) / len(v), 4)}
            for k, v in sorted(by_speakers.items())
        },
    }
