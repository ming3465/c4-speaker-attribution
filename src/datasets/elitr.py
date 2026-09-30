"""ELITR Minuting Corpus (CC BY-NC-SA 4.0) -> utterance contract.

English meetings only: 120 transcripts across the dev / test / test2 / train
splits, one transcript file per meeting. The Czech half is skipped, because the
reader and every baseline in this study are English.

Source format is plain text, not NXT. A speaker marker opens a turn and every
line after it belongs to that speaker until the next marker:

    (PERSON20) I just think that you are always the host.
    So when we will be going -
    (PERSON12) Yes.

**One utterance per marker block, not per line.** The lines inside a block are
sentence splits of one continuous turn, so joining them gives a mean of 24.0
words against 9.6 per line -- close to AMI's 28.4, and it keeps the turn-taking
baseline meaning what it means elsewhere in the study.

Speakers arrive already anonymised as `PERSONnn` and are relabelled
`Speaker_<letter>` in first-appearance order per meeting, the same surface the
reader sees on AMI and ICSI. The relabelling also breaks a leak: the text keeps
ELITR's in-line entity placeholders, including `[PERSONnn]` drawn from the same
numbering as the markers, so leaving the ids in the roster would let a reader
match `[PERSON20]` in a context line to speaker `PERSON20`. After relabelling,
no in-text placeholder matches any roster label.

Non-speech tags (`<laugh/>`, `<unintelligible/>`, `<parallel_talk>`, ...) are
dropped like AMI's vocal sounds. Entity placeholders (`[ORGANIZATION1]`,
`[PROJECT2]`, ...) are content and stay. ELITR has no timestamps, so no
`start_time` is emitted; order is the order of the transcript.

13 of the 120 transcripts carry lines before any speaker marker, 272 lines in
all. Ten are noise tags alone. `meeting_en_test2_004` opens with one real
sentence, and **`meeting_en_dev_006` has no speaker marker anywhere in its
19 kB**, so all 257 of its lines are unattributed and the meeting yields no
rows at all -- 119 meetings reach the output, not 120. Nothing can attribute an
unlabelled line, so these are dropped, counted per meeting, and printed by the
CLI, rather than lost silently.

One consequence of merging blocks is worth knowing before reading a gate
result: adjacent turns always have different speakers, because a run of lines
by one speaker becomes a single turn. That makes "not the neighbouring
speakers" a genuinely informative guess, and the turn-taking shortcut reaches
54.9% against 33.5% chance on the registered design -- a far higher bar for the
headroom gate than AMI's 33.8%.

Download: LINDAT handle 11234/1-4692. The old XMLUI bitstream URL is dead after
the DSpace 7 migration -- see data/README.md for the REST call that resolves
the current one.
"""
from __future__ import annotations

import re
from pathlib import Path

ENGLISH = "elitr-minuting-corpus-en"
MARKER = re.compile(r"^\((PERSON\d+)\)\s*(.*)$")
TAG = re.compile(r"<[^>]*>")


def _label(position: int) -> str:
    """0 -> Speaker_A ... 25 -> Speaker_Z, 26 -> Speaker_AA. Meetings have far fewer."""
    letters = ""
    position += 1
    while position:
        position, remainder = divmod(position - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return f"Speaker_{letters}"


def _clean(lines: list[str]) -> str:
    return " ".join(TAG.sub(" ", " ".join(lines)).split())


def _turns(transcript_path: Path) -> tuple[list[tuple[str, str]], int]:
    """((PERSONnn, text) per marker block, dropped preamble lines).

    Blocks that clean down to nothing are dropped too: a turn that was only
    `<laugh/>` has no words to attribute.
    """
    out: list[tuple[str, str]] = []
    speaker: str | None = None
    buffer: list[str] = []
    preamble = 0

    def flush() -> None:
        if speaker is not None:
            text = _clean(buffer)
            if text:
                out.append((speaker, text))

    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = MARKER.match(stripped)
        if match:
            flush()
            speaker, buffer = match.group(1), ([match.group(2)] if match.group(2) else [])
        elif speaker is None:
            preamble += 1          # no marker yet: nobody to attribute this line to
        else:
            buffer.append(stripped)
    flush()
    return out, preamble


def convert_meeting(meeting_dir: Path) -> tuple[list[dict], int]:
    """(contract rows, dropped preamble lines) for one meeting, speakers relabelled."""
    transcripts = sorted(meeting_dir.glob("transcript*.txt"))
    if not transcripts:
        return [], 0
    turns, preamble = _turns(transcripts[0])
    names: dict[str, str] = {}
    rows = []
    for turn, (person, text) in enumerate(turns):
        if person not in names:
            names[person] = _label(len(names))
        rows.append({"conversation_id": meeting_dir.name, "turn_index": turn,
                     "speaker": names[person], "text": text})
    return rows, preamble


def convert(root: Path) -> tuple[list[dict], dict[str, int]]:
    """(rows, dropped preamble lines per meeting) for every English meeting under `root`."""
    base = root / ENGLISH if (root / ENGLISH).is_dir() else root
    rows: list[dict] = []
    dropped: dict[str, int] = {}
    for meeting in sorted(base.glob("*/meeting_*"), key=lambda p: p.name):
        meeting_rows, preamble = convert_meeting(meeting)
        rows += meeting_rows
        if preamble:
            dropped[meeting.name] = preamble
    return rows, dropped
