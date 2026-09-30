#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.groupmembench import iter_messages, load_domain_file  # noqa: E402


MENTION_RE = re.compile(r"@?(User_\d+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create bootstrap oracle labels from decision-change metadata."
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=ROOT
        / "data"
        / "processed"
        / "groupmembench"
        / "oracle_label_template.jsonl",
        help="Oracle label template JSONL.",
    )
    parser.add_argument(
        "--raw-domain-file",
        type=Path,
        default=ROOT
        / "data"
        / "raw"
        / "groupmembench"
        / "synthetic_domain_channels_rolevariants_Finance.json",
        help="Raw GroupMemBench domain JSON for role lookup.",
    )
    parser.add_argument("--domain", default="Finance", help="GroupMemBench domain.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "data"
        / "processed"
        / "groupmembench"
        / "oracle_labels.bootstrap.jsonl",
        help="Output bootstrap oracle label JSONL.",
    )
    parser.add_argument("--limit", type=int, default=10, help="Maximum rows to emit.")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def most_common_roles(raw_domain_file: Path, domain: str) -> dict[str, str]:
    data = load_domain_file(raw_domain_file)
    records = iter_messages(data, domain=domain)
    role_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        role_counts[record.author][record.role] += 1
    return {
        author: counter.most_common(1)[0][0]
        for author, counter in role_counts.items()
        if counter
    }


def mentions_from_row(row: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for evidence in row.get("candidate_evidence") or []:
        if isinstance(evidence, dict):
            texts.append(str(evidence.get("content", "")))
    metadata = row.get("decision_change_metadata") or {}
    for key in ("changed_to", "proposed_alternative", "triggering_event"):
        texts.append(str(metadata.get(key, "")))

    seen: set[str] = set()
    mentions: list[str] = []
    for text in texts:
        for match in MENTION_RE.findall(text):
            if match not in seen:
                seen.add(match)
                mentions.append(match)
    return mentions


def evidence_authors(row: dict[str, Any]) -> tuple[list[str], list[str]]:
    speakers: list[str] = []
    roles: list[str] = []
    for evidence in row.get("candidate_evidence") or []:
        if not isinstance(evidence, dict):
            continue
        speaker = evidence.get("author")
        role = evidence.get("role")
        if speaker and speaker not in speakers:
            speakers.append(str(speaker))
        if role and role not in roles:
            roles.append(str(role))
    return speakers, roles


def make_bootstrap_labels(
    rows: list[dict[str, Any]],
    role_by_author: dict[str, str],
    limit: int,
) -> list[dict[str, Any]]:
    labels: list[dict[str, Any]] = []
    for row in rows:
        metadata = row.get("decision_change_metadata") or {}
        proposed_alternative = metadata.get("proposed_alternative")
        if not proposed_alternative:
            continue

        future_consumers = mentions_from_row(row)
        if not future_consumers:
            continue

        future_consumer_roles = [
            role_by_author.get(consumer, "unknown") for consumer in future_consumers
        ]
        source_speakers, source_roles = evidence_authors(row)
        question_asker = future_consumers[0]

        label = dict(row)
        label.update(
            {
                "question_id": f"{row['label_id']}_Q",
                "question_type": "knowledge_update",
                "question_asker": question_asker,
                "question_asker_role": role_by_author.get(question_asker, "unknown"),
                "answer": proposed_alternative,
                "future_consumer_ids": future_consumers,
                "future_consumer_roles": future_consumer_roles,
                "source_speakers": source_speakers,
                "source_roles": source_roles,
                "requires_provenance": False,
                "requires_update": True,
                "requires_multi_hop": len(row.get("evidence_message_ids") or []) > 1,
                "notes": (
                    "Bootstrap label generated from decision-change metadata; "
                    "not an official GroupMemBench question row."
                ),
            }
        )
        labels.append(label)
        if len(labels) >= limit:
            break
    return labels


def main() -> None:
    args = parse_args()
    role_by_author = most_common_roles(args.raw_domain_file, args.domain)
    rows = read_jsonl(args.template)
    labels = make_bootstrap_labels(rows, role_by_author, args.limit)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        for label in labels:
            file.write(json.dumps(label, ensure_ascii=False) + "\n")
    print(f"Wrote {len(labels)} bootstrap oracle labels to {args.output}")


if __name__ == "__main__":
    main()
