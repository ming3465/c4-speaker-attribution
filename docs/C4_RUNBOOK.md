# C4 Runbook — Compression-Induced Attribution Failure

**Question.** After a memory is compressed, can a reader still tell *who* said
a statement in a multi-party conversation, and does that ability degrade with
the compression budget?

**Status.** Instrument complete and tested (79 tests). AMI main result: compression cuts `qwen2.5:14b` attribution by 9.2 pts at budget 0.1 — full write-up in [`C4_MAIN_STUDY.md`](C4_MAIN_STUDY.md). The GroupMemBench
pilot is a floor result — see [`PILOT_RESULTS.md`](PILOT_RESULTS.md). The AMI
meeting study is registered in [`C4_ANALYSIS_PLAN.md`](C4_ANALYSIS_PLAN.md)
(committed before any AMI output) and runs through the data contract below.

---

## 1. Setup

```bash
uv sync                                   # creates .venv with pytest (dev group)
PYTHONHASHSEED=0 uv run pytest -q         # 78 tests, ~2 s
ollama serve                              # local reader; or point --ollama-url at the GPU box
ollama pull qwen2.5:7b
```

Always run with `PYTHONHASHSEED=0`. Probe construction is deterministic across
hash seeds and across Python 3.13 / 3.14 (tested), but manifests record the
seed so a reviewer can confirm it.

## 2. Data contract (AMI, ELITR, or any multi-party transcript)

One utterance per JSONL line:

```json
{"conversation_id": "ES2002a", "turn_index": 14, "speaker": "B", "text": "so the budget is twelve fifty", "role": "PM", "start_time": 312.4}
```

| Field | Required | Rule |
| --- | --- | --- |
| `conversation_id` | yes | non-empty string; one meeting / chat |
| `turn_index` | yes | integer ≥ 0, unique within its conversation; defines order |
| `speaker` | yes | non-empty string; only needs to be consistent within a conversation |
| `text` | yes | string (backchannels allowed — filter with `--min-target-words`) |
| `role` | no | string |
| `start_time` | no | number, seconds from meeting start (not a date) |

The loader (`src/datasets/utterances.py`) fails fast with the file and line
number on any violation, and warns about single-speaker conversations (they
yield no probes). No labels are needed: attribution gold is the `speaker`
field itself.

**Converting AMI** (manual annotations v1.6.2, CC BY 4.0, 23 MB):

```bash
curl -LO https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
unzip ami_public_manual_1.6.2.zip -d data/raw/ami
uv run python scripts/data/convert_ami.py      # 171 meetings, 83,868 utterances, ~3 s
```

One utterance per transcriber segment, ordered by start time across speakers;
`speaker` = `Speaker_<letter>`, `role` = PM / ME / UI / ID where the meeting
has one (never shown to the reader). **ELITR**: same mapping with its meeting
ids and speaker tags.

## 3. Running a study

```bash
R="scripts/evaluation/run_attribution_frozen.py"
DATA="--dataset utterances --utterances data/processed/ami.jsonl --contexts window \
      --window-size 20 --window-stride 10 --min-target-words 8 \
      --budgets 1.0 0.5 0.25 0.1 --allocation per-message --limit 1200"   # the registered AMI design

# a. construction checks only -- no model calls
PYTHONHASHSEED=0 uv run python $R $DATA --controls

# b. plumbing check -- stub reader, no model
PYTHONHASHSEED=0 uv run python $R $DATA --reader stub --skip-gate --limit 20 --out-dir /tmp/c4-stub

# c. the real run: budget 1.0 first, headroom gate, then the sweep
PYTHONHASHSEED=0 uv run python $R $DATA --model qwen2.5:7b

# d. tables
uv run python scripts/evaluation/analyze_attribution_frozen.py \
    --csv results/proposed/attribution_v2/attribution_frozen_<tag>.csv
```

**The headroom gate.** Step (c) runs the uncompressed probes first. It sweeps
only if the lower 95% bound of (Hit@1 − chance) exceeds `--gate-margin`
(default 0.05) **and** the lower 95% bound of (Hit@1 − the stronger label-only
heuristic) exceeds 0. The label-only heuristics are *frequency* (the most
labelled speaker) and, on conversation windows, *turn-taking* (anyone but the
neighbouring speakers — about 7 pts above chance on AMI). Compression cannot
touch either, so a reader that only matches them has nothing to lose.
Otherwise the runner exits with code 3 and writes `<tag>.gate.json`. Declare
the margin before running. `--skip-gate` is an explicit override. Record why
if you use it.

**Useful flags**

| Flag | Purpose |
| --- | --- |
| `--compressor salient\|prefix\|summary` | word-dropping (pilot default) vs LLM per-message summaries |
| `--allocation pooled\|per-message` | word-drop budget: pooled per conversation (pilot) or `round(b × words)` of every message, matching the summarizer — use `per-message` on meetings |
| `--summarizer-model` | model for `summary`; summaries are cached in `results/cache/` |
| `--compress-scope both\|target\|context` | localize where binding breaks |
| `--window-size / --window-stride` | context size; larger windows → larger rosters |
| `--top-k` | retrieval context size (GroupMemBench only) |
| `--ollama-url http://gpu-box:11434` | run the reader or summarizer on the GPU machine |
| `--limit N` | first N probes of a deterministic shuffle — still a random, paired subsample |

Runs append row by row and resume where they stopped; any prefix is paired
across budgets. The runner refuses to append to a CSV with a different
schema (exit 2) — use a new `--out-dir`.

**Tables.** Table 1 accuracy by budget with chance, the frequency and
turn-taking heuristics, and a lexical TF-IDF attributor computed on the same
compressed text; Table 2 paired change vs 1.0 with McNemar; Table 3 by roster
size; Table 4 label swap; Table 5 what each estimate can rule out (90% CI,
detectable effect at 80% power, effect / no effect beyond the margin /
inconclusive).

**Outputs** (next to each CSV): `<tag>.manifest.json` (git commit + dirty
flag, dataset sha256, every argument, model digest, hash seed, Python version,
ISO 8601 UTC timestamps, row count, gate result, summary counts) and
`<tag>.gate.json`. The analyzer prints both under **Provenance**.

**Cost.** Word-drop runs: ~2 s per reader call on an M1 Pro (7B, 4-bit).
Summaries: ~5–10 s each locally, and one per (message, budget) — run
`--compressor summary` against the GPU box.

## 4. Reproducing the GroupMemBench pilot

```bash
PYTHONHASHSEED=0 uv run python $R --controls        # 542 probes, 161 questions, 0 violations
PYTHONHASHSEED=0 uv run python $R                   # 542/542 gate rows done -> gate FAIL, exit 3
PYTHONHASHSEED=0 uv run python $R --skip-gate       # 3140/3140 sweep rows done, 0 to run
uv run python scripts/evaluation/analyze_attribution_frozen.py
```

Expected: gate lift **+3.4 pts [−0.8, +7.4]** vs margin +5.0 → FAIL; Hit@1
41.7 / 41.7 / 41.7 / 41.0 / 39.7% at budgets 1.0 → 0.1 against 38.3% chance.
The pilot's probes and all 3,682 prompts are fingerprinted in
`tests/test_attribution_frozen.py`; any change to them fails the suite. The
raw pilot CSV is gitignored and regenerates deterministically (~2 h with the
reader).

## 5. Code status

| Path | Status |
| --- | --- |
| `src/evaluation/attribution_frozen.py` | **current** — contexts, frozen probes, rendering, grading, readers |
| `src/evaluation/attribution_compressors.py` | **current** — word-drop and summary compressors |
| `src/evaluation/attribution_gate.py`, `attribution_stats.py` | **current** — headroom gate; cluster bootstrap, McNemar |
| `src/evaluation/ollama_client.py`, `run_manifest.py` | **current** — HTTP client; run provenance |
| `src/datasets/utterances.py` | **current** — data contract loader |
| `src/datasets/ami.py`, `scripts/data/convert_ami.py` | **current** — AMI annotations → data contract |
| `scripts/evaluation/run_attribution_frozen.py`, `analyze_attribution_frozen.py` | **current** — runner, analysis |
| `src/evaluation/attribution_probe.py`, `run_attribution_probe.py`, `analyze_attribution.py` | superseded — C4 v1 (probes re-drawn per budget) |
| `src/evaluation/reader_pass.py`, `run_reader_pass.py` | pilot — C4 v0 reader pass (original decomposition, scooped) |
| `src/memory/*`, `src/interpretation/*`, `run_consumer_prediction.py`, `run_provenance_ablation.py` | pilot skeletons — lexical C1–C3 prototypes; current C1–C3 work lives outside this repo |
| `src/evaluation/failure_decomposition.py` | shared instrument — do not modify (the pilot's stores depend on it) |

## 6. After the GPU: the AHN-layer probe (design only)

The text probe asks whether a *compressed message* still carries its
speaker. The AHN version asks whether AHN's *compressed hidden state* does:

1. Build a long multi-party transcript from the same contract; render it with
   speaker tags.
2. Place early turns so they fall **outside** the sliding window and are
   absorbed into AHN's recurrent memory; keep later turns inside the window.
3. Ask "who said X?" about a statement whose speaker is identifiable only from
   the out-of-window turns.
4. Compare full attention (lossless), sliding window only (no compressed
   memory), and AHN. `Δ_mem = φ(AHN) − φ(SWA)` is what the compressed memory
   contributes to speaker binding; AHN's own RULER result (Δ_mem ≈ 0 on exact
   recall) predicts it is near zero.

Same discipline as the text probe: headroom gate on full attention first,
frozen probes, a paired sweep over window size, and a declared margin.
