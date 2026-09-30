from __future__ import annotations

import json
import shutil
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DOMAINS = ("Finance", "Technology", "Healthcare", "Manufacturing")

REMOTE_FILENAMES = {
    domain: (
        "data/final/"
        f"{domain}/synthetic_domain_channels_rolevariants_{domain}.json"
    )
    for domain in DOMAINS
}

REMOTE_BASE_URL = "https://huggingface.co/datasets/kimperyang/GroupMemBench/resolve/main"


@dataclass(frozen=True)
class MessageRecord:
    domain: str
    channel: str
    msg_node: str
    content: str
    author: str
    role: str
    timestamp: str
    reply_to: str | None
    phase_name: str | None
    topic: str | None
    is_noise: bool | None
    is_decision_point: bool | None
    raw: dict[str, Any]


def remote_url_for_domain(domain: str) -> str:
    if domain not in REMOTE_FILENAMES:
        raise ValueError(f"Unknown GroupMemBench domain: {domain}")
    return f"{REMOTE_BASE_URL}/{REMOTE_FILENAMES[domain]}"


def download_domain(domain: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(REMOTE_FILENAMES[domain]).name
    output_path = output_dir / filename
    url = remote_url_for_domain(domain)
    with urllib.request.urlopen(url) as response, output_path.open("wb") as file:
        shutil.copyfileobj(response, file)
    return output_path


def load_domain_file(path: Path) -> dict[str, list[dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level object keyed by channel: {path}")
    return data


def iter_messages(
    data: dict[str, list[dict[str, Any]]],
    *,
    domain: str,
) -> list[MessageRecord]:
    records: list[MessageRecord] = []
    for channel, messages in data.items():
        if not isinstance(messages, list):
            continue
        for message in messages:
            if not isinstance(message, dict):
                continue
            records.append(
                MessageRecord(
                    domain=domain,
                    channel=channel,
                    msg_node=str(message.get("msg_node", "")),
                    content=str(message.get("content", "")),
                    author=str(message.get("author", "")),
                    role=str(message.get("role", "")),
                    timestamp=str(message.get("timestamp", "")),
                    reply_to=message.get("reply_to"),
                    phase_name=message.get("phase_name"),
                    topic=message.get("topic"),
                    is_noise=message.get("is_noise"),
                    is_decision_point=message.get("is_decision_point"),
                    raw=message,
                )
            )
    return records


def summarize_schema(records: list[MessageRecord]) -> dict[str, Any]:
    field_counter: Counter[str] = Counter()
    type_counter: dict[str, Counter[str]] = defaultdict(Counter)
    role_counter: Counter[str] = Counter()
    author_counter: Counter[str] = Counter()
    channel_counter: Counter[str] = Counter()
    decision_count = 0
    noise_count = 0

    for record in records:
        role_counter[record.role] += 1
        author_counter[record.author] += 1
        channel_counter[record.channel] += 1
        decision_count += int(bool(record.is_decision_point))
        noise_count += int(bool(record.is_noise))
        for key, value in record.raw.items():
            field_counter[key] += 1
            type_counter[key][type(value).__name__] += 1

    return {
        "message_count": len(records),
        "channel_count": len(channel_counter),
        "author_count": len(author_counter),
        "role_count": len(role_counter),
        "decision_message_count": decision_count,
        "noise_message_count": noise_count,
        "fields": sorted(field_counter),
        "field_presence": dict(sorted(field_counter.items())),
        "field_types": {
            key: dict(counter.most_common())
            for key, counter in sorted(type_counter.items())
        },
        "top_channels": channel_counter.most_common(20),
        "top_roles": role_counter.most_common(30),
        "top_authors": author_counter.most_common(30),
    }


def sample_records(records: list[MessageRecord], limit: int) -> list[dict[str, Any]]:
    return [
        {
            "domain": record.domain,
            "channel": record.channel,
            "msg_node": record.msg_node,
            "author": record.author,
            "role": record.role,
            "timestamp": record.timestamp,
            "reply_to": record.reply_to,
            "phase_name": record.phase_name,
            "topic": record.topic,
            "is_noise": record.is_noise,
            "is_decision_point": record.is_decision_point,
            "content": record.content,
        }
        for record in records[:limit]
    ]
