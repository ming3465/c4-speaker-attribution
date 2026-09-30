"""ConvoKit Supreme Court oral arguments -> utterance contract (synthetic fixture)."""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from src.datasets.supreme import convert, convert_source
from src.datasets.utterances import load_utterances

ROOT = Path(__file__).resolve().parents[1]
SUPREME = Path(__file__).parent / "fixtures" / "supreme_mini"


def test_turns_are_ordered_by_session_then_index_not_by_clock():
    """Sessions restart their clock, so start_times cannot order a whole argument."""
    rows = [r for r in convert(SUPREME) if r["conversation_id"] == "c1"]
    assert [(r["turn_index"], r["speaker"], r["text"]) for r in rows] == [
        (0, "Speaker_A", "We'll hear argument next in Case 18-877."),
        (1, "Speaker_B", "Mr. Chief Justice, and may it please the Court."),   # newline collapsed
        (2, "Speaker_C", "That is the patent decision."),                     # session 1, clock back to 1.5
        (3, "Speaker_D", "We disagree."),                                     # blank turn dropped, no gap
    ]
    assert [r["start_time"] for r in rows] == [0.0, 6.8, 1.5, 12.0]


def test_real_names_never_reach_the_contract():
    rows = convert(SUPREME)
    assert {r["speaker"] for r in rows} <= {"Speaker_A", "Speaker_B", "Speaker_C", "Speaker_D"}
    assert not any("roberts" in r["speaker"].lower() or "kagan" in r["speaker"].lower() for r in rows)


def test_labels_are_assigned_per_conversation():
    """The same person is Speaker_C in one argument and Speaker_A in the next."""
    rows = convert(SUPREME)
    first = [r for r in rows if r["conversation_id"] == "c1"]
    second = [r for r in rows if r["conversation_id"] == "c2"]
    assert first[2]["speaker"] == "Speaker_C"      # Kagan, third to speak in c1
    assert second[0]["speaker"] == "Speaker_A"     # the same person opens c2


def test_speaker_type_becomes_a_role():
    rows = convert(SUPREME)
    assert {r["role"] for r in rows} == {"Justice", "Advocate"}


def test_output_satisfies_the_utterance_contract(tmp_path):
    out = tmp_path / "supreme.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in convert(SUPREME)))
    units = load_utterances(out)
    assert [u.uid for u in units] == ["c1:0", "c1:1", "c1:2", "c1:3", "c2:0", "c2:1"]


def test_years_filter_selects_sources():
    assert convert(SUPREME, years=["1999"]) == convert(SUPREME)
    assert convert(SUPREME, years=["2019"]) == []


def test_a_zip_reads_the_same_as_a_folder(tmp_path):
    packed = tmp_path / "supreme-1999.zip"
    with zipfile.ZipFile(packed, "w") as archive:
        archive.write(SUPREME / "supreme-1999" / "utterances.jsonl", "supreme-1999/utterances.jsonl")
    assert convert_source(packed) == convert_source(SUPREME / "supreme-1999")


def test_an_unparseable_utterance_id_fails_naming_the_source(tmp_path):
    source = tmp_path / "supreme-2000"
    source.mkdir()
    (source / "utterances.jsonl").write_text(
        json.dumps({"id": "no-session-here", "conversation_id": "c", "speaker": "x", "text": "hi", "meta": {}}) + "\n")
    with pytest.raises(ValueError, match="no-session-here"):
        convert_source(source)


def test_cli_writes_jsonl_and_reports_counts(tmp_path):
    out = tmp_path / "supreme.jsonl"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "data" / "convert_supreme.py"),
         "--root", str(SUPREME), "--out", str(out)],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr
    assert "2 arguments, 6 utterances" in result.stdout


def test_cli_rejects_a_root_without_any_year(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "data" / "convert_supreme.py"),
         "--root", str(tmp_path), "--out", str(tmp_path / "x.jsonl")],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 2
    assert "supreme-<year>" in result.stderr


def test_a_saved_404_page_fails_with_the_path_and_a_hint(tmp_path):
    """The ConvoKit host answers 404 with a 162-byte HTML page; curl -o saves it as a .zip."""
    fake = tmp_path / "supreme-2020.zip"
    fake.write_text("<html>\n<head><title>404 Not Found</title></head>\n</html>\n")
    with pytest.raises(ValueError, match=r"supreme-2020\.zip: not a zip"):
        convert_source(fake)
