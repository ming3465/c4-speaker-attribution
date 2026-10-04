# C4 Handoff — Remaining Work

*Updated 2026-09-30. Work continues in Claude Code on the PC (Windows). The PC
writes code and analyses results. **Every model run goes to one rented
Runpod A40**, and the PC does not run models.*

## 1. Where C4 stands (read first)

The main result is done, committed and written up.

- **Main result.** On 1,200 frozen AMI probes, compressing each statement to a
  tenth of its words cut `qwen2.5:14b` speaker attribution by
  **9.2 pts [−12.3, −6.0]** (McNemar p = 3×10⁻⁸).
- **Supporting results.**
  - The lexical attributor falls 48.8% → 32.6%.
  - `qwen2.5:7b` failed the headroom gate.
- **Write-up.** [`docs/C4_MAIN_STUDY.md`](C4_MAIN_STUDY.md) covers the method,
  results, deviations and how to reproduce them.
- **Registered plan and results log.**
  [`docs/C4_ANALYSIS_PLAN.md`](C4_ANALYSIS_PLAN.md). Log every new run there.
- **Runbook.** [`docs/C4_RUNBOOK.md`](C4_RUNBOOK.md) covers every flag, the
  gate and the output files.
- **Rendered tables.** `results/comparisons/attribution_v2/`.
- **Mentor-facing report.** A Claude Docs page, "C4 Report: Speaker
  Attribution Under Memory Compression".
- **Older, different framing.** [`docs/C4_HANDOFF.md`](C4_HANDOFF.md), from
  Sep 7, covers provenance arms on GroupMemBench. It is not this study, and
  the mentor decides whether it continues.

**Rules the study follows.**

- Probes are frozen once and compared paired across budgets.
- No compression sweep runs without a passing headroom gate.
- A gate failure is a result: never rerun with `--skip-gate` to get a sweep.
- Every reader is reported separately and never pooled.
- Any change or new run is logged in the plan before its results are read.
- `qwen2.5:72b` is dropped; the paper reports readers up to 32B.

## 2. The plan: all model runs on one A40

**GPU.** A40, 48 GB, Secure Cloud, **$0.49/hr**. Re-read live on 2026-10-05:
availability `LOW` in CA-MTL-1 and EU-SE-1, the only two data centers that
carry it. Community Cloud lists $0.35/hr but availability is `NONE`, so Secure
is the only option.

**Storage: a host-local persistent mount, not a network volume.** CA-MTL-1 and
EU-SE-1 both report `networkVolumeTypes: []` — neither supports network volumes
at all, so the A40 cannot have one. `/workspace` is instead `mounts.persistent`,
host-local storage available on any GPU pod. It survives stop/start but **not
pod termination or a host failure**, and Runpod marks it deprecated for data you
cannot recreate. The one artifact that is expensive to regenerate is the summary
cache (43,704 summaries, several GPU-hours), so **copy the cache and the CSVs
down after every job**, not just at the end.

**Why not a GPU that can take a network volume.** Every chip with at least
32 GB in a volume-capable data center costs far more, and 25–30 h of it does not
fit the credit: RTX PRO 4500 32 GB $0.72/hr (EU-RO-1), RTX 4090 24 GB $0.74/hr,
RTX 5090 32 GB $0.99/hr, PRO 6000 MIG 48 GB $1.09/hr (US-NE-1), RTX PRO 6000
96 GB $2.09/hr. The A40 at $0.49/hr is the only one inside budget. L40S is
$1.09/hr on Secure, not the $0.79 quoted earlier — that is its Community price,
and none of its data centers takes a volume either.

**Context fits.** `qwen2.5:32b` q4 is about 20 GB and a 16,384-token KV cache
about 4 GB, so the Supreme Court and ELITR runs at `NUM_CTX=16384` sit near
25 GB of the A40's 48 GB.

**Budget.**

- The credit is about $15 ($10 loaded, plus an expected $5 referral bonus).
  Check it under runpod.io → Billing. Runpod's tools report **spend**, not
  balance — `list-billing` showed $0.00 across the last 7 days, which confirms
  nothing has been charged yet but says nothing about what is available.
- **The gates cap the spend.** Jobs 3–5 are the expensive ones and the likeliest
  to fail their headroom gate, and a failed gate stops before the sweep:

  | Outcome | Jobs 3–5 | Campaign total |
  | --- | ---: | ---: |
  | All six gates fail | ~$2.50 | **≈ $8** |
  | All six gates pass | ~$8.10 | **≈ $14** |

  Either way the two AMI jobs — the highest-value ones — come first and cost
  about $4.40 combined. Still add ~$5 of buffer before renting: $14 against $15
  leaves nothing for a rerun.

**Order.** The most important results come first. All times are estimates;
the speed test gives the real figure.

| Job | What | Time | Cost |
| --- | --- | --- | --- |
| 0 | Pod setup; download 7B, 14B and 32B | ~1 h | $0.50 |
| 1 | `qwen2.5:32b` on AMI: the second passing reader | ~2.5–3 h | ~$1.40 |
| 2 | LLM-summary compressor on AMI: 43,704 summaries from 7B, read by 14B | ~4–5 h | ~$2.25 |
| 3 | 14B and 32B on ELITR | ~4–4.5 h | ~$2.10 |
| 4 | 14B and 32B on ICSI | ~4–4.5 h | ~$2.10 |
| 5 | 14B and 32B on the high-signal corpus (long turns, slower) | ~6–9 h | ~$3.60 |
| 6 | Bigger label-swap arm (14B, AMI) | ~1 h | $0.50 |
| — | Disk for about 2 days | — | $0.60 |
| | **Total** | **~25–30 h (about 1.5 days)** | **≈ $13–15** |

A failed gate makes that job about a fifth of the cost, because no sweep runs.

**Expect gate failures on jobs 3-5, and budget for them.** The label-only
shortcuts are far stronger on the new corpora than on AMI, and the gate demands
a significant lead over the stronger of the two. Measured with `--controls`,
before any reader ran:

| Corpus | Chance | Frequency | Turn-taking | Best shortcut, over chance |
| --- | ---: | ---: | ---: | ---: |
| AMI | 27.6% | 34.6% | 33.8% | +7.0 pts |
| ICSI | 30.8% | **55.2%** | 18.7% | +24.4 pts |
| ELITR | 33.5% | 36.1% | **54.9%** | +21.4 pts |
| Supreme Court | 23.7% | **42.6%** | 35.3% | +18.9 pts |

A reader has to beat those, not chance. That is a result either way, and a
failed gate costs about a fifth of its job -- but do not plan on three passing
sweeps.

**Out of scope for this budget:**

- the summarizer on the three new corpora (about $5 more);
- `qwen2.5:72b`;
- the AHN-layer probe.

## 3. PC setup (one time, PowerShell)

The PC only needs to write code and run tests, so it needs no Ollama and no
GPU.

1. Install Git from git-scm.com.
2. Install uv:

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. Reopen PowerShell, then get the code and run the tests:

   ```powershell
   git clone https://github.com/ming3465/c4-speaker-attribution.git
   cd c4-speaker-attribution
   uv sync
   uv run pytest -q
   ```

**Check:** the tests print **76 passed, 3 skipped**. The skipped tests need
GroupMemBench pilot data, which is deliberately not in the public repo; see
`data/README.md`.

## 4. Before renting: code (on the PC)

An idle pod still bills, so finish all of this first. Each item needs tests,
and the full suite must stay green.

1. **Check the licences** for ICSI and the high-signal corpus. The high-signal
   options are Supreme Court oral arguments (via ConvoKit) or parliamentary
   debates. Record the result in `data/README.md`. ELITR is already cleared:
   CC BY-NC-SA 4.0.
2. **Write the converters** to the utterance contract, following
   `src/datasets/ami.py` and `scripts/data/convert_ami.py`:
   - `src/datasets/icsi.py`. The Edinburgh ICSI release uses the same NXT XML
     as AMI, so reuse that code.
   - `src/datasets/elitr.py`. Source: LINDAT handle 11234/1-4692, or the JSON
     version on GitHub (guokan-shang/elitr-minuting-corpus). Use English
     meetings only.
   - A converter for the chosen high-signal corpus.

   Each output must pass `load_utterances`. For each corpus, run the runner's
   `--controls` on the registered design and record the probe count, chance
   level and heuristic baselines.
3. **Add a swap-only option to the runner** for the bigger label-swap arm. It
   runs only the swap-arm jobs, on more probes.
4. **Extend `scripts/runpod/bootstrap.sh`:**
   - add a `DATASET` variable, with a download-and-convert step for each
     corpus;
   - add a `swap` job.

   Check it with `bash -n` and a mistyped job name.
5. **Amend `docs/C4_ANALYSIS_PLAN.md`:** add the new corpora, the summarizer
   run and the swap arm, with the same design, rules and margin. Commit and
   push it **before** renting.

## 5. Rent and set up the A40

1. Install and sign in to the Runpod plugin in Claude Code on the PC:

   ```
   claude plugin marketplace add runpod/runpod-plugins-official
   claude plugin install runpod@runpod
   ```

   Then `/reload-plugins`, then `/mcp` → **runpod** → **Sign in with Runpod**.

2. **The OAuth sign-in is only half the setup.** It authenticates the MCP
   tools, which manage infrastructure and nothing else — they do no SSH, no
   file transfer, no interactive terminals. This campaign needs all three, so
   it also needs `runpodctl` and a real API key:

   ```bash
   curl -sSL https://cli.runpod.net | bash          # runpodctl
   export RUNPOD_API_KEY=…                          # console.runpod.io/user/settings
   runpodctl user                                   # succeeds => key is valid
   ```

   One key authenticates runpodctl, flash and the MCP alike.

3. **Register an SSH key — `startSsh` is a no-op without one.** The account has
   none registered (`get-ssh-keys` returned `{"keys": []}`), and a pod created
   with `startSsh` but no registered key simply has no SSH access.

   ```bash
   ssh-keygen -t ed25519                            # none exists on this PC
   runpodctl ssh add-key                            # or paste into Runpod → Settings
   ```

4. Create the pod — **1× A40**, Secure Cloud, `templateId` `runpod-torch-v280`
   (Runpod PyTorch 2.8.0; it allows CUDA 13.0, which is the only version the
   A40 currently reports available), `mounts.persistent` of **100 GB at
   `/workspace`**, ports `8888/http,22/tcp`, `startSsh: true`, and
   `dataCenterIds: ["CA-MTL-1"]`.

   Claude states the hourly price before creating it. **Stock is `LOW`** in
   both A40 data centers, so creation can fail: retry, then try EU-SE-1. Do not
   silently substitute a different GPU — every alternative changes the budget.

## 6. Run the jobs on the pod

Open the pod's web terminal, or SSH in. Work inside `tmux`, so jobs survive a
disconnect:

```bash
tmux new -s c4
curl -fsSL https://raw.githubusercontent.com/ming3465/c4-speaker-attribution/main/scripts/runpod/bootstrap.sh -o bootstrap.sh

bash bootstrap.sh speedtest                                 # 32B, 20 probes: seconds per call first
bash bootstrap.sh sweep                                     # job 1: 32B on AMI
MODEL=qwen2.5:14b bash bootstrap.sh summary                 # job 2: summarizer on AMI

for m in qwen2.5:14b qwen2.5:32b; do                        # jobs 3, 4, 5
  DATASET=elitr   MODEL=$m bash bootstrap.sh sweep
  DATASET=icsi    MODEL=$m bash bootstrap.sh sweep
  DATASET=supreme MODEL=$m bash bootstrap.sh sweep
done

MODEL=qwen2.5:14b bash bootstrap.sh swap                    # job 6: 1,000 probes, not 278
```

`DATASET` is `ami` | `icsi` | `elitr` | `supreme` and downloads and converts
that corpus on first use. `MODEL` picks the reader, `LIMIT` the probe cap, and
`NUM_CTX` the reader's context window -- which defaults to 16,384 on ELITR and
Supreme Court, whose longest windows run past Ollama's 4,096-token default.
`bash bootstrap.sh ami` still works as an older name for `sweep`.

- **After the speed test,** compare the real seconds per call with the
  estimates in section 2. Re-estimate the total cost before starting the long
  jobs.
- **Resuming.** Everything lives under `/workspace`, so a restarted pod picks
  up where it stopped. Finished rows and cached summaries are skipped.
- **Order.** Run the jobs in the order given in section 2.

## 7. Bring the results back and close the pod

1. Copy the results to the PC. The pod page shows its IP and port:

   ```powershell
   scp -P <port> -r root@<ip>:/workspace/results ./results/runpod
   ```

2. **Stop the pod as soon as the last job finishes,** and terminate it once
   the results are copied. A stopped pod still bills a little for its volume.
3. Render the tables for each run:

   ```powershell
   uv run python scripts/evaluation/analyze_attribution_frozen.py --csv <run>.csv
   ```

   For the lexical attributor, add `--score lexical`.
4. Update these, then commit and push the rendered `*_tables.md` files and the
   docs:
   - `docs/C4_ANALYSIS_PLAN.md`: Results and Deviations;
   - `docs/C4_MAIN_STUDY.md`;
   - the report's to-do list.

## 8. Troubleshooting

| Symptom | Fix |
| --- | --- |
| The A40 is out of stock | Wait and retry. Or use an L40S ($0.79/hr, faster, so the total cost is similar), after re-estimating the budget |
| The pod has no GPU in `nvidia-smi` | Recreate it with the A40 selected. The template alone does not reserve one |
| `ollama pull` is slow or fails | Rerun `bootstrap.sh`; the pull resumes |
| The run exits with code 3 | The headroom gate failed. That is a result, so log it; do not rerun with `--skip-gate` |
| The run exits with code 2 and a schema message | The output folder holds an older CSV; use a new `--out-dir` |
| The credit runs low mid-run | Stop the pod. Finished rows are saved, and the run resumes after a top-up |

## 9. Still open (no GPU needed)

- Figure script for paper-quality charts (PNG/PDF).
- Mentor decisions: the ±5 pt margin, which readers, whether the Sep 7
  framing continues, and AHN scope.
