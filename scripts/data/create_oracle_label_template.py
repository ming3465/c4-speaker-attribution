#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.groupmembench import iter_messages, load_domain_file  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a manual oracle-label template from GroupMemBench messages."
    )
    parser.add_argument("--domain", default="Finance", help="GroupMemBench domain.")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT
        / "data"
        / "raw"
        / "groupmembench"
        / "synthetic_domain_channels_rolevariants_Finance.json",
        help="Local GroupMemBench domain JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "data"
        / "processed"
        / "groupmembench"
        / "oracle_label_template.jsonl",
        help="Output JSONL template for manual labeling.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum number of candidate rows to emit.",
    )
    parser.add_argument(
        "--mode",
        choices=("decision_changes", "decision_points"),
        default="decision_changes",
        help="Candidate type to export.",
    )
    return parser.parse_args()


def compact_message(message: dict[str, Any] | None) -> dict[str, Any] | None:
    if not message:
        return None
    return {
        "msg_node": message.get("msg_node"),
        "author": message.get("author"),
        "role": message.get("role"),
        "timestamp": message.get("timestamp"),
        "reply_to": message.get("reply_to"),
        "topic": message.get("topic"),
        "phase_name": message.get("phase_name"),
        "decision_type": message.get("decision_type"),
        "content": message.get("content"),
    }


def make_template_rows(
    *,
    data: dict[str, list[dict[str, Any]]],
    domain: str,
    mode: str,
    limit: int,
) -> list[dict[str, Any]]:
    records = iter_messages(data, domain=domain)
    raw_by_id = {record.msg_node: record.raw for record in records}
    rows: list[dict[str, Any]] = []

    for record in records:
        decision_label = record.raw.get("decision_label") or {}
        change_metadata = record.raw.get("decision_change_metadata") or {}
        if mode == "decision_changes" and not change_metadata:
            continue
        if mode == "decision_points" and not record.is_decision_point:
            continue

        linked_id = decision_label.get("linked_to_msg")
        evidence_ids = [record.msg_node]
        if linked_id:
            evidence_ids.insert(0, linked_id)

        row = {
            "label_id": f"{domain}_{len(rows) + 1:04d}",
            "domain": domain,
            "channel": record.channel,
            "question_id": "",
            "question_type": "knowledge_update"
            if change_metadata
            else "",
            "question_asker": "",
            "question_asker_role": "",
            "answer": "",
            "evidence_message_ids": evidence_ids,
            "future_consumer_ids": [],
            "future_consumer_roles": [],
            "source_speakers": [record.author],
            "source_roles": [record.role],
            "topic": record.topic,
            "phase_name": record.phase_name,
            "requires_provenance": False,
            "requires_update": bool(change_metadata),
            "requires_multi_hop": len(evidence_ids) > 1,
            "candidate_evidence": [
                compact_message(raw_by_id.get(evidence_id))
                for evidence_id in evidence_ids
            ],
            "decision_change_metadata": change_metadata or None,
            "notes": "Fill question_id, asker, answer, and future consumers manually.",
        }
        rows.append(row)
        if len(rows) >= limit:
            break

    return rows


def main() -> None:
    args = parse_args()
    data = load_domain_file(args.input)
    rows = make_template_rows(
        data=data,
        domain=args.domain,
        mode=args.mode,
        limit=args.limit,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} template rows to {args.output}")


if __name__ == "__main__":
    main()
