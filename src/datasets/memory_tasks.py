"""Adapters that map memory benchmarks onto the common (unit, question) schema
used by `src.evaluation.failure_decomposition`.

GroupMemBench conversations ship without question sets; the typed questions
live in the code repo (UCSB-NLP-Chang/GroupMemBench) and carry no evidence
pointers. Gold evidence for the 214 Finance questions is recovered by
`toddzheng024/groupmembench-agent-sessions` and merged in here.
See docs/DATASET_AUDIT.md for provenance and quality caveats.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.evaluation.failure_decomposition import MemoryQuestion, MemoryUnit

QUESTION_TYPES = (
    "multi_hop",
    "knowledge_update",
    "temporal",
    "term_ambiguity",
    "user_implicit",
    "abstention",
)

LOCOMO_CATEGORIES = {
    1: "multi_hop",
    2: "temporal",
    3: "open_domain",
    4: "single_hop",
    5: "adversarial",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def load_groupmembench(
    conversation_file: Path,
    questions_dir: Path,
    evidence_file: Path | None = None,
    *,
    require_evidence: bool = True,
) -> tuple[list[MemoryUnit], list[MemoryQuestion]]:
    data = json.loads(conversation_file.read_text(encoding="utf-8"))
    units: list[MemoryUnit] = []
    order = 0
    for channel, messages in data.items():
        for message in messages:
            units.append(
                MemoryUnit(
                    uid=str(message["msg_node"]),
                    group=channel,
                    text=str(message.get("content", "")),
                    author=str(message.get("author", "")),
                    role=str(message.get("role", "")),
                    order=order,
                    meta={
                        "is_noise": bool(message.get("is_noise")),
                        "is_decision_point": bool(message.get("is_decision_point")),
                        "timestamp": message.get("timestamp"),
                        "topic": message.get("topic"),
                    },
                )
            )
            order += 1

    evidence: dict[str, list[str]] = {}
    if evidence_file is not None and evidence_file.exists():
        for row in read_jsonl(evidence_file):
            evidence[str(row["id"])] = [str(x) for x in row.get("evidence_msg_ids") or []]

    questions: list[MemoryQuestion] = []
    for question_type in QUESTION_TYPES:
        path = questions_dir / f"{question_type}.jsonl"
        if not path.exists():
            continue
        for row in read_jsonl(path):
            uids = tuple(evidence.get(str(row["id"]), ()))
            if require_evidence and not uids:
                continue
            questions.append(
                MemoryQuestion(
                    qid=str(row["id"]),
                    category=question_type,
                    question=str(row["question"]),
                    answer=str(row["answer"]),
                    asker=str(row.get("asking_user_id", "")),
                    evidence_uids=uids,
                )
            )
    return units, questions


def load_locomo(path: Path) -> tuple[list[MemoryUnit], list[MemoryQuestion]]:
    samples = json.loads(path.read_text(encoding="utf-8"))
    units: list[MemoryUnit] = []
    questions: list[MemoryQuestion] = []
    order = 0
    for sample in samples:
        sample_id = str(sample["sample_id"])
        conversation = sample["conversation"]
        for key in sorted(
            (k for k in conversation if k.startswith("session_") and "date" not in k),
            key=lambda k: int(k.split("_")[1]),
        ):
            for turn in conversation[key]:
                units.append(
                    MemoryUnit(
                        uid=f"{sample_id}|{turn['dia_id']}",
                        group=sample_id,
                        text=str(turn.get("text", "")),
                        author=str(turn.get("speaker", "")),
                        role=str(turn.get("speaker", "")),
                        order=order,
                        meta={"session": key},
                    )
                )
                order += 1
        known = {unit.uid for unit in units if unit.group == sample_id}
        for index, qa in enumerate(sample.get("qa", [])):
            uids = tuple(
                f"{sample_id}|{e}"
                for e in qa.get("evidence") or ()
                if f"{sample_id}|{e}" in known
            )
            if not uids:
                continue
            questions.append(
                MemoryQuestion(
                    qid=f"{sample_id}|q{index}",
                    category=LOCOMO_CATEGORIES.get(qa.get("category"), "unknown"),
                    question=str(qa["question"]),
                    answer=str(qa.get("answer", qa.get("adversarial_answer", ""))),
                    asker="",
                    evidence_uids=uids,
                )
            )
    return units, questions


def load_pilot_bundle(
    bundle_dir: Path, corpus_name: str = "corpus_10pct.jsonl"
) -> tuple[list[MemoryUnit], list[MemoryQuestion]]:
    """Load the self-contained Contribution 4 pilot bundle.

    Needs none of the 48 MB raw files — everything comes from `data/pilot/c4/`.
    Pass `corpus_name="evidence_messages.jsonl"` for an evidence-only smoke test,
    or point it at a full-corpus export to reproduce the reported numbers.
    """
    units = [
        MemoryUnit(
            uid=str(row["msg_node"]),
            group=str(row["channel"]),
            text=str(row.get("content", "")),
            author=str(row.get("author", "")),
            role=str(row.get("role", "")),
            order=index,
            meta={
                "is_noise": bool(row.get("is_noise")),
                "is_decision_point": bool(row.get("is_decision_point")),
                "timestamp": row.get("timestamp"),
                "topic": row.get("topic"),
            },
        )
        for index, row in enumerate(read_jsonl(bundle_dir / corpus_name))
    ]
    known = {unit.uid for unit in units}
    questions = [
        MemoryQuestion(
            qid=str(row["qid"]),
            category=str(row["category"]),
            question=str(row["question"]),
            answer=str(row["answer"]),
            asker=str(row.get("asking_user_id", "")),
            evidence_uids=tuple(u for u in row["evidence_msg_ids"] if u in known),
        )
        for row in read_jsonl(bundle_dir / "questions.jsonl")
    ]
    return units, [q for q in questions if q.evidence_uids]
