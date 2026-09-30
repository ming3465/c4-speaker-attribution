"""ICSI Meeting Corpus core NXT annotations (v1.0, CC BY 4.0) -> utterance contract.

Same Edinburgh NXT tooling as AMI, so the shape is familiar, but the two
releases differ in five places and the AMI converter cannot be pointed at ICSI:

| | AMI | ICSI |
| --- | --- | --- |
| folders | `words/`, `segments/` | `Words/`, `Segments/` |
| segment file | `<m>.<agent>.segments.xml` | `<m>.<agent>.segs.xml` |
| segment start | `transcriber_start` | `starttime` |
| punctuation | `punc="true"` | a `c` class, e.g. `c="CM"` |
| roles | PM / ME / UI / ID | none |

`src/datasets/ami.py` is deliberately left alone: `data/processed/ami.jsonl`
has a sha256 recorded in `docs/C4_ANALYSIS_PLAN.md` and the main result depends
on it, so the two converters share only pure helpers.

One utterance per transcriber segment, ordered by start time across speakers.
Speaker = "Speaker_<letter>" (the meeting's NXT agent, A-J). ICSI meetings have
3-10 speakers where AMI has 4, which makes it the widest corpus in the study
for the by-roster-size outcome. No `role` is emitted: ICSI records gender,
education and age for each participant, none of which is a meeting role, and
showing them would change the task.

Download: https://groups.inf.ed.ac.uk/ami/ICSICorpusAnnotations/ICSI_core_NXT.zip
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from src.datasets.ami import NITE_CHILD, NITE_ID, WORD_RANGE, _join

# `c` classes that attach to the word before them with no space -- ICSI's
# equivalent of AMI's punc="true". Everything else (W, TRUNCW, LET, SYM, ...)
# is an ordinary token: TRUNCW is a cut-off word and LET a spoken letter.
ATTACHING = frozenset({".", "CM", "APOSS", "HYPH", "RQUOTE"})


def _tokens(words_path: Path) -> tuple[dict[str, int], list[tuple[str, bool] | None]]:
    """Position of every element by nite id; (text, attaches_to_previous) for words, None otherwise."""
    index: dict[str, int] = {}
    tokens: list[tuple[str, bool] | None] = []
    for element in ET.parse(words_path).getroot():
        index[element.get(NITE_ID)] = len(tokens)
        is_word = element.tag == "w"
        tokens.append((element.text or "", element.get("c") in ATTACHING) if is_word else None)
    return index, tokens


def _segments(segments_path: Path, words_path: Path) -> list[tuple[float, str]]:
    """(start time, text) for each non-empty segment of one speaker."""
    index, tokens = _tokens(words_path)
    out = []
    for segment in ET.parse(segments_path).getroot().iter("segment"):
        words: list[tuple[str, bool]] = []
        for child in segment.iter(NITE_CHILD):
            match = WORD_RANGE.search(child.get("href", ""))
            first, last = (match.group(1), match.group(2) or match.group(1)) if match else (None, None)
            if first not in index or last not in index:
                raise ValueError(f"{segments_path}: segment {segment.get(NITE_ID)} points to unknown words "
                                 f"{child.get('href')!r}")
            words += [t for t in tokens[index[first]:index[last] + 1] if t is not None]
        text = _join(words)
        if text:
            out.append((float(segment.get("starttime")), text))
    return out


def convert_meeting(root: Path, meeting_id: str) -> list[dict]:
    """All speakers' utterances of one meeting, in start-time order, as contract rows."""
    timed = []
    for words_path in sorted((root / "Words").glob(f"{meeting_id}.*.words.xml")):
        agent = words_path.name.split(".")[1]
        segments_path = root / "Segments" / f"{meeting_id}.{agent}.segs.xml"
        if segments_path.exists():
            timed += [(start, agent, order, text)
                      for order, (start, text) in enumerate(_segments(segments_path, words_path))]
    return [{"conversation_id": meeting_id, "turn_index": turn, "speaker": f"Speaker_{agent}",
             "text": text, "start_time": start}
            for turn, (start, agent, _, text) in enumerate(sorted(timed))]


def convert(root: Path) -> list[dict]:
    """Every meeting under `root` (the unzipped annotation folder), meetings in id order."""
    meetings = sorted({p.name.split(".")[0] for p in (root / "Words").glob("*.words.xml")})
    return [row for meeting in meetings for row in convert_meeting(root, meeting)]
