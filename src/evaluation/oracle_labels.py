from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_LABEL_FIELDS = (
    "label_id",
    "domain",
    "channel",
    "question_id",
    "question_type",
    "question_asker",
    "question_asker_role",
    "answer",
    "evidence_message_ids",
    "future_consumer_ids",
    "future_consumer_roles",
)


@dataclass(frozen=True)
class ValidationIssue:
    line_number: int
    field: str
    message: str


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Expected JSON object on line {line_number}")
            records.append(value)
    return records


def validate_oracle_labels(records: list[dict[str, Any]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_label_ids: set[str] = set()

    for line_number, record in enumerate(records, 1):
        for field in REQUIRED_LABEL_FIELDS:
            if field not in record:
                issues.append(
                    ValidationIssue(line_number, field, "missing required field")
                )

        label_id = record.get("label_id")
        if isinstance(label_id, str):
            if label_id in seen_label_ids:
                issues.append(
                    ValidationIssue(line_number, "label_id", "duplicate label id")
                )
            seen_label_ids.add(label_id)

        for field in (
            "evidence_message_ids",
            "future_consumer_ids",
            "future_consumer_roles",
        ):
            value = record.get(field)
            if field in record and not isinstance(value, list):
                issues.append(ValidationIssue(line_number, field, "must be a list"))
            elif isinstance(value, list) and not value:
                issues.append(ValidationIssue(line_number, field, "must not be empty"))

        if record.get("question_type") == "abstention":
            evidence = record.get("evidence_message_ids")
            if isinstance(evidence, list) and evidence:
                issues.append(
                    ValidationIssue(
                        line_number,
                        "evidence_message_ids",
                        "abstention rows should not point to positive evidence",
                    )
                )

    return issues


def write_validation_report(issues: list[ValidationIssue], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "line_number": issue.line_number,
            "field": issue.field,
            "message": issue.message,
        }
        for issue in issues
    ]
    output_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
