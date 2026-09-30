# PC Handoff — Remaining C4 GPU Runs

*Written 2026-09-30. Hardware: Windows PC with an RTX 2070 Super (8 GB). The
laptop session ends here, and work continues in Claude Code on the PC.*

## For the next Claude Code session: read these first

The main result is done, committed and written up:

- **Main result.** On 1,200 frozen AMI probes, compressing each statement to a
  tenth of its words cut `qwen2.5:14b` speaker attribution by
  **9.2 pts [−12.3, −6.0]**.
- **Full write-up.** [`docs/C4_MAIN_STUDY.md`](C4_MAIN_STUDY.md): method,
  results, deviations, and how to reproduce.
- **Registered plan and results log.** [`docs/C4_ANALYSIS_PLAN.md`](C4_ANALYSIS_PLAN.md).
  Log any new run here under *Deviations* or *Results*.
- **How to run anything.** [`docs/C4_RUNBOOK.md`](C4_RUNBOOK.md).
- **Rendered tables.** `results/comparisons/attribution_v2/`.
- **Mentor-facing report.** A Claude Docs page, "C4 Report: Speaker Attribution
  Under Memory Compression", with a to-do list.
- **Older, different framing.** [`docs/C4_HANDOFF.md`](C4_HANDOFF.md), from
  Sep 7, covers provenance arms on GroupMemBench. It is not this study. The
  mentor decides whether it continues.

**Rules the study follows.**

- Probes are frozen once and compared paired across budgets.
- No compression sweep runs without a passing headroom gate.
- Any change goes under *Deviations* with its reason.
- Every reader is reported separately, never pooled.
- `qwen2.5:72b` is dropped: the paper reports readers up to 32B.

The PC runs **extensions** to that result, not the result itself.

## What the PC can and cannot run

The RTX 2070 Super has 8 GB of VRAM, and that decides what fits. All times
below are estimates. The speed test in step 4 gives the real figure.

| Run | Fits? | Estimated time |
| --- | --- | --- |
| Speed test, 20 probes per model | yes | minutes |
| LLM-summary compressor: `qwen2.5:7b` writes 43,704 summaries, then `qwen2.5:14b` reads | yes | ~6–12 h of summaries, then ~3–6 h of reading |
| `qwen2.5:32b` reader (~20 GB) | only if most of the model is in system RAM (needs ≥ 32 GB RAM) | slow, likely a day or more |
| Bigger label-swap arm | not yet | the runner needs a swap-only option first |
| ELITR replication | not yet | the converter is not written yet |

Run the summarizer first. It is the extension this PC is best suited to.

## 1. One-time setup (PowerShell)

1. Update the NVIDIA driver (GeForce Experience, or nvidia.com/drivers).
2. Install Git from git-scm.com and Ollama from ollama.com/download. Then
   install uv:

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. Close and reopen PowerShell, then fetch the models and the code:

   ```powershell
   ollama pull qwen2.5:7b
   ollama pull qwen2.5:14b
   git clone https://github.com/ming3465/c4-speaker-attribution.git
   cd c4-speaker-attribution
   uv sync
   uv run pytest -q
   ```

**Check:** the tests print **76 passed, 3 skipped**. The skipped tests need
GroupMemBench pilot data, which is deliberately not in the public repo; see
`data/README.md`.

4. Keep the PC awake while plugged in. In Windows Settings, go to
   **System → Power**, and set sleep to **Never** for when plugged in.

## 2. Get the AMI transcripts (one time, about 1 minute)

```powershell
curl.exe -LO https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
Expand-Archive ami_public_manual_1.6.2.zip -DestinationPath data\raw\ami
uv run python scripts/data/convert_ami.py
```

**Check:** it prints `171 meetings, 83868 utterances`.

## 3. Load the registered design into this PowerShell window

Run this in every new PowerShell window before the run commands.

```powershell
$env:PYTHONHASHSEED = "0"
$A = @("--dataset","utterances","--utterances","data/processed/ami.jsonl","--contexts","window",
       "--window-size","20","--window-stride","10","--min-target-words","8",
       "--budgets","1.0","0.5","0.25","0.1","--limit","1200")
```

## 4. Speed test first (minutes)

```powershell
uv run python scripts/evaluation/run_attribution_frozen.py @A --allocation per-message --model qwen2.5:14b --limit 20 --skip-gate --out-dir results/speedtest
ollama ps
```

**Check:** `ollama ps` shows how the model is split between CPU and GPU. Each
row of `results/speedtest/*.csv` records `latency_s`, the seconds per call.
Average it to estimate the full run. On the laptop's M1 Pro, 14B took about
5.2 s per call.

## 5. Main PC run: the LLM-summary compressor

```powershell
uv run python scripts/evaluation/run_attribution_frozen.py @A --compressor summary --summarizer-model qwen2.5:7b --model qwen2.5:14b
```

- **Order of work.** It writes all 43,704 summaries first, then runs the
  headroom gate, then the sweep if the gate passes.
- **Where summaries go.** They are cached in
  `results/cache/summaries_qwen2.5-7b.jsonl`.
- **Stopping and resuming.** If the PC restarts, run the same command again.
  Cached summaries and finished rows are skipped.
- **Clipping.** Summaries longer than their word budget are clipped. The
  manifest records how many were clipped.
- **Do not add `--controls` here.** For this compressor it still generates
  every summary before printing the checks.
- **Log it.** This is an extension: record it in `docs/C4_ANALYSIS_PLAN.md`
  under *Deviations* before reading its results.

## 6. Optional: `qwen2.5:32b` (slow)

Only try this if the PC has at least 32 GB of RAM. Speed-test it first
(step 4 with `--model qwen2.5:32b`), then run:

```powershell
ollama pull qwen2.5:32b
uv run python scripts/evaluation/run_attribution_frozen.py @A --allocation per-message --model qwen2.5:32b
```

## 7. After a run: tables and results

1. Render the tables:

   ```powershell
   uv run python scripts/evaluation/analyze_attribution_frozen.py --csv (Get-ChildItem results/proposed/attribution_v2/*summary*.csv).FullName
   ```

2. Commit and push the rendered tables. The `*_tables.md` files in
   `results/comparisons/attribution_v2/` are tracked; the raw CSVs and JSON
   files are not:

   ```powershell
   git add results/comparisons docs
   git commit -m "results: AMI with LLM-summary compressor (qwen2.5:14b reader)"
   git push
   ```

3. Update `docs/C4_MAIN_STUDY.md`, the plan's *Results* section, and the
   report's to-do list with the new numbers.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ollama` not recognised | Reopen PowerShell after installing, or start the Ollama app |
| `could not connect to ollama server` | Start the Ollama app from the Start menu |
| `ollama ps` shows `100% CPU` | Update the NVIDIA driver, then restart Ollama |
| Out of memory with 32B | The PC lacks RAM for 32B; skip step 6 |
| The run exits with code 3 | The headroom gate failed. That is a result, so report it; do not re-run with `--skip-gate` |
| The run exits with code 2 and a schema message | The output folder holds an older CSV; pass a new `--out-dir` |

## Still open (not PC runs)

- Figure script for paper-quality charts.
- ELITR converter.
- Swap-only runner option, for the bigger swap arm.
- Mentor decisions: the ±5 pt margin, which readers, whether the Sep 7
  handoff's framing continues, and AHN scope.
