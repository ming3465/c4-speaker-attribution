"""End-to-end: runner CLI on the fixture (stub reader, no model), analyzer, v1 regression."""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "evaluation" / "run_attribution_frozen.py"
ANALYZER = ROOT / "scripts" / "evaluation" / "analyze_attribution_frozen.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "utterances_small.jsonl"
TAG = "uniform_compression_stub_utterances_small_win6s3"
BASE = ["--dataset", "utterances", "--utterances", str(FIXTURE), "--contexts", "window",
        "--window-size", "6", "--window-stride", "3", "--reader", "stub"]


def runner_fields() -> list[str]:
    spec = importlib.util.spec_from_file_location("run_attribution_frozen", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FIELDS


def run(script: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    return subprocess.run([sys.executable, str(script), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=300)


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("run")
    return out, run(RUNNER, *BASE, "--skip-gate", "--out-dir", str(out))


def test_stub_run_completes_with_new_schema_and_provenance(full_run):
    out, result = full_run
    assert result.returncode == 0, result.stderr
    header, rows = read_csv(out / f"attribution_frozen_{TAG}.csv")
    assert header == runner_fields()
    assert rows and all(r["valid"] == "True" and not r["error"] for r in rows)
    keys = [(r["probe_id"], r["budget"], r["condition"]) for r in rows]
    assert len(keys) == len(set(keys))
    assert {r["cluster_id"] for r in rows} <= {"m1", "m2"}
    assert {r["dataset"] for r in rows} == {"utterances"}
    manifest = json.loads((out / f"attribution_frozen_{TAG}.manifest.json").read_text())
    assert manifest["status"] == "complete" and manifest["rows"] == len(rows)
    assert manifest["dataset"][0]["path"] == "tests/fixtures/utterances_small.jsonl"
    assert (out / f"attribution_frozen_{TAG}.gate.json").exists()


def test_rerun_resumes_without_new_rows(full_run):
    out, _ = full_run
    before = len(read_csv(out / f"attribution_frozen_{TAG}.csv")[1])
    result = run(RUNNER, *BASE, "--skip-gate", "--out-dir", str(out))
    assert result.returncode == 0
    assert "0 to run" in result.stdout
    assert len(read_csv(out / f"attribution_frozen_{TAG}.csv")[1]) == before


def test_gate_stops_the_sweep(tmp_path):
    result = run(RUNNER, *BASE, "--gate-margin", "0.99", "--out-dir", str(tmp_path))
    assert result.returncode == 3
    _, rows = read_csv(tmp_path / f"attribution_frozen_{TAG}.csv")
    assert rows and {r["budget"] for r in rows} == {"1.0"}      # only the gate ran
    manifest = json.loads((tmp_path / f"attribution_frozen_{TAG}.manifest.json").read_text())
    assert manifest["status"] == "stopped_at_gate" and manifest["gate"]["passed"] is False


def test_retrieval_contexts_need_questions(tmp_path):
    result = run(RUNNER, "--dataset", "utterances", "--utterances", str(FIXTURE),
                 "--reader", "stub", "--out-dir", str(tmp_path))
    assert result.returncode == 2 and "needs questions" in result.stderr


def test_refuses_to_append_to_a_legacy_schema_csv(tmp_path):
    legacy = runner_fields()[:-5]
    (tmp_path / f"attribution_frozen_{TAG}.csv").write_text(",".join(legacy) + "\n")
    result = run(RUNNER, *BASE, "--skip-gate", "--out-dir", str(tmp_path))
    assert result.returncode == 2 and "schema differs" in result.stderr


def test_controls_only_prints_checks(tmp_path):
    result = run(RUNNER, *BASE, "--controls", "--out-dir", str(tmp_path))
    assert result.returncode == 0 and "invariant violations: 0" in result.stdout
    assert not list(tmp_path.iterdir())


def test_analyzer_writes_named_tables_with_provenance(full_run, tmp_path):
    out, _ = full_run
    csv_path = out / f"attribution_frozen_{TAG}.csv"
    result = run(ANALYZER, "--csv", str(csv_path), "--out-dir", str(tmp_path))
    assert result.returncode == 0, result.stderr
    text = (tmp_path / f"{csv_path.stem}_tables.md").read_text()
    assert "## Table 2 — paired dose-response" in text
    assert "| Turn-taking heuristic |" in text                      # new-schema rows carry it
    assert "| Lexical attributor |" in text
    assert "## Table 5 — what the data can rule out" in text and "Detectable at 80% power" in text
    assert "## Provenance" in text and "Headroom gate" in text
    assert "predate run manifests" not in text                      # new-schema rows
    assert (tmp_path / f"{csv_path.stem}_summary.json").exists()


def test_analyzer_can_score_the_lexical_attributor(full_run, tmp_path):
    out, _ = full_run
    csv_path = out / f"attribution_frozen_{TAG}.csv"
    result = run(ANALYZER, "--csv", str(csv_path), "--out-dir", str(tmp_path), "--score", "lexical")
    assert result.returncode == 0, result.stderr
    text = (tmp_path / f"{csv_path.stem}_lexical_tables.md").read_text()
    assert "Scored: the lexical TF-IDF attributor" in text
    assert "## Table 2 — paired dose-response" in text and "## Table 4" in text


def test_v1_grader_no_longer_credits_substring_names():
    from src.evaluation.attribution_probe import AttributionItem, grade
    item = AttributionItem(qid="q", budget=0.5, target_text="t", gold_author="User_1", gold_role="",
                           candidates=["User_1", "User_13"], snippets=[], n_speakers=2)
    assert grade(item, "User_1")
    assert not grade(item, "User_13")
    assert not grade(item, "User_12")        # off-roster name that contains "User_1"
