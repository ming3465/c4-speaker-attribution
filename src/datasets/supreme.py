"""Supreme Court Oral Arguments (ConvoKit) -> utterance contract.

The study's high-signal corpus: oral arguments are long multi-party sessions,
about 236 utterances and 9 speakers each, with a mean of 47.9 words per turn
against AMI's 28.4. Long, distinctive turns are the condition under which
speaker attribution has the most content to bind to, which is what makes this
corpus worth its slower reader passes.

Read straight out of ConvoKit's per-year zip with `zipfile` and `json`. The
`convokit` package is deliberately not a dependency: this project has none, and
that package would pull in spacy and torch to read a JSONL file.

    https://zissou.infosci.cornell.edu/convokit/datasets/supreme-corpus/supreme-<year>.zip

ConvoKit's page advertises years 1955 to 2023, but the per-year zips stop at
**2019** -- 2020 onwards answer 404 with a 162-byte error page. A download that
quietly saved that page is caught here rather than surfacing as a zip error
with no path in it.

**Speakers are anonymised.** The source names them
(`j__john_g_roberts_jr`, `ryan_park`), and the study's whole design shows the
reader `Speaker_<letter>` and nothing else -- real names turn "who said this?"
into a recall question about famous people. They are relabelled per
conversation in first-appearance order.

`role` carries the source's `speaker_type`, Justice or Advocate. Roles are
metadata: `RenderedProbe.prompt` renders only speaker labels and text, so no
role ever reaches the reader. AMI does the same with PM / ME / UI / ID.

**Licence.** ConvoKit states none for this corpus and Oyez's own licence page
renders only in JavaScript. Treated as research-use-only, never redistributed;
see data/README.md.
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from src.datasets.elitr import _label

# "24929__0_000": conversation, then the argument session and the turn inside it.
# Sessions restart their clock, so this ordering -- not start_times -- is the
# transcript's real order. 3-6 sessions per argument, under 1,000 turns each.
UTTERANCE_ID = re.compile(r"^(?P<conversation>.+)__(?P<session>\d+)_(?P<index>\d+)$")
ROLES = {"J": "Justice", "A": "Advocate"}


def _records(source: Path) -> list[dict]:
    """utterances.jsonl out of a `supreme-<year>.zip` or an unzipped folder."""
    if source.is_dir():
        candidates = sorted(source.rglob("utterances.jsonl"))
        if not candidates:
            raise ValueError(f"{source}: no utterances.jsonl under this folder")
        return [json.loads(line) for line in candidates[0].read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        with zipfile.ZipFile(source) as archive:
            names = [n for n in archive.namelist() if n.endswith("utterances.jsonl")]
            if not names:
                raise ValueError(f"{source}: no utterances.jsonl inside this zip")
            text = archive.read(names[0]).decode("utf-8")
    except zipfile.BadZipFile:
        raise ValueError(f"{source}: not a zip ({source.stat().st_size} bytes). A 404 from the "
                         f"ConvoKit host saves an HTML error page under this name; the per-year "
                         f"zips stop at 2019.") from None
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _order(record: dict, source: Path) -> tuple[int, int]:
    match = UTTERANCE_ID.match(record["id"])
    if not match:
        raise ValueError(f"{source}: utterance id {record['id']!r} is not <conversation>__<session>_<index>")
    return int(match.group("session")), int(match.group("index"))


def convert_source(source: Path) -> list[dict]:
    """One year's arguments as contract rows, conversations in id order."""
    by_conversation: dict[str, list[dict]] = {}
    for record in _records(source):
        by_conversation.setdefault(record["conversation_id"], []).append(record)
    rows = []
    for conversation in sorted(by_conversation):
        names: dict[str, str] = {}
        ordered = sorted(by_conversation[conversation], key=lambda r: _order(r, source))
        for turn, record in enumerate(ordered):
            text = " ".join(record["text"].split())
            if not text:
                continue                       # a turn transcribed as nothing to attribute
            speaker = record["speaker"]
            if speaker not in names:
                names[speaker] = _label(len(names))
            meta = record.get("meta") or {}
            row = {"conversation_id": conversation, "turn_index": turn,
                   "speaker": names[speaker], "text": text}
            if meta.get("speaker_type") in ROLES:
                row["role"] = ROLES[meta["speaker_type"]]
            starts = meta.get("start_times") or []
            if starts and isinstance(starts[0], (int, float)):
                row["start_time"] = starts[0]
            rows.append(row)
    return rows


def convert(root: Path, years: list[str] | None = None) -> list[dict]:
    """Every `supreme-<year>` zip or folder under `root`, oldest year first.

    `turn_index` is renumbered per conversation after empty turns are dropped,
    so it stays gapless as the contract requires.
    """
    sources = sorted(p for p in root.iterdir()
                     if p.name.startswith("supreme-") and (p.is_dir() or p.suffix == ".zip"))
    if years:
        wanted = {str(y) for y in years}
        sources = [p for p in sources if p.name.removeprefix("supreme-").removesuffix(".zip") in wanted]
    rows = [row for source in sources for row in convert_source(source)]
    seen: dict[str, int] = {}
    for row in rows:
        conversation = row["conversation_id"]
        row["turn_index"] = seen[conversation] = seen.get(conversation, -1) + 1
    return rows
