"""ICSI core NXT annotations -> utterance contract (synthetic fixture, no corpus needed)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.datasets.icsi import ATTACHING, convert, convert_meeting
from src.datasets.utterances import load_utterances

ROOT = Path(__file__).resolve().parents[1]
ICSI = Path(__file__).parent / "fixtures" / "icsi_mini"


def test_utterances_follow_start_time_across_speakers():
    rows = convert_meeting(ICSI, "M1")
    assert [(r["turn_index"], r["speaker"], r["text"]) for r in rows] == [
        (0, "Speaker_A", "Hi, I'm the manager."),      # CM and APOSS attach, so does the final stop
        (1, "Speaker_B", "Hello"),                     # single-id segment
        (2, "Speaker_C", "We discu discussed B."),     # TRUNCW and LET are ordinary tokens; pause dropped
        (3, "Speaker_A", "So budget first"),           # vocalsound and disfmarker dropped
        (4, "Speaker_B", "Twelve euros?"),
    ]                                                  # sound-only and comment-only segments skipped
    assert [r["start_time"] for r in rows] == [0.9, 2.9, 5.9, 8.9, 11.9]


def test_role_is_never_emitted():
    """ICSI records gender, education and age -- none of them a meeting role."""
    assert all("role" not in r for r in convert_meeting(ICSI, "M1"))


def test_only_punctuation_classes_attach_to_the_previous_word():
    assert ATTACHING == {".", "CM", "APOSS", "HYPH", "RQUOTE"}
    assert "TRUNCW" not in ATTACHING and "W" not in ATTACHING


def test_output_satisfies_the_utterance_contract(tmp_path):
    out = tmp_path / "icsi.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in convert(ICSI)))
    units = load_utterances(out)
    assert [u.uid for u in units] == ["M1:0", "M1:1", "M1:2", "M1:3", "M1:4"]
    assert {u.author for u in units} == {"Speaker_A", "Speaker_B", "Speaker_C"}
    assert all(u.role == "" for u in units)


def test_unknown_word_id_fails_naming_the_file(tmp_path):
    broken = tmp_path / "icsi"
    shutil.copytree(ICSI, broken)
    seg = broken / "Segments" / "M1.B.segs.xml"
    seg.write_text(seg.read_text().replace("M1.w.20", "M1.w.99"))
    with pytest.raises(ValueError, match=r"M1\.B\.segs\.xml"):
        convert(broken)


def test_cli_writes_jsonl_and_reports_counts(tmp_path):
    out = tmp_path / "icsi.jsonl"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "data" / "convert_icsi.py"), "--root", str(ICSI), "--out", str(out)],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr
    assert len(out.read_text().splitlines()) == 5
    assert "1 meetings, 5 utterances" in result.stdout
    assert "3: 1" in result.stdout           # one meeting with three speakers


def test_cli_rejects_a_root_without_words(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "data" / "convert_icsi.py"),
         "--root", str(tmp_path), "--out", str(tmp_path / "x.jsonl")],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 2
    assert "Words/" in result.stderr
