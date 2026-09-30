"""Utterance data contract, window contexts, and probes built from them."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.datasets.utterances import UtteranceContractError, load_utterances
from src.evaluation.attribution_frozen import (
    check_probe,
    probes_from_contexts,
    render_main,
    window_contexts,
)

SMALL = Path(__file__).resolve().parent / "fixtures" / "utterances_small.jsonl"
BACKCHANNELS = {"mm-hmm", "yeah", "okay"}


@pytest.fixture(scope="module")
def units():
    with pytest.warns(UserWarning, match="single speaker"):
        return load_utterances(SMALL)


# --------------------------------------------------------------------------
# contract
# --------------------------------------------------------------------------

def test_valid_file_loads_into_memory_units(units):
    assert len(units) == 24
    first = units[0]
    assert (first.uid, first.group, first.author, first.order) == ("m1:0", "m1", "PM", 0)
    assert first.role == "project manager"
    assert first.meta["start_time"] == 0.0
    assert {u.group for u in units} == {"m1", "m2", "m3"}


def write_lines(tmp_path, *rows):
    path = tmp_path / "u.jsonl"
    path.write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows) + "\n")
    return path


OK = {"conversation_id": "c", "turn_index": 0, "speaker": "A", "text": "hi"}


@pytest.mark.parametrize("bad, fragment", [
    ("{not json", "invalid JSON"),
    ("[1, 2]", "must be a JSON object"),
    ({"conversation_id": "c", "turn_index": 1, "speaker": "A"}, "missing required field(s): text"),
    ({**OK, "turn_index": -1}, "turn_index must be an integer >= 0"),
    ({**OK, "turn_index": True}, "turn_index must be an integer >= 0"),
    ({**OK, "turn_index": "3"}, "turn_index must be an integer >= 0"),
    ({**OK, "speaker": "  "}, "speaker must be a non-empty string"),
    ({**OK, "conversation_id": ""}, "conversation_id must be a non-empty string"),
    ({**OK, "text": 5}, "text must be a string"),
    ({**OK, "role": 3}, "role must be a string"),
    ({**OK, "start_time": "12:00"}, "start_time must be a number"),
])
def test_contract_violations_name_the_line(tmp_path, bad, fragment):
    path = write_lines(tmp_path, {**OK, "turn_index": 9, "speaker": "B"}, bad)
    with pytest.raises(UtteranceContractError) as err:
        load_utterances(path)
    assert fragment in str(err.value)
    assert ":2:" in str(err.value)


def test_duplicate_turn_reports_both_lines(tmp_path):
    path = write_lines(tmp_path, OK, {**OK, "speaker": "B"})
    with pytest.raises(UtteranceContractError, match=r":2: duplicate turn_index 0 .*first seen on line 1"):
        load_utterances(path)


def test_empty_file_is_rejected(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("\n\n")
    with pytest.raises(UtteranceContractError, match="no utterances"):
        load_utterances(path)


# --------------------------------------------------------------------------
# window contexts
# --------------------------------------------------------------------------

def test_windows_stay_inside_one_conversation(units):
    by_uid = {u.uid: u for u in units}
    for context in window_contexts(units, size=6, stride=3):
        groups = {by_uid[uid].group for uid in context.uids}
        assert groups == {context.cluster_id}
        orders = [by_uid[uid].order for uid in context.uids]
        assert orders == sorted(orders)


def test_window_sizes_and_strides(units):
    contexts = window_contexts(units, size=6, stride=3)
    m1 = [c for c in contexts if c.cluster_id == "m1"]
    assert [c.context_id for c in m1] == ["m1@0", "m1@3", "m1@6"]
    assert all(len(c.uids) == 6 for c in m1)


def test_short_conversation_yields_one_whole_window(units):
    contexts = window_contexts(units, size=10, stride=5)
    m3 = [c for c in contexts if c.cluster_id == "m3"]
    assert len(m3) == 1 and len(m3[0].uids) == 2


@pytest.mark.parametrize("size, stride", [(1, 1), (5, 0)])
def test_invalid_window_parameters_raise(units, size, stride):
    with pytest.raises(ValueError, match="window size"):
        window_contexts(units, size=size, stride=stride)


# --------------------------------------------------------------------------
# probes from windows
# --------------------------------------------------------------------------

def test_window_probes_are_bindable_and_satisfy_invariants(units):
    store = {u.uid: u.text for u in units}
    probes = probes_from_contexts(window_contexts(units, size=6, stride=3), units)
    assert probes
    for probe in probes:
        assert check_probe(render_main(probe, store, 1.0)) == []
        assert probe.cluster_id in {"m1", "m2"}          # m3 is single-speaker -> no probes
        assert probe.probe_id.startswith(probe.qid + ":")


def test_min_target_words_drops_backchannels(units):
    contexts = window_contexts(units, size=6, stride=3)
    texts = {u.uid: u.text for u in units}
    loose = probes_from_contexts(contexts, units)
    strict = probes_from_contexts(contexts, units, min_target_words=3)
    assert any(texts[p.target_uid] in BACKCHANNELS for p in loose)
    assert not any(texts[p.target_uid] in BACKCHANNELS for p in strict)
    assert len(strict) < len(loose)


def test_probe_construction_is_deterministic(units):
    contexts = window_contexts(units, size=6, stride=3)
    assert probes_from_contexts(contexts, units, seed=3) == probes_from_contexts(contexts, units, seed=3)


def test_scope_compresses_only_the_selected_part(units):
    probe = probes_from_contexts(window_contexts(units, size=6, stride=3), units)[0]
    full = {u.uid: u.text for u in units}
    squeezed = {uid: "X" for uid in full}
    target_only = render_main(probe, squeezed, 0.1, full_store=full, scope="target").texts
    context_only = render_main(probe, squeezed, 0.1, full_store=full, scope="context").texts
    t = probe.target_index
    assert target_only[t] == "X" and all(x != "X" for i, x in enumerate(target_only) if i != t)
    assert context_only[t] != "X" and all(x == "X" for i, x in enumerate(context_only) if i != t)
    with pytest.raises(ValueError, match="scope"):
        render_main(probe, squeezed, 0.1, full_store=full, scope="everything")
