# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1200 frozen probes from 1126 contexts in 169 clusters; 5634 graded rows. Dataset `utterances`, contexts `window`, compressor `salient`, scope `both`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1200 | 28.4 | 40.4% [37.3, 43.6] | 27.6% | 34.6% | 33.8% | 48.8% | +12.8% [+9.7, +16.0] | 100% |
| 0.5 | 1200 | 14.2 | 35.8% [32.9, 38.6] | 27.6% | 34.6% | 33.8% | 45.6% | +8.2% [+5.4, +11.0] | 100% |
| 0.25 | 1200 | 7.1 | 31.3% [28.7, 33.8] | 27.6% | 34.6% | 33.8% | 39.0% | +3.7% [+1.1, +6.3] | 100% |
| 0.1 | 1200 | 2.9 | 31.2% [28.6, 34.0] | 27.6% | 34.6% | 33.8% | 32.6% | +3.6% [+1.1, +6.3] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.5 | 1200 | 40.4% | 35.8% | -4.6% [-7.3, -1.9] | 177 / 122 | 0.00174 |
| 0.25 | 1200 | 40.4% | 31.3% | -9.1% [-12.2, -6.1] | 239 / 130 | 1.49e-08 |
| 0.1 | 1200 | 40.4% | 31.2% | -9.2% [-12.3, -6.0] | 250 / 140 | 2.77e-08 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.5 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 50% | 56% (n=36) | 53% (n=36) | 47% (n=36) | 53% (n=36) |
| 3 | 33% | 47% (n=275) | 40% (n=275) | 35% (n=275) | 37% (n=275) |
| 4 | 25% | 38% (n=876) | 34% (n=876) | 29% (n=876) | 29% (n=876) |
| 5+ | 20% | 31% (n=13) | 38% (n=13) | 46% (n=13) | 31% (n=13) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |
| 1.0 | 278 | 34.2% [28.7, 39.9] | 28.8% [24.1, 33.5] | +5.4% [-3.2, +14.4] | 26.1% | 31.7% |
| 0.25 | 278 | 25.5% [20.5, 30.9] | 25.2% [20.0, 30.8] | +0.4% [-8.0, +8.3] | 26.1% | 26.3% |
| 0.1 | 278 | 25.2% [20.1, 30.6] | 26.6% [21.1, 32.8] | -1.4% [-10.5, +7.2] | 26.1% | 25.2% |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1200 (169) | +12.8% [+9.7, +16.0] | [+10.2, +15.3] | 4.4 pts | effect |
| Δ Hit@1, b=0.5 vs 1.0 | 1200 (169) | -4.6% [-7.3, -1.9] | [-6.8, -2.3] | 3.8 pts | effect |
| Δ Hit@1, b=0.25 vs 1.0 | 1200 (169) | -9.1% [-12.2, -6.1] | [-11.6, -6.5] | 4.4 pts | effect |
| Δ Hit@1, b=0.1 vs 1.0 | 1200 (169) | -9.2% [-12.3, -6.0] | [-11.8, -6.5] | 4.4 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `complete`, rows 5634, started 2026-09-27T15:33:13+00:00, finished 2026-09-27T21:51:40+00:00
- Git `22e2c88cbde27eeeacfd1b1a0280145bee8ee273` (dirty tree); Python 3.13.5; PYTHONHASHSEED=0
- Reader `qwen2.5:14b` digest `7cdf5a0187d5`
- Dataset `data/processed/ami.jsonl` sha256 `f15cc2fa6db2`
- Headroom gate **PASS**: lift +12.8 pts [+9.7, +16.0] vs margin +5.0; headroom confirmed
