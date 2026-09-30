# PC Handoff — Remaining C4 GPU Runs

*Written 2026-09-30. Work continues in Claude Code on the PC (Windows, RTX
2070 Super). All GPU runs go to one rented Runpod A40 (see the next section).
The PC sections below remain as a fallback.*

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

## Decided 2026-09-30: all GPU runs on one Runpod A40

Every GPU run goes to **one A40 pod** on Runpod ($0.49/hr on Secure Cloud).
The PC does not run models. Claude Code on the PC writes the code, starts the
pod and analyses the results. The runbook for the pod is the **Fallback: rent
an A40 on Runpod** section below.

**Do the code first, before renting.** An idle pod still bills.

1. **Check licences** for ICSI and the high-signal corpus (Supreme Court oral
   arguments via ConvoKit, or parliamentary debates). Record the result in
   `data/README.md`.
2. **Write converters** to the utterance contract, following the pattern of
   `src/datasets/ami.py`, with tests. The ICSI release on the Edinburgh site
   uses the same NXT format as AMI, so reuse that code.
   - `src/datasets/icsi.py`
   - `src/datasets/elitr.py`
   - one converter for the high-signal corpus
3. **Add jobs to `scripts/runpod/bootstrap.sh`:** one per new corpus (a
   `DATASET` variable plus its download), and a swap-only job for the bigger
   label-swap arm. The swap-only job also needs a small runner option.
4. **Amend the plan.** Before any new run, add the new corpora and the swap
   arm to `docs/C4_ANALYSIS_PLAN.md`, with the same design and rules. Commit
   it.
5. **Rent one A40.** Check the credit first under runpod.io → Billing. Then
   run the jobs back to back in this order, so the most important results come
   first:

| Order | Job | Time (estimate) | Cost |
| --- | --- | --- | --- |
| 0 | Setup and model downloads (7B, 14B, 32B) | ~1 h | $0.50 |
| 1 | 32B on AMI (second passing reader) | ~2.5–3 h | ~$1.40 |
| 2 | Summarizer on AMI (7B summaries, 14B reader) | ~4–5 h | ~$2.25 |
| 3 | 14B + 32B on ELITR | ~4–4.5 h | ~$2.10 |
| 4 | 14B + 32B on ICSI | ~4–4.5 h | ~$2.10 |
| 5 | 14B + 32B on the high-signal corpus (long turns, slower) | ~6–9 h | ~$3.60 |
| 6 | Bigger label-swap arm (14B, AMI) | ~1 h | $0.50 |
| — | Disk, about 2 days | — | $0.60 |
| | **Total** | **~25–30 h, about 1.5 days** | **≈ $13–15** |

**Budget.**

- The total uses almost all of the $15 credit ($10 plus a $5 referral), with
  no room for reruns. Add about $5 of buffer, or drop step 6 if money runs
  short.
- A failed headroom gate makes that job about a fifth as expensive, because no
  sweep runs.
- **Stop the pod after the last job, and terminate it once the results are
  copied.**

**Out of scope for this budget:**

- the summarizer on the three new corpora (about $5 more);
- `qwen2.5:72b` (dropped);
- the AHN-layer probe.

## What the PC can and cannot run

The RTX 2070 Super has 8 GB of VRAM, and that decides what fits. All times
below are estimates. The speed test in step 4 gives the real figure.

| Run | Fits? | Estimated time |
| --- | --- | --- |
| Speed test, 20 probes per model | yes | minutes |
| LLM-summary compressor: `qwen2.5:7b` writes 43,704 summaries, then `qwen2.5:14b` reads | yes | ~6–12 h of summaries, then ~3–6 h of reading |
| `qwen2.5:32b` reader (~20 GB) | only if most of the model is in system RAM (needs ≥ 32 GB RAM); otherwise use the Runpod A40 fallback below | slow on the PC, likely a day or more; about 2–3 h on an A40 |
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

## Fallback: rent an A40 on Runpod

Use this when the PC cannot do a run, above all `qwen2.5:32b` on a PC with
less than 32 GB of RAM, or when you want a run finished faster.

- **Price.** Checked live on 2026-09-30: an A40 (48 GB) costs $0.49/hr on
  Secure Cloud. Stock was Low, in Montreal (CA-MTL-1) only. Community Cloud is
  $0.35/hr when it has stock. The L4 was sold out.
- **Budget.** The 32B run, the summarizer and the extras come to roughly
  10–14 h, or **about $5–7.50**. Check the balance under runpod.io → Billing:
  $10 was loaded, plus an expected $5 referral bonus. Runpod's tools cannot
  read the balance.
- **Status.** No pod has been created and nothing has been charged.

Steps, using Claude Code on the PC:

1. Install and sign in to the Runpod plugin:
   `claude plugin marketplace add runpod/runpod-plugins-official`, then
   `claude plugin install runpod@runpod`, then `/reload-plugins`, then `/mcp`
   → **runpod** → **Sign in with Runpod**. It signs in with OAuth, so no API
   key is created.
2. Add the PC's SSH public key under Runpod → Settings → SSH Public Keys. You
   need it to log in and copy results.
3. Create the pod: **A40**, Secure Cloud, the **Runpod PyTorch** template, a
   **100 GB volume mounted at `/workspace`**, and **TCP port 22** exposed.
   Claude should state the hourly price before creating it.
4. On the pod, in the web terminal or over SSH, inside `tmux` so jobs survive
   a disconnect:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/ming3465/c4-speaker-attribution/main/scripts/runpod/bootstrap.sh -o bootstrap.sh
   bash bootstrap.sh speedtest                    # qwen2.5:32b, 20 probes: seconds per call
   bash bootstrap.sh ami                          # qwen2.5:32b: gate, then sweep
   MODEL=qwen2.5:14b bash bootstrap.sh summary    # LLM-summary compressor
   ```

   Everything lives under `/workspace`, so a restarted pod resumes where it
   stopped.
5. Copy the results back. The pod page shows its IP and port:

   ```bash
   scp -P <port> -r root@<ip>:/workspace/results ./results/runpod
   ```

6. **Stop the pod when the runs finish.** It bills until it is stopped. A
   stopped pod still bills a little for its volume, so terminate it once the
   results are copied.

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
