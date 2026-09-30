# C4 Handoff

Written 2026-09-07. Supersedes the earlier "C4 Handoff Prompt" on the point of
what C4 should be. Read the Corrections section before trusting anything from
the previous handoff.

## Project

Repo `summer-algoverse`, branch `ming/c4-failure-decomposition`, commit
`57092c5`, pushed to `ming3465/summer-algoverse` (private fork of
`rjustyn1/summer-algoverse`). Research project: predicted-consumer-aware memory
compression for multi-party LLM agents (Algoverse).

Two working copies exist and they have diverged:

| | This machine | Other machine |
| --- | --- | --- |
| Path | `/mnt/f/project/summer-algoverse` | `~/Project/Algoverse/summer-algoverse` |
| Python | 3.12.3, stdlib only, no pip | 3.14 |
| Has failure-decomposition code | yes (committed, pushed) | via the branch |
| Has attribution-probe code | **no** | yes, **unpushed** |
| Reader | ollama, 3 models, GPU | ollama |

`attribution_probe.py`, `run_attribution_probe.py` and `reader_pass.py` are on
the other machine only. They are not on the remote branch. Push them.

## Environment on this machine

- ollama v0.33.3, user-local at `~/.local/ollama/bin/ollama` (no sudo). Needed a
  zstd binary too, at `~/.local/bin/zstd`. In a fresh shell:
  `export PATH="$HOME/.local/ollama/bin:$HOME/.local/bin:$PATH"`
- Models: `qwen2.5:7b` (4.7 GB), `llama3.1:8b` (4.9 GB), `gemma2:9b` (5.4 GB).
- GPU: RTX 2070 SUPER, 8 GB, CUDA detected.
- **A 490-probe sweep takes ~2 minutes here, not 60-90.** That estimate in the
  previous handoff was from a CPU-only box. Multi-reader robustness is cheap.

## What we are trying to achieve

The proposal's core claim is that memory compression should be driven by
*predicted future consumers* — who will need this later — rather than by
recency or global importance. Four contributions:

1. Does keeping residual detail matter, and how much (fidelity allocation).
2. (a) Does predicting the future consumer matter? (b) Does provenance help
   that prediction?
3. Provenance-conditioned interpretation at read time.
4. **C4** — originally the failure decomposition; see below.

2a and 2b have results: 99.38% Hit@1 vs 16.67% random on future-consumer
prediction (480 examples), and 17.92% -> 51.46% with provenance on 240 matched
counterfactuals. Both still need the audit described at the end of this file.

## What happened to C4

**Originally** a failure-mode decomposition: attribute every wrong answer to
`lost_at_write` / `not_retrieved` / `answer_visible`. Built, run, committed at
`57092c5`, with a matched-budget harness, an eligibility gate, and per-category
tables.

**Then scooped.** WhenLoss (arXiv 2605.24579) publishes the same protocol.

**Reframed** to compression-induced attribution failure: after compression, can
the reader still tell who said what, and does it worsen with more speakers.

**That reframe is dead on our data.** Two independent tests, below.

**Recommendation: revert to memory failure, but on the axis WhenLoss cannot
reach** — not *when* memory fails (they own that) but *whose* memory fails.

## What WhenLoss actually contains

Read from the PDF, not the abstract. They own:

- The four-condition protocol: TFC (truncated full context), OE (oracle
  evidence), CSM (complete stored memory), RM (retrieved memory), with
  `Δ_write = φ(OE) − φ(CSM)` and `Δ_retr = φ(CSM) − φ(RM)`.
- The write-dominant finding: 4 of 6 baselines, on LongMemEval *and* LoCoMo,
  three readers (GPT-5.2, Claude Sonnet 4, Gemini 2.5 Pro).
- **A budget sweep.** They report the advantage is largest under tight budgets.
  Do not claim the write/retrieval crossover as novel.
- EPC (Expected Predictive Compression): write budget B = 5,000 tokens, LLM
  self-generates k=5 probe questions, keeps minimal supporting evidence.

Their stated limitations: diagnosis is conditioned on reader and metric; both
benchmarks need gold evidence annotations for OE (they name LLM-generated
*silver* evidence as future work — our recovered GroupMemBench evidence is
exactly that); future work includes adaptive compression from per-session
diagnostic signals, longer conversations, more domains.

### The opening

Full-text keyword counts in the paper:

```
speaker 0 · multi-party 0 · multi-user 0 · participant 0 · group 0
```

"provenance" appears twice, both meaning *where the baseline code came from*.
The paper has no concept of who said anything, because LongMemEval is one user
plus an assistant and LoCoMo is two friends. This is structural, not an
oversight — their benchmarks cannot express the question.

### EPC does not scoop 2a

EPC's objective is an expectation over a future-**question** distribution:

```
m* = argmin_{|m| <= B}  Σ_{q ∈ Q(x)}  w(q) · L( A(x,q), A(m,q) )
```

In a two-party conversation *who will ask* is degenerate — there is one asker —
so consumer prediction was never available to them. In a group, Q(x) factorises
over participants and the right weight is P(this participant needs this), not
just P(this question is asked). **2a is the multi-party generalisation of their
own formalism.** Frame it that way, and use EPC as the headline baseline for
C1/C2: question-anticipating vs consumer-anticipating allocation, same write
budget.

## Experiments run this session

### 1. Attribution ceiling test — is the task solvable at all?

Before compression can degrade attribution, attribution must work uncompressed.
Identical probe on four corpora: 5 consecutive turns, one speaker blinded,
6-name roster (4 for AMI, which has only 4 speakers), name-leak probes
discarded, reader `qwen2.5:7b`.

| Corpus | Probes | Cands | Random | **Majority** | Hit@1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| SocialMemBench | 35 | 6 | 16.7% | 17.1% | **40.0%** |
| QMSum / AMI | 70 | 4 | 25.0% | 35.7% | 28.6% |
| GroupMemBench | 70 | 6 | 16.7% | 25.7% | 24.3% |
| DialSim / Friends | 70 | 6 | 16.7% | 27.1% | 15.7% |

Re-running gives 22.9-24.3% for GroupMemBench and 15.7-17.1% for DialSim:
ollama is not fully deterministic at temperature 0, so treat +/-2 points as
run-to-run noise. No conclusion below turns on that margin.

**Only SocialMemBench beats both floors.** GroupMemBench clears random by 7.6
points but loses to its own majority baseline, so it cannot support a speaker-
attribution claim. SocialMemBench works because its personas ship explicit
`speaking_quirks_json` and `communication_profile_json` — the distinctiveness
was engineered in. It has no named asker, so it cannot support 2a.

### 2. Read-time provenance — three arms, three readers

Hold question, gold evidence and reader fixed; vary only the speaker label:
correct / stripped / deliberately wrong. 98 questions, GroupMemBench Finance.

| Reader | Labelled | Stripped | Shuffled | Δ | McNemar p |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen2.5:7b | 55.1% | 58.2% | 56.1% | −3.1% | 0.375 |
| llama3.1:8b | 46.9% | 50.0% | 45.9% | −3.1% | 0.453 |
| gemma2:9b | 56.1% | 56.1% | 56.1% | +0.0% | 1.000 |

Per category (qwen2.5:7b), the effect is absent exactly where theory says it
should be strongest: `term_ambiguity` −4.8%, `user_implicit` −7.7%. In three of
five categories labelled and shuffled are *identical to the question*, so the
readers are not weighing provenance and finding it unhelpful — they never read
the field.

**Caveat that matters:** this design supplied all-correct, non-conflicting
evidence, so provenance had no job to do. The proposal's real claim is about
*contested* evidence — an old and a new statement disagree and role/recency is
the tiebreaker. That version is untested and is the best remaining shot.

### 3. Failure decomposition stratified by speaker

Uniform compression at 25% budget, n=98, from the committed harness.

| Stratum | n | Lost at write |
| --- | ---: | ---: |
| Asker ≠ evidence author | 83 | 53% |
| Asker == evidence author | 15 | 100% |

| Evidence author's role | n | Lost at write |
| --- | ---: | ---: |
| IT Systems Lead | 10 | 40% |
| Compliance Officer | 62 | 53% |
| Product Owner/Manager | 19 | 58% |
| Business Analyst | 17 | 59% |
| Data Analyst | 6 | 67% |
| Risk Analyst | 11 | 73% |
| Client Services Lead | 9 | 78% |

A 40-to-78 point spread by role is the kind of thing WhenLoss structurally
cannot report. But it is underpowered (six of seven roles have n ≤ 19), the
self/cross split is confounded with the `user_implicit` category, and the
"number of evidence authors" cut is mechanical (the formation check passes if
*any* unit survives) and must not be reported as a finding.

## Corrections — do not inherit these mistakes

1. **The lexical grader is broken.** `answer_support >= 0.65` token overlap
   fails correct answers. Inspected outputs:
   - gold *"Expand owner and expiry tracking to all items currently in the
     register, with low-risk entries tagged as provisional…"*, model *"Owner and
     expiry tracking now applies to all register items; low-risk entries stay
     provisional but are reviewed in the same cutoff cycle"* — support 0.60,
     graded FAIL. It is correct.
   - Another correct answer scored 0.64 against the 0.65 threshold.
   At least 3-4 of 6 inspected were substantively right and graded wrong.
   GroupMemBench's own baselines use a GPT-5 judge. Use a judge.
2. **`knowledge_update` at 0-14% is a grading artifact, not a broken category.**
   An earlier note said that category needed debugging. Wrong diagnosis.
3. **The eligibility gate is lexical too**, so "98 gradeable questions" is
   optimistic. Real usable n is lower.
4. **We do not contradict WhenLoss.** An earlier note said retrieval dominates
   on our data. That was at budget 1.0, where write-loss is zero by
   construction. At a tight budget our numbers are write-dominant (60.2% vs
   33.7% at 25%), replicating them.
5. **Majority, not random, is the baseline to beat** — GroupMemBench attribution
   at 24.3% looks above the 16.7% random floor and is still below its 25.7%
   majority. This was trap #2 in the previous handoff and it decided the result.
6. **WhenLoss sweeps budgets.** Do not claim the tight-budget finding.

## What to do next

1. **Push the attribution-probe code** from the other machine, or delete it —
   the ceiling test says the framing it serves is not viable on GroupMemBench.
2. **Re-run the provenance arms with an LLM judge** instead of token overlap.
   One local model answers, another judges. ~15 minutes. This is the only way
   to know whether the null survives; every absolute accuracy above is a floor,
   not an accuracy.
3. **Build the contested-evidence test.** Retrieved set contains a
   contradiction; provenance (role, seniority, timestamp) is the only
   tiebreaker. This is the proposal's actual claim and the best chance of
   rescuing the GroupMemBench framing. Depends on (2), since it leans on
   `knowledge_update`.
4. **Recover evidence for the other three domains** (531 questions). n=98 caps
   every multi-party claim and leaves per-role cells at 6-19.
5. **Adopt the WhenLoss instrument** (TFC/OE/CSM/RM with a reader and judge) in
   place of the ad-hoc lexical decomposition, then stratify Δ_write and Δ_retr
   by speaker and role. Claim: the diagnosis is not uniform across
   participants; uniform-budget compression systematically disadvantages some
   roles.
6. **Audit 2a before presenting.** 99.38% Hit@1 is implausibly high for a
   future-prediction task. Run: channel-only baseline, group-wise (not random)
   train/test split, label-in-text scan, shuffled-label control, majority-class
   baseline. The same audit protects C4.

## Files

Committed at `57092c5`:

| Path | Contents |
| --- | --- |
| `src/evaluation/failure_decomposition.py` | `build_store`, `BM25Index`, `POLICIES`, compression, attribution. Shared instrument. |
| `src/datasets/memory_tasks.py` | GroupMemBench / LoCoMo / pilot-bundle adapters onto one schema. |
| `scripts/evaluation/run_failure_decomposition.py` | Runner: budget sweep, policies, `--dataset pilot`. |
| `scripts/evaluation/render_failure_tables.py` | Table 3 per question category. |
| `scripts/data/evidence_statistics.py` | Evidence density, sharing, cross-consumer rate. |
| `scripts/data/export_pilot_bundle.py` | Rebuilds the pilot bundle from raw sources. |
| `data/pilot/c4/` | Self-contained 2.8 MB bundle: 185 questions, 288 evidence messages, 10% corpus, results. |
| `docs/DATASET_AUDIT.md` | What every candidate dataset actually contains, verified by download. |
| `docs/FAILURE_DECOMPOSITION.md` | Bucket definitions, eligibility gate, budget matching, limits. |

Added by this session:

| Path | Contents |
| --- | --- |
| `docs/C4_HANDOFF.md` | This file. |
| `scripts/evaluation/run_attribution_ceiling.py` | Corpus screen: is speaker attribution solvable uncompressed? Run before investing in any attribution study. |
| `scripts/evaluation/run_provenance_arms.py` | Three-arm read-time provenance test (labelled / stripped / shuffled) with McNemar and per-category breakdown. |
| `data/processed/attribution_ceiling/candidate_turns.json` | Turn data for the four screened corpora (GroupMemBench, SocialMemBench, DialSim/Friends, QMSum/AMI). |

Both scripts need a local ollama on `127.0.0.1:11434`; pass the model as the
first argument. Still scratch-only: `inspect_outputs.py`, `bench_readers.py`,
`pdftext.py` (a minimal pure-Python PDF text extractor, useful since this box
has no poppler).

## Structural facts about the data

- GroupMemBench Finance: 30,000 messages, 6 channels, 12 users, 7 roles.
- 745 typed questions exist across 4 domains x 6 types, in the code repo
  `UCSB-NLP-Chang/GroupMemBench` — **not** the HF data repo, and they carry no
  evidence pointers.
- Gold evidence for the 214 Finance questions was recovered by HF
  `toddzheng024/groupmembench-agent-sessions`; 185 have evidence, all ids
  resolve, 98 pass the (lexical, see correction 3) eligibility gate.
- Evidence density: only **0.96%** of the corpus is ever asked about, and only
  **5.6%** of evidence units are wanted by more than one question — so an oracle
  future-consumer policy is nearly free and ~94% of its advantage is
  per-question memorisation. A leave-one-out oracle is required before any
  Phase-0 gate is read as support for 2a.
- Cross-consumer rate: **87.6%** of (question, evidence) pairs have asker ≠
  author. This is the one structural assumption of the proposal that the data
  confirms.
