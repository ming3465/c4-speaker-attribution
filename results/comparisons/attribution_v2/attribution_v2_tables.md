# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

542 frozen probes from 161 questions; 3682 graded rows. Reader `qwen2.5:7b`, temperature 0, via the ollama HTTP API. Policy `uniform_compression`, GroupMemBench Finance 10% pilot bundle.
Each probe is fixed from budget-1.0 retrieval; only the text of the same messages is compressed at each budget.
Roster = the speakers visible in the conversation (2–4), so chance = 1/|roster|. Cluster bootstrap by question, 2000 resamples.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| 1.0 | 542 | 65.0 | 41.7% [37.1, 46.1] | 38.3% | 42.6% | +3.4% [-0.8, +7.4] | 100% |
| 0.75 | 542 | 44.2 | 41.7% [37.2, 46.2] | 38.3% | 42.6% | +3.4% [-0.5, +7.4] | 100% |
| 0.5 | 542 | 29.5 | 41.7% [37.0, 46.2] | 38.3% | 42.6% | +3.4% [-0.7, +7.3] | 100% |
| 0.25 | 542 | 14.8 | 41.0% [36.2, 45.4] | 38.3% | 42.6% | +2.6% [-1.6, +6.7] | 100% |
| 0.1 | 542 | 6.0 | 39.7% [35.2, 44.1] | 38.3% | 42.6% | +1.4% [-2.7, +5.5] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.75 | 542 | 41.7% | 41.7% | +0.0% [-3.2, +3.1] | 33 / 33 | 1 |
| 0.5 | 542 | 41.7% | 41.7% | +0.0% [-3.5, +3.4] | 45 / 45 | 1 |
| 0.25 | 542 | 41.7% | 41.0% | -0.7% [-4.8, +3.1] | 60 / 56 | 0.781 |
| 0.1 | 542 | 41.7% | 39.7% | -2.0% [-6.3, +2.0] | 85 / 74 | 0.428 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.75 | b=0.5 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 50% | 56% (n=212) | 59% (n=212) | 59% (n=212) | 54% (n=212) | 52% (n=212) |
| 3 | 33% | 34% (n=230) | 31% (n=230) | 32% (n=230) | 35% (n=230) | 33% (n=230) |
| 4 | 25% | 29% (n=100) | 29% (n=100) | 28% (n=100) | 26% (n=100) | 29% (n=100) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |
| 1.0 | 324 | 31.5% [26.2, 36.6] | 34.3% [29.1, 39.6] | -2.8% [-11.9, +5.9] | 34.5% | 36.7% |
| 0.25 | 324 | 33.6% [28.5, 38.7] | 33.6% [29.0, 38.5] | +0.0% [-8.6, +7.6] | 34.5% | 36.1% |
| 0.1 | 324 | 31.2% [25.8, 36.5] | 40.1% [35.1, 45.2] | -9.0% [-18.1, +0.3] | 34.5% | 34.6% |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 542 (161) | +3.4% [-0.8, +7.4] | [-0.2, +6.8] | 6.1 pts | inconclusive |
| Δ Hit@1, b=0.75 vs 1.0 | 542 (161) | +0.0% [-3.2, +3.1] | [-2.6, +2.6] | 4.6 pts | no effect beyond the margin |
| Δ Hit@1, b=0.5 vs 1.0 | 542 (161) | +0.0% [-3.5, +3.4] | [-2.8, +2.9] | 5.0 pts | no effect beyond the margin |
| Δ Hit@1, b=0.25 vs 1.0 | 542 (161) | -0.7% [-4.8, +3.1] | [-4.0, +2.6] | 5.4 pts | no effect beyond the margin |
| Δ Hit@1, b=0.1 vs 1.0 | 542 (161) | -2.0% [-6.3, +2.0] | [-5.6, +1.4] | 5.9 pts | inconclusive |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- **These rows predate run manifests** (legacy schema). The manifest below records the most recent invocation against this CSV (a resume/verification), not the original generation.
- Status `stopped_at_gate`, rows 3682, started 2026-09-27T14:30:54+00:00, finished 2026-09-27T14:30:55+00:00
- Git `22368ace1a786bbfe5da9e0fdb8eaba75a320988` (dirty tree); Python 3.13.5; PYTHONHASHSEED=0
- Reader `qwen2.5:7b` digest `845dbda0ea48`
- Dataset `data/pilot/c4/corpus_10pct.jsonl` sha256 `919acb1cded1`
- Dataset `data/pilot/c4/questions.jsonl` sha256 `d11b1231c669`
- Headroom gate **FAIL**: lift +3.4 pts [-0.8, +7.4] vs margin +5.0; lift lower bound -0.008 does not exceed margin +0.050; accuracy 0.417 does not clearly beat the frequency heuristic 0.426 (lower bound of the lead -0.078)
