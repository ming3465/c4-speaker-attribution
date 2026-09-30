from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "so",
    "that",
    "the",
    "then",
    "this",
    "to",
    "with",
}

STRATEGIES = (
    "uniform_compression",
    "speaker_partitioned_memory",
    "random_consumer_allocation",
    "a_mac_metadata_utility",
    "query_task_conditioned_compression",
    "recency_window",
    "oracle_future_consumer_allocation",
)


def load_labels(path: Path) -> list[dict[str, Any]]:
    labels: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                labels.append(json.loads(line))
    return labels


def tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if token.lower() not in STOPWORDS and len(token) > 2
    ]


def truncate_words(text: str, word_count: int) -> str:
    words = text.split()
    return " ".join(words[:word_count])


def residual_words(text: str, core_word_count: int, residual_word_count: int) -> str:
    words = text.split()
    return " ".join(words[core_word_count : core_word_count + residual_word_count])


def answer_coverage(answer: str, visible_text: str) -> float:
    answer_tokens = set(tokenize(answer))
    if not answer_tokens:
        return 0.0
    visible_tokens = set(tokenize(visible_text))
    return len(answer_tokens & visible_tokens) / len(answer_tokens)


def visible_memory_text(
    label: dict[str, Any],
    *,
    strategy: str,
    shared_core_tokens: int,
    residual_tokens: int,
) -> tuple[str, int]:
    asker = label["question_asker"]
    future_consumers = set(label.get("future_consumer_ids") or [])
    visible_parts: list[str] = []
    stored_word_count = 0
    candidate_evidence = label.get("candidate_evidence") or []
    newest_evidence_id = None
    if candidate_evidence:
        newest = candidate_evidence[-1]
        if isinstance(newest, dict):
            newest_evidence_id = newest.get("msg_node")

    for evidence in label.get("candidate_evidence") or []:
        if not isinstance(evidence, dict):
            continue
        content = str(evidence.get("content", ""))
        author = str(evidence.get("author", ""))
        message_id = evidence.get("msg_node")
        is_decision_point = evidence.get("decision_type") in {"original", "changed"}

        core = truncate_words(content, shared_core_tokens)
        residual = residual_words(content, shared_core_tokens, residual_tokens)
        visible_parts.append(core)
        stored_word_count += len(core.split())

        if strategy == "uniform_compression":
            continue

        keeps_residual = False
        if strategy == "speaker_partitioned_memory" and author == asker:
            keeps_residual = True
        elif strategy == "random_consumer_allocation" and _stable_random_match(
            label["label_id"], asker
        ):
            keeps_residual = True
        elif strategy == "a_mac_metadata_utility" and is_decision_point:
            keeps_residual = True
        elif strategy == "query_task_conditioned_compression" and _topic_overlap(
            label, content
        ):
            keeps_residual = True
        elif strategy == "recency_window" and message_id == newest_evidence_id:
            keeps_residual = True
        elif strategy == "oracle_future_consumer_allocation" and asker in future_consumers:
            keeps_residual = True

        if strategy != "uniform_compression" and keeps_residual:
            stored_word_count += len(residual.split())
            visible_parts.append(residual)

    return "\n".join(part for part in visible_parts if part), stored_word_count


def _stable_random_match(label_id: str, asker: str) -> bool:
    value = sum(ord(char) for char in f"{label_id}:{asker}")
    return value % 3 == 0


def _topic_overlap(label: dict[str, Any], content: str) -> bool:
    query_text = " ".join(
        str(label.get(field, ""))
        for field in ("topic", "phase_name", "question_type", "answer")
    )
    query_tokens = set(tokenize(query_text))
    content_tokens = set(tokenize(content))
    return len(query_tokens & content_tokens) >= 3


def score_labels(
    labels: list[dict[str, Any]],
    *,
    shared_core_tokens: int,
    residual_tokens: int,
    success_threshold: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summary: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for label in labels:
        for strategy in STRATEGIES:
            visible_text, stored_word_count = visible_memory_text(
                label,
                strategy=strategy,
                shared_core_tokens=shared_core_tokens,
                residual_tokens=residual_tokens,
            )
            coverage = answer_coverage(str(label.get("answer", "")), visible_text)
            success = coverage >= success_threshold
            row = {
                "label_id": label["label_id"],
                "question_id": label["question_id"],
                "strategy": strategy,
                "question_asker": label["question_asker"],
                "question_asker_role": label["question_asker_role"],
                "question_type": label["question_type"],
                "requires_update": label.get("requires_update"),
                "requires_multi_hop": label.get("requires_multi_hop"),
                "stored_word_count": stored_word_count,
                "answer_coverage": round(coverage, 4),
                "formation_success": success,
            }
            rows.append(row)

            bucket = summary[strategy]
            bucket["rows"] += 1
            bucket["stored_word_count"] += stored_word_count
            bucket["answer_coverage"] += coverage
            bucket["formation_success"] += int(success)

    final_summary: dict[str, Any] = {}
    for strategy, values in summary.items():
        rows_count = max(values["rows"], 1)
        final_summary[strategy] = {
            "rows": int(values["rows"]),
            "avg_stored_word_count": round(
                values["stored_word_count"] / rows_count, 2
            ),
            "avg_answer_coverage": round(values["answer_coverage"] / rows_count, 4),
            "formation_success_rate": round(
                values["formation_success"] / rows_count, 4
            ),
        }

    return rows, final_summary


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
