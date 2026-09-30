"""ELITR Minuting Corpus -> utterance contract (synthetic fixture, no corpus needed)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.datasets.elitr import _label, convert, convert_meeting
from src.datasets.utterances import load_utterances

ROOT = Path(__file__).resolve().parents[1]
ELITR = Path(__file__).parent / "fixtures" / "elitr_mini"
MEETING = ELITR / "elitr-minuting-corpus-en" / "dev" / "meeting_en_dev_001"
PREAMBLE = ELITR / "elitr-minuting-corpus-en" / "dev" / "meeting_en_dev_006"


def test_a_marker_block_is_one_turn_and_tags_are_dropped():
    rows, _ = convert_meeting(MEETING)
    assert [(r["turn_index"], r["speaker"], r["text"]) for r in rows] == [
        (0, "Speaker_A", "Yeah so you are always host."),
        (1, "Speaker_B", "Eh, uh, not always, when I open the link I am never the host."),
        # the two continuation lines join the marker's own text into one turn
        (2, "Speaker_A", "I just think that you are always the host. So when we will be going - to [LOCATION1] -"),
        # a block that is nothing but <laugh/> disappears entirely
        (3, "Speaker_A", "How is [PROJECT2] looking, [PERSON12]?"),
        (4, "Speaker_C", "We shipped it on Monday."),
    ]


def test_speakers_are_relabelled_so_in_text_placeholders_cannot_leak():
    """PERSON12 speaks and is also named in another turn's text; the two must not match."""
    rows, _ = convert_meeting(MEETING)
    roster = {r["speaker"] for r in rows}
    assert roster == {"Speaker_A", "Speaker_B", "Speaker_C"}
    assert any("[PERSON12]" in r["text"] for r in rows)
    assert not any(r["speaker"] in r["text"] for r in rows)


def test_elitr_has_no_timestamps_or_roles():
    assert all("start_time" not in r and "role" not in r for r in convert_meeting(MEETING)[0])


def test_czech_meetings_and_minutes_files_are_skipped():
    rows, _ = convert(ELITR)
    assert {r["conversation_id"] for r in rows} == {"meeting_en_dev_001", "meeting_en_dev_006", "meeting_en_test_001"}
    assert not any("Czech" in r["text"] or "Not a transcript" in r["text"] for r in rows)


def test_output_satisfies_the_utterance_contract(tmp_path):
    out = tmp_path / "elitr.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in convert(ELITR)[0]))
    units = load_utterances(out)
    assert [u.uid for u in units][:2] == ["meeting_en_dev_001:0", "meeting_en_dev_001:1"]
    assert all(u.role == "" for u in units)


def test_lines_before_the_first_marker_are_dropped_and_counted():
    """meeting_en_dev_006 in the real corpus opens with 257 unattributable lines."""
    rows, preamble = convert_meeting(PREAMBLE)
    assert preamble == 2
    assert [r["text"] for r in rows] == ["Hello.", "Hi back."]
    assert not any("nobody said this" in r["text"] for r in rows)


def test_convert_reports_dropped_preamble_per_meeting():
    _, dropped = convert(ELITR)
    assert dropped == {"meeting_en_dev_006": 2}


def test_labels_run_past_z():
    assert [_label(0), _label(25), _label(26), _label(27)] == [
        "Speaker_A", "Speaker_Z", "Speaker_AA", "Speaker_AB"]


def test_cli_writes_jsonl_and_reports_counts(tmp_path):
    out = tmp_path / "elitr.jsonl"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "data" / "convert_elitr.py"), "--root", str(ELITR), "--out", str(out)],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr
    assert "3 meetings, 9 utterances" in result.stdout
    assert "dropped 2 unattributed line(s)" in result.stdout


def test_cli_rejects_a_root_without_the_english_corpus(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "data" / "convert_elitr.py"),
         "--root", str(tmp_path), "--out", str(tmp_path / "x.jsonl")],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 2
    assert "elitr-minuting-corpus-en" in result.stderr


def test_a_transcript_with_no_marker_at_all_yields_no_rows(tmp_path):
    """meeting_en_dev_006 in the real corpus has no (PERSONnn) marker in 19 kB."""
    meeting = tmp_path / "meeting_en_dev_007"
    meeting.mkdir()
    (meeting / "transcript_MAN_annot07.txt").write_text("one\ntwo\nthree\n")
    rows, preamble = convert_meeting(meeting)
    assert rows == [] and preamble == 3
