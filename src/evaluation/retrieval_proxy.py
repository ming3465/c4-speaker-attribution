from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.datasets.groupmembench import MessageRecord, iter_messages, load_domain_file
from src.evaluation.proxy_allocation import (
    STRATEGIES,
    _stable_random_match,
    _topic_overlap,
    answer_coverage,
    residual_words,
    tokenize,
    truncate_words,
)


@dataclass(frozen=True)
class IndexedMessage:
    msg_node: str
    author: str
    role: str
    channel: str
    visible_text: str
    stored_word_count: int
    tokens: Counter[str]


def load_labels(path: Path) -> list[dict[str, Any]]:
    labels: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                labels.append(json.loads(line))
    return labels


def synthetic_query(label: dict[str, Any]) -> str:
    metadata = label.get("decision_change_metadata") or {}
    trigger = metadata.get("triggering_event") or metadata.get("change_reason") or ""
    topic = label.get("topic") or ""
    phase = label.get("phase_name") or ""
    asker = label.get("question_asker") or ""
    return (
        f"What is the current updated decision for {topic} during {phase}? "
        f"Question asker: {asker}. Context: {trigger}"
    )


def strategy_visible_text(
    record: MessageRecord,
    label: dict[str, Any],
    *,
    strategy: str,
    shared_core_tokens: int,
    residual_tokens: int,
) -> tuple[str, int]:
    content = record.content
    core = truncate_words(content, shared_core_tokens)
    residual = residual_words(content, shared_core_tokens, residual_tokens)
    stored_word_count = len(core.split())
    visible_parts = [core]

    if strategy == "uniform_compression":
        return "\n".join(visible_parts), stored_word_count

    keeps_residual = False
    if strategy == "speaker_partitioned_memory":
        keeps_residual = record.author == label.get("question_asker")
    elif strategy == "random_consumer_allocation":
        keeps_residual = _stable_random_match(
            str(label.get("label_id", "")), str(label.get("question_asker", ""))
        )
    elif strategy == "a_mac_metadata_utility":
        keeps_residual = bool(record.is_decision_point)
    elif strategy == "query_task_conditioned_compression":
        keeps_residual = _topic_overlap(label, content)
    elif strategy == "recency_window":
        label_time = max(
            (
                str(evidence.get("timestamp", ""))
                for evidence in label.get("candidate_evidence") or []
                if isinstance(evidence, dict)
            ),
            default="",
        )
        keeps_residual = record.timestamp >= label_time
    elif strategy == "oracle_future_consumer_allocation":
        evidence_ids = set(label.get("evidence_message_ids") or [])
        future_consumers = set(label.get("future_consumer_ids") or [])
        keeps_residual = (
            record.msg_node in evidence_ids
            and label.get("question_asker") in future_consumers
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    if keeps_residual:
        stored_word_count += len(residual.split())
        visible_parts.append(residual)

    return "\n".join(part for part in visible_parts if part), stored_word_count


def build_index(
    records: list[MessageRecord],
    label: dict[str, Any],
    *,
    strategy: str,
    shared_core_tokens: int,
    residual_tokens: int,
) -> list[IndexedMessage]:
    indexed: list[IndexedMessage] = []
    for record in records:
        if record.channel != label.get("channel"):
            continue
        visible_text, stored_word_count = strategy_visible_text(
            record,
            label,
            strategy=strategy,
            shared_core_tokens=shared_core_tokens,
            residual_tokens=residual_tokens,
        )
        indexed.append(
            IndexedMessage(
                msg_node=record.msg_node,
                author=record.author,
                role=record.role,
                channel=record.channel,
                visible_text=visible_text,
                stored_word_count=stored_word_count,
                tokens=Counter(tokenize(visible_text)),
            )
        )
    return indexed


def idf_by_token(indexed: list[IndexedMessage]) -> dict[str, float]:
    document_frequency: Counter[str] = Counter()
    for message in indexed:
        document_frequency.update(message.tokens.keys())
    document_count = len(indexed)
    return {
        token: math.log((document_count + 1) / (frequency + 1)) + 1.0
        for token, frequency in document_frequency.items()
    }


def retrieve(
    indexed: list[IndexedMessage],
    query: str,
    *,
    top_k: int,
) -> list[tuple[float, IndexedMessage]]:
    query_tokens = Counter(tokenize(query))
    idf = idf_by_token(indexed)
    scored: list[tuple[float, IndexedMessage]] = []
    for message in indexed:
        score = 0.0
        for token, query_count in query_tokens.items():
            if token in message.tokens:
                score += query_count * message.tokens[token] * idf.get(token, 1.0)
        if message.tokens:
            score = score / math.sqrt(sum(message.tokens.values()))
        scored.append((score, message))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:top_k]


def score_retrieval(
    *,
    raw_domain_file: Path,
    domain: str,
    labels: list[dict[str, Any]],
    shared_core_tokens: int,
    residual_tokens: int,
    top_k: int,
    success_threshold: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = load_domain_file(raw_domain_file)
    records = iter_messages(data, domain=domain)
    rows: list[dict[str, Any]] = []
    summary: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for label in labels:
        evidence_ids = set(label.get("evidence_message_ids") or [])
        query = synthetic_query(label)
        for strategy in STRATEGIES:
            indexed = build_index(
                records,
                label,
                strategy=strategy,
                shared_core_tokens=shared_core_tokens,
                residual_tokens=residual_tokens,
            )
            retrieved = retrieve(indexed, query, top_k=top_k)
            retrieved_ids = [message.msg_node for _, message in retrieved]
            retrieved_text = "\n".join(message.visible_text for _, message in retrieved)
            evidence_retrieved = bool(evidence_ids & set(retrieved_ids))
            coverage = answer_coverage(str(label.get("answer", "")), retrieved_text)
            success = evidence_retrieved and coverage >= success_threshold
            indexed_word_count = sum(message.stored_word_count for message in indexed)
            row = {
                "label_id": label["label_id"],
                "question_id": label["question_id"],
                "strategy": strategy,
                "question_asker": label["question_asker"],
                "question_asker_role": label["question_asker_role"],
                "channel": label["channel"],
                "top_k": top_k,
                "evidence_retrieved": evidence_retrieved,
                "retrieved_ids": " ".join(retrieved_ids),
                "answer_coverage": round(coverage, 4),
                "retrieval_visible_success": success,
                "indexed_word_count": indexed_word_count,
            }
            rows.append(row)

            bucket = summary[strategy]
            bucket["rows"] += 1
            bucket["evidence_retrieved"] += int(evidence_retrieved)
            bucket["answer_coverage"] += coverage
            bucket["retrieval_visible_success"] += int(success)
            bucket["indexed_word_count"] += indexed_word_count

    final_summary: dict[str, Any] = {}
    for strategy, values in summary.items():
        rows_count = max(values["rows"], 1)
        final_summary[strategy] = {
            "rows": int(values["rows"]),
            "recall_at_k": round(values["evidence_retrieved"] / rows_count, 4),
            "avg_answer_coverage_in_top_k": round(
                values["answer_coverage"] / rows_count, 4
            ),
            "retrieval_visible_success_rate": round(
                values["retrieval_visible_success"] / rows_count, 4
            ),
            "avg_indexed_word_count": round(
                values["indexed_word_count"] / rows_count, 2
            ),
        }
    return rows, final_summary


def raw_domain_file(raw_dir: Path, domain: str) -> Path:
    return raw_dir / f"synthetic_domain_channels_rolevariants_{domain}.json"


def score_retrieval_multi_domain(
    *,
    raw_dir: Path,
    labels: list[dict[str, Any]],
    shared_core_tokens: int,
    residual_tokens: int,
    top_k: int,
    success_threshold: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    labels_by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for label in labels:
        labels_by_domain[str(label.get("domain", ""))].append(label)

    rows: list[dict[str, Any]] = []
    for domain, domain_labels in sorted(labels_by_domain.items()):
        domain_rows, _ = score_retrieval(
            raw_domain_file=raw_domain_file(raw_dir, domain),
            domain=domain,
            labels=domain_labels,
            shared_core_tokens=shared_core_tokens,
            residual_tokens=residual_tokens,
            top_k=top_k,
            success_threshold=success_threshold,
        )
        rows.extend(domain_rows)

    return rows, summarize_rows(rows)


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        strategy = row["strategy"]
        bucket = summary[strategy]
        bucket["rows"] += 1
        bucket["evidence_retrieved"] += int(bool(row["evidence_retrieved"]))
        bucket["answer_coverage"] += float(row["answer_coverage"])
        bucket["retrieval_visible_success"] += int(
            bool(row["retrieval_visible_success"])
        )
        bucket["indexed_word_count"] += int(row["indexed_word_count"])

    final_summary: dict[str, Any] = {}
    for strategy, values in summary.items():
        rows_count = max(values["rows"], 1)
        final_summary[strategy] = {
            "rows": int(values["rows"]),
            "recall_at_k": round(values["evidence_retrieved"] / rows_count, 4),
            "avg_answer_coverage_in_top_k": round(
                values["answer_coverage"] / rows_count, 4
            ),
            "retrieval_visible_success_rate": round(
                values["retrieval_visible_success"] / rows_count, 4
            ),
            "avg_indexed_word_count": round(
                values["indexed_word_count"] / rows_count, 2
            ),
        }
    return final_summary


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
