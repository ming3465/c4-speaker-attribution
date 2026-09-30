"""Frozen-probe attribution design (C4 v2).

v1 (attribution_probe.py) rebuilt retrieval and re-drew the target at every
budget, so budget 1.0 and budget 0.1 measured different statements, speakers
and contexts -- only 6 of 98 targets matched between them. That is not a
dose-response. An adversarial audit confirmed it (3/3 verifiers).

v2 freezes each probe once and varies only the compression of its text:

    1. Build contexts once: either the budget-1.0 retrieval for a question
       (GroupMemBench) or a window of consecutive turns (any utterance data,
       e.g. AMI/ELITR -- see src/datasets/utterances.py).
    2. A probe = one message in a context as target, whose author ALSO appears
       on another message in the context ("bindable"); non-bindable targets
       cannot be solved by binding and are excluded.
    3. Roster = exactly the speakers visible in the context, in a shuffled but
       deterministic order. Chance = 1/|roster|. Every roster name is visible,
       so a "pick someone visible" heuristic is exactly chance, and the reader
       cannot answer off-roster by copying a label (v1: ~21% of answers).
    4. At each budget re-render the SAME message ids with that budget's
       compressed text. Only the text changes; probes are paired by probe_id.
       `scope` restricts compression to the target or to the context, to
       localize where binding breaks.

Counterfactual (swap): swap the labels A <-> B on the non-target messages,
choosing B with exactly as many visible labels as A. Presence is unchanged and
label counts are unchanged, so presence and frequency heuristics are both
indifferent. Only a reader that binds the target's content to its author's
other messages follows the swap and answers B. v1's relabel counterfactual
could not separate binding from presence (the relabelled name was the only
new visible label).
"""
from __future__ import annotations

import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from src.evaluation.failure_decomposition import (
    BM25Index,
    MemoryQuestion,
    MemoryUnit,
    build_store,
    corpus_idf,
    salience_order,
    tokenize,
)
from src.evaluation.ollama_client import DEFAULT_BASE_URL, OllamaClient

HIDDEN = "?"
SCOPES = ("both", "target", "context")


# --------------------------------------------------------------------------
# stores
# --------------------------------------------------------------------------

def build_stores(
    units: list[MemoryUnit],
    questions: list[MemoryQuestion],
    *,
    policy: str,
    budgets: Iterable[float],
    core_share: float = 0.5,
    compressor: str = "salient",
) -> dict[float, dict[str, str]]:
    """uid -> stored text, per budget. Mirrors reader_pass.build_reader_items."""
    idf = corpus_idf(units)
    salience = {unit.uid: salience_order(unit.text, idf) for unit in units}
    by_group: dict[str, list[MemoryUnit]] = defaultdict(list)
    for unit in units:
        by_group[unit.group].append(unit)
    consumers: dict[str, set[str]] = defaultdict(set)
    for question in questions:
        for uid in question.evidence_uids:
            consumers[uid].add(question.asker)

    stores: dict[float, dict[str, str]] = {}
    for budget in budgets:
        stored: dict[str, str] = {}
        for group_units in by_group.values():
            stored |= build_store(
                group_units,
                policy=policy,
                budget_fraction=budget,
                salience=salience,
                consumers_by_uid=consumers,
                core_share=core_share,
                compressor=compressor,
            )
        stores[budget] = stored
    return stores


# --------------------------------------------------------------------------
# contexts
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Context:
    """A fixed set of messages a probe is drawn from.

    `cluster_id` is the unit of statistical independence: the question for
    retrieval contexts, the conversation for windows (overlapping windows share
    turns, so windows from one conversation are not independent).
    """

    context_id: str
    cluster_id: str
    uids: tuple[str, ...]


def retrieval_contexts(
    questions: list[MemoryQuestion],
    full_store: dict[str, str],
    *,
    top_k: int = 5,
) -> list[Context]:
    """Top-k BM25 retrieval per question over the uncompressed store."""
    index = BM25Index(full_store)
    return [
        Context(question.qid, question.qid, tuple(index.search(question.question, top_k)))
        for question in questions
    ]


def window_contexts(units: list[MemoryUnit], *, size: int, stride: int) -> list[Context]:
    """Windows of `size` consecutive turns, every `stride` turns, per conversation.

    Never crosses a conversation boundary. A conversation shorter than `size`
    yields one window of all its turns.
    """
    if size < 2 or stride < 1:
        raise ValueError(f"window size must be >= 2 and stride >= 1 (got size={size}, stride={stride})")
    by_conversation: dict[str, list[MemoryUnit]] = defaultdict(list)
    for unit in units:
        by_conversation[unit.group].append(unit)
    contexts: list[Context] = []
    for conversation in sorted(by_conversation):
        turns = sorted(by_conversation[conversation], key=lambda u: u.order)
        for start in range(0, max(1, len(turns) - size + 1), stride):
            window = turns[start:start + size]
            contexts.append(Context(f"{conversation}@{start}", conversation, tuple(u.uid for u in window)))
    return contexts


# --------------------------------------------------------------------------
# probes
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class FrozenProbe:
    """Fixed once; identical across every budget it is rendered at."""

    probe_id: str
    qid: str                       # context id (the question id for retrieval)
    target_uid: str
    context_uids: tuple[str, ...]  # context order, target included
    speakers: tuple[str, ...]      # author of each context uid, same order
    gold_author: str
    roster: tuple[str, ...]        # visible speakers, deterministic shuffle
    cluster_id: str = ""

    @property
    def target_index(self) -> int:
        return self.context_uids.index(self.target_uid)


@dataclass(frozen=True)
class RenderedProbe:
    probe: FrozenProbe
    budget: float
    condition: str                 # "main" or "swap"
    gold: str
    labels: tuple[str, ...]        # label shown per context uid; HIDDEN on target
    texts: tuple[str, ...]         # budget-b text per context uid

    @property
    def target_text(self) -> str:
        return self.texts[self.probe.target_index]

    def prompt(self) -> str:
        lines = [f"[{i}] ({label}) {text}" for i, (label, text) in
                 enumerate(zip(self.labels, self.texts), start=1)]
        return f"""You are identifying the author of a statement from a group conversation.

Rules:
- Answer with exactly one name from the candidate list.
- You must choose one name even if you are unsure; give your best guess.
- Reply with the name only, no explanation and no markdown.

Candidates:
{", ".join(self.probe.roster)}

Conversation snippets:
{chr(10).join(lines)}

Statement:
{self.target_text}

Who said the statement?
"""


def probes_from_contexts(
    contexts: Iterable[Context],
    units: list[MemoryUnit],
    *,
    seed: int = 0,
    min_target_words: int = 0,
) -> list[FrozenProbe]:
    """One probe per bindable target in each context.

    `min_target_words` drops very short targets (backchannels such as "mm-hmm"
    in meeting transcripts), which carry nothing to attribute.
    """
    by_uid = {unit.uid: unit for unit in units}
    probes: list[FrozenProbe] = []
    for context in contexts:
        uids = tuple(uid for uid in context.uids if uid in by_uid and by_uid[uid].author)
        speakers = tuple(by_uid[uid].author for uid in uids)
        counts = Counter(speakers)
        roster_set = sorted(counts)
        if len(roster_set) < 2:
            continue  # a one-speaker context has chance 1.0 -- uninformative
        for uid, author in zip(uids, speakers):
            if counts[author] < 2:
                continue  # author not visible elsewhere -> not bindable
            if len(by_uid[uid].text.split()) < min_target_words:
                continue
            order = list(roster_set)
            random.Random(f"{seed}:{context.context_id}:{uid}:roster").shuffle(order)
            probes.append(FrozenProbe(
                probe_id=f"{context.context_id}:{uid}",
                qid=context.context_id,
                target_uid=uid,
                context_uids=uids,
                speakers=speakers,
                gold_author=author,
                roster=tuple(order),
                cluster_id=context.cluster_id,
            ))
    return probes


def freeze_probes(
    questions: list[MemoryQuestion],
    units: list[MemoryUnit],
    full_store: dict[str, str],
    *,
    top_k: int = 5,
    seed: int = 0,
) -> list[FrozenProbe]:
    """Pilot entry point: retrieval contexts, then probes. Uses every
    evidence-linked question -- attribution does not depend on whether the
    memory question was answerable."""
    return probes_from_contexts(retrieval_contexts(questions, full_store, top_k=top_k), units, seed=seed)


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _texts(probe: FrozenProbe, store: dict[str, str], full_store: dict[str, str] | None,
           scope: str) -> tuple[str, ...]:
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {SCOPES}, got {scope!r}")
    if scope == "both" or full_store is None:
        return tuple(store.get(uid, "") for uid in probe.context_uids)
    compress_target = scope == "target"
    return tuple(
        (store if (uid == probe.target_uid) == compress_target else full_store).get(uid, "")
        for uid in probe.context_uids
    )


def render_main(probe: FrozenProbe, store: dict[str, str], budget: float, *,
                full_store: dict[str, str] | None = None, scope: str = "both") -> RenderedProbe:
    labels = tuple(HIDDEN if uid == probe.target_uid else spk
                   for uid, spk in zip(probe.context_uids, probe.speakers))
    return RenderedProbe(probe, budget, "main", probe.gold_author, labels,
                         _texts(probe, store, full_store, scope))


def visible_counts(labels: Iterable[str]) -> Counter:
    return Counter(label for label in labels if label != HIDDEN)


def swap_partner(probe: FrozenProbe, *, seed: int = 0) -> str | None:
    """A speaker B != A with exactly as many visible labels as A, or None."""
    counts = visible_counts(render_main(probe, {}, 1.0).labels)
    a = probe.gold_author
    matches = sorted(s for s in counts if s != a and counts[s] == counts[a])
    if not matches:
        return None
    return random.Random(f"{seed}:{probe.probe_id}:swap").choice(matches)


def render_swap(probe: FrozenProbe, store: dict[str, str], budget: float, partner: str, *,
                full_store: dict[str, str] | None = None, scope: str = "both") -> RenderedProbe:
    """Swap labels A <-> B on the non-target messages; the gold becomes B."""
    a = probe.gold_author
    swapped = {a: partner, partner: a}
    main = render_main(probe, store, budget, full_store=full_store, scope=scope)
    labels = tuple(swapped.get(label, label) for label in main.labels)
    return RenderedProbe(probe, budget, "swap", partner, labels, main.texts)


# --------------------------------------------------------------------------
# grading and baselines
# --------------------------------------------------------------------------

def names_in_answer(answer: str, names: Iterable[str]) -> set[str]:
    """Whole-token matches only; "User_13" is not a mention of "User_1"."""
    return {
        name for name in names
        if name and re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", answer, re.IGNORECASE)
    }


def grade(rendered: RenderedProbe, answer: str) -> tuple[bool, bool, str]:
    """(correct, valid, named). Valid = names exactly one roster member."""
    named = names_in_answer(answer or "", rendered.probe.roster)
    valid = len(named) == 1
    pick = next(iter(named)) if valid else ""
    return valid and pick == rendered.gold, valid, pick


def frequency_baseline(rendered: RenderedProbe) -> float:
    """Expected accuracy of 'pick the most frequently visible label' (ties uniform)."""
    counts = visible_counts(rendered.labels)
    if not counts:
        return 1.0 / len(rendered.probe.roster)
    top = max(counts.values())
    leaders = [s for s, c in counts.items() if c == top]
    return (1.0 / len(leaders)) if rendered.gold in leaders else 0.0


def turn_taking_baseline(rendered: RenderedProbe) -> float:
    """Expected accuracy of 'someone other than the neighbouring speakers' (uniform guess).

    Neighbours are the labels on the nearest visible turns before and after the
    target. Label-only like the frequency heuristic, so compression cannot touch
    it; on conversation windows it beats chance because the next turn usually
    belongs to someone else.
    """
    i = rendered.probe.target_index
    before = [label for label in rendered.labels[:i] if label != HIDDEN]
    after = [label for label in rendered.labels[i + 1:] if label != HIDDEN]
    neighbours = set(before[-1:] + after[:1])
    pool = [s for s in rendered.probe.roster if s not in neighbours] or list(rendered.probe.roster)
    return (rendered.gold in pool) / len(pool)


def _tfidf(text: str, idf: dict[str, float]) -> Counter:
    weights: Counter = Counter()
    for token in tokenize(text):
        weights[token] += idf.get(token, 0.0)
    return weights


def _cosine(a: Counter, b: Counter) -> float:
    norm = math.sqrt(sum(w * w for w in a.values())) * math.sqrt(sum(w * w for w in b.values()))
    return sum(w * b[t] for t, w in a.items()) / norm if norm else 0.0


def lexical_pick(rendered: RenderedProbe, idf: dict[str, float]) -> str:
    """Roster speaker whose visible messages are most TF-IDF-similar to the statement.

    A non-LLM attributor over exactly the (compressed) text the reader sees, so
    it has its own dose-response. Ties go to the earlier roster name, so a
    statement with no usable words scores like a random guess.
    """
    by_speaker: dict[str, list[str]] = defaultdict(list)
    for label, text in zip(rendered.labels, rendered.texts):
        if label != HIDDEN:
            by_speaker[label].append(text)
    target = _tfidf(rendered.target_text, idf)
    return max(rendered.probe.roster, key=lambda s: _cosine(target, _tfidf(" ".join(by_speaker[s]), idf)))


def check_probe(rendered: RenderedProbe) -> list[str]:
    """Invariants that must hold for every rendered probe. Empty list = OK."""
    problems = []
    p = rendered.probe
    if rendered.labels[p.target_index] != HIDDEN:
        problems.append("target label visible")
    if rendered.gold not in p.roster:
        problems.append("gold not on roster")
    if set(visible_counts(rendered.labels)) != set(p.roster):
        problems.append("roster != visible speakers")
    if rendered.gold not in visible_counts(rendered.labels):
        problems.append("gold not visible elsewhere (not bindable)")
    return problems


# --------------------------------------------------------------------------
# readers
# --------------------------------------------------------------------------

JSON_INSTRUCTION = '\nRespond as JSON: {"author": "<one candidate name>"}.'


@dataclass
class OllamaHTTPReader:
    """Deterministic reader: temperature 0, fixed seed, short output.

    With `choices`, decoding is constrained: Ollama structured output with the
    roster as a JSON-schema enum, so the reader can only name a roster member.
    Unconstrained, it invented an unseen participant (e.g. "User_4" for a roster
    of User_1..User_3) on 13% of rows, concentrated in 3 probes -- treating the
    hidden speaker as a new person, the opposite of binding. That is a reader
    finding, reported separately; for the forced-choice measurement the answer
    must be on the roster or 1/|roster| is not the floor.

    `num_ctx` is set explicitly and never left to the server. Ollama's default
    context is 4,096 tokens and it truncates a longer prompt silently, from the
    left -- which is where the instructions and the candidate roster are. AMI
    and ICSI never come close (1,759 and 936 estimated tokens at their longest),
    but on Supreme Court and ELITR windows a handful of probes run past 4,096,
    and a truncated probe would be scored as if the reader had seen it.
    """

    model: str = "qwen2.5:7b"
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: int = 180
    num_predict: int = 32
    num_ctx: int = 8192

    def answer(self, prompt: str, choices: Iterable[str] | None = None) -> str:
        client = OllamaClient(self.base_url, self.timeout_seconds)
        options = {"temperature": 0, "seed": 0,
                   "num_predict": self.num_predict, "num_ctx": self.num_ctx}
        names = list(choices) if choices else []
        if not names:
            return client.generate(self.model, prompt, options=options)
        schema = {"type": "object", "properties": {"author": {"type": "string", "enum": names}},
                  "required": ["author"]}
        text = client.generate(self.model, prompt + JSON_INSTRUCTION, options=options, format=schema)
        try:
            return str(json.loads(text).get("author", "")).strip()
        except (json.JSONDecodeError, AttributeError):
            return text  # surfaced as an invalid answer by grade(), never silently fixed


@dataclass
class StubReader:
    """Plumbing check only: always answers the first roster name. Not a result."""

    model: str = "stub"

    def answer(self, prompt: str, choices: Iterable[str] | None = None) -> str:  # noqa: ARG002
        names = list(choices) if choices else []
        return names[0] if names else ""
