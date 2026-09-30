"""Reader pass: split C4's `answer_visible` bucket (Contribution 4, completion).

STATUS: PILOT (C4 v0 reader pass over the original failure decomposition, which WhenLoss published first); C4 v1 still imports build_reader_items. See docs/C4_RUNBOOK.md, 'Code status'.

C4 sorts every question into three buckets, and the third one is not an outcome:
`answer_visible` means the evidence survived compression AND was retrieved. It
says nothing about whether the model then read it correctly. Until that bucket
is split, Table 3 measures two failure modes out of three, and C3 has no target
metric at all -- `retrieved_but_misinterpreted` is the only bucket that supports
the provenance-conditioned interpretation claim.

This module asks a reader model each `answer_visible` question with its
retrieved snippets attached, grades the answer against gold, and splits:

    answer_visible -> correct
                   -> retrieved_but_misinterpreted

Backends follow the repo's Phase 0 convention (`src/evaluation/llm_pilot.py`):
shell out to a local CLI rather than holding an API key in the codebase.

    StubReader   offline, deterministic, no credits. Validates the plumbing --
                 it is NOT a result. It answers by copying the snippets, so it
                 can only ever confirm the pipeline runs end to end.
    CodexReader  the real reader, via the `codex` CLI already used by Phase 0.

Grading defaults to the same lexical criterion C4 uses everywhere else, so the
new bucket is consistent with the three that already exist. `--judge codex`
swaps in an LLM judge when lexical grading is too blunt.
"""
from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from src.evaluation.failure_decomposition import (
    BM25Index,
    MemoryQuestion,
    MemoryUnit,
    answer_support,
    answer_tokens,
    build_store,
    corpus_idf,
    decompose_question,
    salience_order,
)

NOT_ENOUGH = "NOT_ENOUGH_INFORMATION"

# `ollama run` emits terminal control sequences (cursor moves, line erases) as
# it streams. They survive into stdout and corrupt the graded answer text.
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\[[0-9]+[A-Z]\[K")


def clean_output(text: str) -> str:
    return ANSI_RE.sub("", text).strip()


# --------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------

@dataclass
class ReaderItem:
    """One `answer_visible` question, with what the reader actually gets to see.

    `hide_provenance` and `shown_asker` are the two knobs of the provenance
    ablation. They change ONLY what the reader is told about people -- the
    question, the evidence text, and the retrieval result are byte-identical
    across all four conditions, so any score difference is attributable to
    identity information alone.
    """

    qid: str
    category: str
    question: str
    gold_answer: str
    asker: str
    snippets: list[dict[str, str]] = field(default_factory=list)
    hide_provenance: bool = False
    shown_asker: str | None = None

    def visible_snippets(self) -> list[dict[str, str]]:
        """Evidence text is never altered; only the speaker/role fields drop."""
        if not self.hide_provenance:
            return self.snippets
        return [{"text": s["text"]} for s in self.snippets]

    def prompt(self) -> str:
        """Mirrors llm_pilot.answer_prompt so Phase 0 and this stay comparable."""
        snippets_json = json.dumps(self.visible_snippets(), ensure_ascii=False, indent=2)
        asker_line = self.asker if self.shown_asker is None else self.shown_asker
        if self.hide_provenance and self.shown_asker == "":
            # both halves ablated: the reader is told nothing about anyone
            return f"""You are answering a memory question from retrieved conversation snippets.

Rules:
- Use only the provided snippets.
- If the snippets do not contain enough information to answer, reply exactly: {NOT_ENOUGH}.
- Do not mention that you are an AI or discuss the evaluation.
- Return only the answer, with no markdown.

Question:
{self.question}

Retrieved snippets:
{snippets_json}
"""
        return f"""You are answering a memory question from retrieved conversation snippets.

Rules:
- Use only the provided snippets.
- If the snippets do not contain enough information to answer, reply exactly: {NOT_ENOUGH}.
- Do not mention that you are an AI or discuss the evaluation.
- Return only the answer, with no markdown.

Question:
{self.question}

Question asker:
{asker_line}

Retrieved snippets:
{snippets_json}
"""


def build_reader_items(
    units: list[MemoryUnit],
    questions: list[MemoryQuestion],
    *,
    policy: str,
    budget: float,
    top_k: int = 5,
    tau: float = 0.65,
    core_share: float = 0.5,
    compressor: str = "salient",
    hide_provenance: bool = False,
    swap_asker: bool = False,
    swap_seed: int = 0,
    all_questions: bool = False,
) -> list[ReaderItem]:
    """Rebuild the store for one (policy, budget) and collect its answer_visible
    questions together with the snippets BM25 actually returned.

    The decomposition CSV only stores bucket labels, not text, so the store has
    to be rebuilt here rather than read back. Rebuilt exactly as
    run_failure_decomposition does it, or the buckets would not line up.
    """
    idf = corpus_idf(units)
    salience = {unit.uid: salience_order(unit.text, idf) for unit in units}

    by_group: dict[str, list[MemoryUnit]] = defaultdict(list)
    for unit in units:
        by_group[unit.group].append(unit)

    consumers: dict[str, set[str]] = defaultdict(set)
    for question in questions:
        for uid in question.evidence_uids:
            consumers[uid].add(question.asker)

    # Same eligibility gate the C4 runner applies: grade only questions whose
    # answer is recoverable at full fidelity.
    full = {unit.uid: unit.text for unit in units}
    full_index = BM25Index(full)
    eligible = {
        q.qid
        for q in questions
        if decompose_question(q, full, full_index, top_k=top_k, tau=tau)["bucket"]
        != "lost_at_write"
    }
    graded = [q for q in questions if q.qid in eligible]

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
    index = BM25Index(stored)

    units_by_uid = {unit.uid: unit for unit in units}
    items: list[ReaderItem] = []
    for question in graded:
        row = decompose_question(question, stored, index, top_k=top_k, tau=tau)
        # The reader pass wants only answer_visible. The attribution probe wants
        # every graded question: whether the memory question was answerable is
        # irrelevant to whether a retrieved snippet can be attributed, and
        # filtering would bias the sample toward well-preserved evidence.
        if not all_questions and row["bucket"] != "answer_visible":
            continue
        retrieved = index.search(question.question, top_k)
        snippets = []
        for uid in retrieved:
            unit = units_by_uid.get(uid)
            snippets.append(
                {
                    "text": stored.get(uid, ""),
                    "speaker": unit.author if unit else "",
                    "role": unit.role if unit else "",
                }
            )
        items.append(
            ReaderItem(
                qid=question.qid,
                category=question.category,
                question=question.question,
                gold_answer=question.answer,
                asker=question.asker,
                snippets=snippets,
                hide_provenance=hide_provenance,
            )
        )

    if swap_asker:
        # Deterministically reassign each question to a DIFFERENT participant.
        # Not random noise: a real other person from the same conversation, so
        # the prompt stays plausible and only the identity is wrong.
        roster = sorted({q.asker for q in questions})
        rng = random.Random(swap_seed)
        for item in items:
            others = [a for a in roster if a != item.asker]
            item.shown_asker = rng.choice(others) if others else item.asker

    return items


# --------------------------------------------------------------------------
# backends
# --------------------------------------------------------------------------

class ReaderBackend(Protocol):
    name: str

    def answer(self, item: ReaderItem) -> str: ...


@dataclass
class StubReader:
    """Offline plumbing check. Produces no scientific claim.

    Concatenates the retrieved snippets and returns them as the "answer", so
    lexical grading marks an item correct exactly when the answer tokens are
    present in what was retrieved. That reproduces C4's own criterion by
    construction -- it verifies the pipeline runs, nothing more. Any number it
    produces must be labelled as a plumbing test, never reported as a result.
    """

    name: str = "stub"

    def answer(self, item: ReaderItem) -> str:
        return " ".join(s["text"] for s in item.snippets)[:2000] or NOT_ENOUGH


@dataclass
class OllamaReader:
    """Local reader via `ollama`. No account, no API key, no credits.

    Needs `ollama serve` running and the model pulled. Quality depends entirely
    on the local model -- fine for validating the split end to end, and worth
    reporting only if the model is strong enough to judge honestly.
    """

    model: str = "llama3.1:8b"
    timeout_seconds: int = 120
    name: str = "ollama"

    def answer(self, item: ReaderItem) -> str:
        import subprocess

        result = subprocess.run(
            ["ollama", "run", self.model],
            input=item.prompt(),
            text=True,
            capture_output=True,
            check=True,
            timeout=self.timeout_seconds,
        )
        return clean_output(result.stdout)


@dataclass
class CommandReader:
    """Escape hatch: any CLI that takes the prompt on stdin and prints the answer.

    Lets the reader point at Azure, a local server, or anything else through a
    one-line wrapper script, without this module knowing about the provider or
    ever handling a credential.

        --backend command --command "./my_azure_wrapper.sh"
    """

    command: str
    timeout_seconds: int = 120
    name: str = "command"

    def answer(self, item: ReaderItem) -> str:
        import shlex
        import subprocess

        result = subprocess.run(
            shlex.split(self.command),
            input=item.prompt(),
            text=True,
            capture_output=True,
            check=True,
            timeout=self.timeout_seconds,
        )
        return clean_output(result.stdout)


@dataclass
class CodexReader:
    """The real reader, via the `codex` CLI Phase 0 already uses."""

    codex_path: Path
    model: str
    cwd: Path
    timeout_seconds: int = 120
    name: str = "codex"

    def answer(self, item: ReaderItem) -> str:
        from src.evaluation.llm_pilot import run_codex_exec

        return run_codex_exec(
            codex_path=self.codex_path,
            model=self.model,
            cwd=self.cwd,
            prompt=item.prompt(),
            timeout_seconds=self.timeout_seconds,
        )


# --------------------------------------------------------------------------
# grading
# --------------------------------------------------------------------------

def judge_lexical(gold_answer: str, model_answer: str, *, tau: float = 0.65) -> bool:
    """Same criterion C4 uses for every other bucket, applied to the answer.

    Keeps the fourth bucket commensurable with the three that already exist. It
    is blunt: an answer that quotes the right words while drawing the wrong
    conclusion is scored correct, which biases `retrieved_but_misinterpreted`
    downward. Use the LLM judge when that distinction is the point.
    """
    if not model_answer or model_answer.strip() == NOT_ENOUGH:
        return False
    return answer_support(answer_tokens(gold_answer), model_answer) >= tau


def run_reader_pass(
    items: Iterable[ReaderItem],
    backend: ReaderBackend,
    *,
    judge: Callable[[str, str], bool] = judge_lexical,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[dict[str, Any]]:
    items = list(items)
    rows: list[dict[str, Any]] = []
    for position, item in enumerate(items, start=1):
        try:
            model_answer = backend.answer(item)
            error = ""
        except Exception as exc:  # noqa: BLE001 - surfaced per row, never silent
            model_answer, error = "", f"{type(exc).__name__}: {exc}"

        correct = judge(item.gold_answer, model_answer) if not error else False
        rows.append(
            {
                "qid": item.qid,
                "category": item.category,
                "gold_answer": item.gold_answer,
                "model_answer": model_answer,
                "bucket": "correct" if correct else "retrieved_but_misinterpreted",
                "error": error,
            }
        )
        if on_progress:
            on_progress(position, len(items))
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Split counts overall and per question category."""
    total = len(rows)
    correct = sum(r["bucket"] == "correct" for r in rows)
    errors = sum(bool(r["error"]) for r in rows)

    by_category: dict[str, dict[str, int]] = defaultdict(
        lambda: {"correct": 0, "retrieved_but_misinterpreted": 0}
    )
    for row in rows:
        by_category[row["category"]][row["bucket"]] += 1

    return {
        "answer_visible_items": total,
        "correct": correct,
        "retrieved_but_misinterpreted": total - correct,
        "correct_share": round(correct / total, 4) if total else 0.0,
        "errors": errors,
        "by_category": {k: dict(v) for k, v in sorted(by_category.items())},
    }
