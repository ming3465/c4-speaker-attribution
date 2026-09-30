"""AMI NXT manual annotations -> utterance contract (synthetic fixture, no corpus needed)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.datasets.ami import convert, convert_meeting, speaker_roles
from src.datasets.utterances import load_utterances

ROOT = Path(__file__).resolve().parents[1]
AMI = Path(__file__).parent / "fixtures" / "ami_mini"


def test_utterances_follow_start_time_across_speakers():
    rows = convert_meeting(AMI, "M1", speaker_roles(AMI)["M1"])
    assert [(r["turn_index"], r["speaker"], r["text"]) for r in rows] == [
        (0, "Speaker_A", "Hi, I'm the manager."),     # punctuation attached, entity decoded
        (1, "Speaker_B", "Hello"),                    # single-id segment
        (2, "Speaker_A", "So budget first"),          # vocal sound and disfluency marker dropped
        (3, "Speaker_B", "Twelve euros?"),
    ]                                                 # cough-only segment skipped
    assert [r["role"] for r in rows] == ["PM", "ME", "PM", "ME"]
    assert [r["start_time"] for r in rows] == [0.9, 2.9, 8.9, 11.9]


def test_role_is_omitted_when_the_meeting_has_none():
    assert all("role" not in r for r in convert_meeting(AMI, "M1", {}))


def test_output_satisfies_the_utterance_contract(tmp_path):
    out = tmp_path / "ami.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in convert(AMI)))
    units = load_utterances(out)
    assert [u.uid for u in units] == ["M1:0", "M1:1", "M1:2", "M1:3"]
    assert {u.author for u in units} == {"Speaker_A", "Speaker_B"}


def test_unknown_word_id_fails_naming_the_file(tmp_path):
    broken = tmp_path / "ami"
    shutil.copytree(AMI, broken)
    seg = broken / "segments" / "M1.B.segments.xml"
    seg.write_text(seg.read_text().replace("M1.B.words3", "M1.B.words99"))
    with pytest.raises(ValueError, match=r"M1\.B\.segments\.xml"):
        convert(broken)


def test_cli_writes_jsonl_and_reports_counts(tmp_path):
    out = tmp_path / "ami.jsonl"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "data" / "convert_ami.py"), "--root", str(AMI), "--out", str(out)],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr
    assert len(out.read_text().splitlines()) == 4
    assert "1 meetings, 4 utterances" in result.stdout
