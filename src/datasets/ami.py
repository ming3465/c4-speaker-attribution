"""AMI Meeting Corpus manual annotations (v1.6.2, CC BY 4.0) -> utterance contract.

One utterance per transcriber segment: the segment's words in order, with
punctuation attached to the word before it. Vocal sounds, disfluency markers
and other non-word elements are dropped, and segments left empty are skipped.
Utterances from every speaker are ordered by segment start time. Speaker =
"Speaker_<letter>" (the meeting's NXT agent); role = PM / ME / UI / ID from
corpusResources/meetings.xml where the meeting has one.

Download: https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

NITE_ID = "{http://nite.sourceforge.net/}id"
NITE_CHILD = "{http://nite.sourceforge.net/}child"
WORD_RANGE = re.compile(r"#id\(([^)]+)\)(?:\.\.id\(([^)]+)\))?")


def speaker_roles(root: Path) -> dict[str, dict[str, str]]:
    """meeting id -> {agent letter: role}, roles only where given."""
    meetings = ET.parse(root / "corpusResources" / "meetings.xml").getroot()
    return {m.get("observation"): {s.get("nxt_agent"): s.get("role")
                                   for s in m.iter("speaker") if s.get("role")}
            for m in meetings.iter("meeting")}


def _tokens(words_path: Path) -> tuple[dict[str, int], list[tuple[str, bool] | None]]:
    """Position of every element by nite id; (text, is_punctuation) for words, None otherwise."""
    index: dict[str, int] = {}
    tokens: list[tuple[str, bool] | None] = []
    for element in ET.parse(words_path).getroot():
        index[element.get(NITE_ID)] = len(tokens)
        is_word = element.tag == "w"
        tokens.append((element.text or "", element.get("punc") == "true") if is_word else None)
    return index, tokens


def _join(words: list[tuple[str, bool]]) -> str:
    text = ""
    for word, is_punctuation in words:
        text += word if is_punctuation or not text else f" {word}"
    return text.strip()


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
            out.append((float(segment.get("transcriber_start")), text))
    return out


def convert_meeting(root: Path, meeting_id: str, roles: dict[str, str]) -> list[dict]:
    """All speakers' utterances of one meeting, in start-time order, as contract rows."""
    timed = []
    for words_path in sorted((root / "words").glob(f"{meeting_id}.*.words.xml")):
        agent = words_path.name.split(".")[1]
        segments_path = root / "segments" / f"{meeting_id}.{agent}.segments.xml"
        if segments_path.exists():
            timed += [(start, agent, order, text)
                      for order, (start, text) in enumerate(_segments(segments_path, words_path))]
    rows = []
    for turn, (start, agent, _, text) in enumerate(sorted(timed)):
        row = {"conversation_id": meeting_id, "turn_index": turn, "speaker": f"Speaker_{agent}",
               "text": text, "start_time": start}
        if agent in roles:
            row["role"] = roles[agent]
        rows.append(row)
    return rows


def convert(root: Path) -> list[dict]:
    """Every meeting under `root` (the unzipped annotation folder), meetings in id order."""
    roles = speaker_roles(root)
    meetings = sorted({p.name.split(".")[0] for p in (root / "words").glob("*.words.xml")})
    return [row for meeting in meetings for row in convert_meeting(root, meeting, roles.get(meeting, {}))]
