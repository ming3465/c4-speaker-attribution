"""Generic multi-party utterance contract (AMI, ELITR, or any meeting/chat data).

C4's attribution probe only needs who said what, in order. Any corpus
converted to this JSONL contract runs through the same pipeline with no
labelling:

    {"conversation_id": "ES2002a", "turn_index": 14, "speaker": "B", "text": "...",
     "role": "UI", "start_time": 312.4}

Required: conversation_id (non-empty str), turn_index (int >= 0, unique within
its conversation), speaker (non-empty str), text (str). Optional: role (str),
start_time (seconds, number). Speaker ids only need to be consistent within a
conversation. Loading fails fast on the first violation, naming the line.
"""
from __future__ import annotations

import json
import warnings
from collections import defaultdict
from pathlib import Path

from src.evaluation.failure_decomposition import MemoryUnit

REQUIRED = ("conversation_id", "turn_index", "speaker", "text")


class UtteranceContractError(ValueError):
    """A line of the utterance file violates the data contract."""


def _fail(path: Path, line_no: int, message: str) -> UtteranceContractError:
    return UtteranceContractError(f"{path}:{line_no}: {message}")


def _parse_line(path: Path, line_no: int, line: str) -> dict:
    try:
        row = json.loads(line)
    except json.JSONDecodeError as exc:
        raise _fail(path, line_no, f"invalid JSON ({exc.msg})") from None
    if not isinstance(row, dict):
        raise _fail(path, line_no, "each line must be a JSON object")
    missing = [f for f in REQUIRED if f not in row]
    if missing:
        raise _fail(path, line_no, f"missing required field(s): {', '.join(missing)}")
    for name in ("conversation_id", "speaker"):
        if not isinstance(row[name], str) or not row[name].strip():
            raise _fail(path, line_no, f"{name} must be a non-empty string")
    turn = row["turn_index"]
    if isinstance(turn, bool) or not isinstance(turn, int) or turn < 0:
        raise _fail(path, line_no, f"turn_index must be an integer >= 0, got {turn!r}")
    if not isinstance(row["text"], str):
        raise _fail(path, line_no, "text must be a string")
    if "role" in row and row["role"] is not None and not isinstance(row["role"], str):
        raise _fail(path, line_no, "role must be a string when present")
    start = row.get("start_time")
    if start is not None and (isinstance(start, bool) or not isinstance(start, (int, float))):
        raise _fail(path, line_no, "start_time must be a number (seconds) when present")
    return row


def load_utterances(path: Path) -> list[MemoryUnit]:
    """Load and validate a contract file into MemoryUnits (group = conversation)."""
    path = Path(path)
    seen: dict[tuple[str, int], int] = {}
    speakers: dict[str, set[str]] = defaultdict(set)
    units: list[MemoryUnit] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = _parse_line(path, line_no, line)
            conversation, turn = row["conversation_id"], row["turn_index"]
            if (conversation, turn) in seen:
                raise _fail(path, line_no, f"duplicate turn_index {turn} in conversation {conversation!r} "
                                           f"(first seen on line {seen[(conversation, turn)]})")
            seen[(conversation, turn)] = line_no
            speakers[conversation].add(row["speaker"])
            units.append(MemoryUnit(
                uid=f"{conversation}:{turn}",
                group=conversation,
                text=row["text"],
                author=row["speaker"],
                role=row.get("role") or "",
                order=turn,
                meta={"start_time": row.get("start_time")},
            ))
    if not units:
        raise UtteranceContractError(f"{path}: no utterances found")
    solo = sorted(c for c, s in speakers.items() if len(s) < 2)
    if solo:
        warnings.warn(f"{len(solo)} conversation(s) have a single speaker and yield no probes: "
                      f"{', '.join(solo[:5])}{'...' if len(solo) > 5 else ''}", stacklevel=2)
    return units
