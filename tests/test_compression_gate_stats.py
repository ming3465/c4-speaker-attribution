"""Compressors, headroom gate, shared statistics, and the Ollama client/readers."""
from __future__ import annotations

import io
import json
import math

import pytest

from src.evaluation import ollama_client
from src.evaluation.attribution_compressors import (
    SummaryCompressor,
    WordDropCompressor,
    cache_key,
    cap_words,
    target_words,
)
from src.evaluation.attribution_frozen import JSON_INSTRUCTION, OllamaHTTPReader, StubReader
from src.evaluation.attribution_gate import evaluate_gate, write_gate
from src.evaluation.attribution_stats import (
    Z_ALPHA,
    Z_POWER,
    cluster_ci,
    mcnemar_exact,
    sensitivity,
)
from src.evaluation.failure_decomposition import MemoryUnit
from src.evaluation.ollama_client import OllamaClient

LONG = "one two three four five six seven eight nine ten eleven twelve"


def mk(uid, text, author="A", group="g"):
    return MemoryUnit(uid=uid, group=group, text=text, author=author, role="", order=int(uid[-1]))


class FakeClient:
    """Stands in for OllamaClient; records calls instead of hitting a server."""

    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def generate(self, model, prompt, *, options=None, format=None):
        self.calls.append({"model": model, "prompt": prompt, "options": options, "format": format})
        return self.reply


# --------------------------------------------------------------------------
# compressors
# --------------------------------------------------------------------------

def test_budget_rule_and_word_cap():
    assert target_words(12, 0.25) == 3
    assert target_words(3, 0.1) == 1          # never below one word
    assert cap_words("a b c d", 2) == "a b"
    assert cache_key("m", 3, "x") != cache_key("m", 4, "x")


def test_word_drop_shrinks_text_with_budget():
    units = [mk("u0", LONG), mk("u1", LONG, author="B")]
    stores = WordDropCompressor().compress(units, [1.0, 0.25])
    assert len(stores[0.25]["u0"].split()) < len(stores[1.0]["u0"].split())


def test_per_message_word_drop_keeps_the_same_fraction_of_every_message():
    units = [mk("u1", LONG), mk("u2", "short note here"), mk("u3", "ok")]      # 12, 3, 1 words
    stores = WordDropCompressor(allocation="per-message").compress(units, [1.0, 0.5, 0.25])
    assert stores[1.0]["u1"] == LONG
    assert [len(stores[0.5][u].split()) for u in ("u1", "u2", "u3")] == [6, 2, 1]
    assert [len(stores[0.25][u].split()) for u in ("u1", "u2", "u3")] == [3, 1, 1]
    kept = stores[0.5]["u1"].split()
    assert kept == [w for w in LONG.split() if w in kept]                    # original order
    with pytest.raises(ValueError, match="allocation"):
        WordDropCompressor(allocation="bogus").compress(units, [0.5])


def test_summary_identity_at_full_budget_and_for_short_text(tmp_path):
    client = FakeClient("should not be used")
    comp = SummaryCompressor(client, "fake", tmp_path / "cache.jsonl")
    stores = comp.compress([mk("u0", LONG), mk("u1", "hi")], [1.0, 0.5])
    assert stores[1.0]["u0"] == LONG
    assert stores[0.5]["u1"] == "hi"           # 1 word <= k=1: already within budget
    assert len(client.calls) == 1              # only u0 at 0.5 needed a summary


def test_summary_is_capped_counted_and_cached(tmp_path):
    cache = tmp_path / "cache.jsonl"
    client = FakeClient("this summary is far too long for the budget")
    comp = SummaryCompressor(client, "fake", cache)
    out = comp.compress([mk("u0", LONG)], [0.25])[0.25]["u0"]
    assert out == "this summary is"            # k = 3 words
    assert (comp.generated, comp.clipped) == (1, 1)
    assert client.calls[0]["options"]["temperature"] == 0
    # a fresh compressor on the same cache makes no model call
    again_client = FakeClient("different")
    again = SummaryCompressor(again_client, "fake", cache)
    assert again.compress([mk("u0", LONG)], [0.25])[0.25]["u0"] == "this summary is"
    assert again_client.calls == []
    assert json.loads(cache.read_text().splitlines()[0])["k"] == 3


def test_summary_only_touches_requested_uids(tmp_path):
    client = FakeClient("short")
    comp = SummaryCompressor(client, "fake", tmp_path / "c.jsonl")
    stores = comp.compress([mk("u0", LONG), mk("u1", LONG)], [0.5], only_uids={"u1"})
    assert set(stores[0.5]) == {"u1"}


# --------------------------------------------------------------------------
# gate
# --------------------------------------------------------------------------

def rows(correct_flags, chance=0.5, freq=0.4):
    return [{"correct": c, "chance": chance, "freq_baseline": freq, "cluster_id": f"c{i}"}
            for i, c in enumerate(correct_flags)]


def test_gate_fails_when_turn_taking_heuristic_wins():
    flags = [True] * 45 + [False] * 5
    result = evaluate_gate([{**r, "turn_baseline": 0.95} for r in rows(flags)], margin=0.05)
    assert not result.passed and "turn-taking heuristic" in result.reason
    assert result.turn_taking == pytest.approx(0.95)
    legacy = evaluate_gate(rows(flags), margin=0.05)          # pilot rows carry no turn baseline
    assert legacy.passed and math.isnan(legacy.turn_taking)


def test_gate_passes_with_clear_headroom():
    result = evaluate_gate(rows([True] * 45 + [False] * 5), margin=0.05)
    assert result.passed and result.lift_lo > 0.05 and result.reason == "headroom confirmed"


def test_gate_fails_when_lower_bound_is_below_margin():
    result = evaluate_gate(rows([True, False] * 25), margin=0.05)   # accuracy == chance
    assert not result.passed and "lower bound" in result.reason


def test_gate_fails_when_frequency_heuristic_wins():
    result = evaluate_gate(rows([True] * 40 + [False] * 10, freq=0.9), margin=0.05)
    assert not result.passed and "frequency heuristic" in result.reason


def test_gate_needs_a_significant_lead_over_the_best_heuristic():
    flags = [True] * 28 + [False] * 32                                   # 46.7% vs frequency 45%
    result = evaluate_gate(rows(flags, chance=0.2, freq=0.45), margin=0.05)
    assert result.lift_lo > 0.05                                         # clears chance + margin
    assert not result.passed and "frequency heuristic" in result.reason
    assert result.over_heuristic_lo < 0 < result.over_heuristic


def test_gate_fails_closed_without_rows(tmp_path):
    result = evaluate_gate([])
    assert not result.passed and result.n == 0
    write_gate(tmp_path / "g.json", result)
    text = (tmp_path / "g.json").read_text()
    assert json.loads(text)["passed"] is False and "NaN" not in text     # strict JSON


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------

def test_mcnemar_exact_known_values():
    assert mcnemar_exact(0, 5) == pytest.approx(0.0625)
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(3, 7) == mcnemar_exact(7, 3)


def test_cluster_ci_constant_and_empty():
    assert cluster_ci([("a", 0.5), ("b", 0.5)]) == (0.5, 0.5, 0.5)
    assert all(math.isnan(x) for x in cluster_ci([]))


def test_cluster_ci_resamples_clusters_not_rows():
    # one cluster holds all the variation: the CI must be as wide as picking it or not
    point, lo, hi = cluster_ci([("a", 1.0)] * 10 + [("b", 0.0)] * 10)
    assert point == 0.5 and lo == 0.0 and hi == 1.0


def test_sensitivity_on_constant_data_is_exact():
    s = sensitivity([("a", 0.02), ("b", 0.02)], margin=0.05)
    assert (s.point, s.lo90, s.hi90, s.se, s.mde) == (0.02, 0.02, 0.02, 0.0, 0.0)
    assert s.significant and s.equivalent and s.reading == "real but inside the margin"


def test_sensitivity_shares_draws_with_the_reported_ci():
    items = [(f"c{i % 7}", float(i % 3 == 0)) for i in range(60)]
    point, lo95, hi95 = cluster_ci(items)
    s = sensitivity(items, margin=0.05)
    assert (s.point, s.lo95, s.hi95) == (point, lo95, hi95)
    assert lo95 <= s.lo90 <= s.hi90 <= hi95
    assert s.mde == pytest.approx((Z_ALPHA + Z_POWER) * s.se) and s.mde > 0


def test_sensitivity_separates_no_effect_from_inconclusive():
    tight = sensitivity([(f"c{i}", 0.01 if i % 2 else -0.01) for i in range(40)], margin=0.05)
    wide = sensitivity([(f"c{i}", 1.0 if i % 2 else -1.0) for i in range(40)], margin=0.05)
    assert tight.equivalent and not tight.significant and tight.reading == "no effect beyond the margin"
    assert not wide.equivalent and not wide.significant and wide.reading == "inconclusive"
    shifted = sensitivity([(f"c{i}", 0.5 + 0.01 * (i % 2)) for i in range(40)], margin=0.05)
    assert shifted.significant and not shifted.equivalent and shifted.reading == "effect"


def test_sensitivity_fails_closed_without_items():
    s = sensitivity([], margin=0.05)
    assert math.isnan(s.mde) and not s.equivalent and s.reading == "inconclusive"


# --------------------------------------------------------------------------
# ollama client and readers
# --------------------------------------------------------------------------

@pytest.fixture
def fake_urlopen(monkeypatch):
    sent = []

    def urlopen(request, timeout):
        body = json.loads(request.data) if request.data else None
        sent.append({"url": request.full_url, "body": body, "timeout": timeout})
        if request.full_url.endswith("/api/tags"):
            payload = {"models": [{"name": "qwen2.5:7b", "digest": "abc123"}]}
        else:
            payload = {"response": '{"author": "B"}'}
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(ollama_client.urllib.request, "urlopen", urlopen)
    return sent


def test_client_generate_sends_format_only_when_given(fake_urlopen):
    client = OllamaClient("http://box:1234/")
    client.generate("m", "p", options={"temperature": 0})
    client.generate("m", "p", format={"type": "object"})
    assert fake_urlopen[0]["url"] == "http://box:1234/api/generate"
    assert "format" not in fake_urlopen[0]["body"] and fake_urlopen[1]["body"]["format"] == {"type": "object"}


def test_client_model_digest(fake_urlopen):
    client = OllamaClient()
    assert client.model_digest("qwen2.5:7b") == "abc123"
    assert client.model_digest("missing") == ""


def test_reader_constrains_to_roster(fake_urlopen):
    answer = OllamaHTTPReader(base_url="http://h:1").answer("PROMPT", choices=["A", "B"])
    body = fake_urlopen[0]["body"]
    assert answer == "B"
    assert body["prompt"] == "PROMPT" + JSON_INSTRUCTION
    assert body["format"]["properties"]["author"]["enum"] == ["A", "B"]
    assert body["options"] == {"temperature": 0, "seed": 0, "num_predict": 32, "num_ctx": 8192}


def test_reader_sends_the_context_window_it_was_given(fake_urlopen):
    """Left to itself Ollama uses 4096 and truncates longer prompts silently."""
    OllamaHTTPReader(base_url="http://h:1", num_ctx=16384).answer("PROMPT", choices=["A"])
    assert fake_urlopen[0]["body"]["options"]["num_ctx"] == 16384


def test_reader_returns_raw_text_when_json_is_malformed(monkeypatch):
    monkeypatch.setattr(OllamaClient, "generate", lambda self, *a, **k: "not json")
    assert OllamaHTTPReader().answer("p", choices=["A"]) == "not json"


def test_stub_reader_answers_first_roster_name():
    assert StubReader().answer("p", choices=["X", "Y"]) == "X"
    assert StubReader().answer("p") == ""


# --------------------------------------------------------------------------
# run manifest
# --------------------------------------------------------------------------

def test_manifest_records_portable_paths_hashes_and_roundtrips(tmp_path):
    import hashlib
    from pathlib import Path

    from src.evaluation.run_manifest import (
        build_manifest, file_sha256, git_state, portable_path, read_manifest, utc_now, write_manifest,
    )
    root = Path(__file__).resolve().parents[1]
    data = tmp_path / "d.jsonl"
    data.write_text("x\n")
    assert file_sha256(data) == hashlib.sha256(b"x\n").hexdigest()
    assert portable_path(root / "tests" / "conftest.py", root) == "tests/conftest.py"
    assert portable_path(data, root) == str(data)          # outside the repo: left absolute
    state = git_state(root)
    assert set(state) == {"git_commit", "git_dirty"}
    assert git_state(tmp_path) == {"git_commit": None, "git_dirty": None}   # not a repo
    manifest = build_manifest(root=root, args={"out": root / "results", "n": 3}, dataset_files=[data],
                              model="m", model_digest="d", started_utc=utc_now())
    assert manifest["args"] == {"out": "results", "n": 3}
    assert manifest["dataset"][0]["sha256"] == file_sha256(data)
    assert manifest["started_utc"].endswith("+00:00")
    write_manifest(tmp_path / "m.json", manifest)
    assert read_manifest(tmp_path / "m.json") == manifest
    assert read_manifest(tmp_path / "absent.json") is None
