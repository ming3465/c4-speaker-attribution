# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1200 frozen probes from 1126 contexts in 169 clusters; 5634 graded rows. Dataset `utterances`, contexts `window`, compressor `salient`, scope `both`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

**Scored: the lexical TF-IDF attributor recorded on each row, not the LLM reader.** It needs no model, so this is its own dose-response over the same frozen probes.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1200 | 28.4 | 48.8% [45.3, 52.1] | 27.6% | 34.6% | 33.8% | 48.8% | +21.1% [+17.9, +24.5] | 100% |
| 0.5 | 1200 | 14.2 | 45.6% [42.5, 48.9] | 27.6% | 34.6% | 33.8% | 45.6% | +18.0% [+14.9, +21.2] | 100% |
| 0.25 | 1200 | 7.1 | 39.0% [36.2, 41.8] | 27.6% | 34.6% | 33.8% | 39.0% | +11.4% [+8.7, +14.2] | 100% |
| 0.1 | 1200 | 2.9 | 32.6% [30.1, 35.2] | 27.6% | 34.6% | 33.8% | 32.6% | +5.0% [+2.7, +7.5] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.5 | 1200 | 48.8% | 45.6% | -3.2% [-5.3, -0.9] | 108 / 70 | 0.0054 |
| 0.25 | 1200 | 48.8% | 39.0% | -9.8% [-13.2, -6.7] | 229 / 112 | 2.25e-10 |
| 0.1 | 1200 | 48.8% | 32.6% | -16.2% [-20.0, -12.0] | 345 / 151 | 1.63e-18 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.5 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 50% | 81% (n=36) | 75% (n=36) | 67% (n=36) | 61% (n=36) |
| 3 | 33% | 56% (n=275) | 55% (n=275) | 47% (n=275) | 39% (n=275) |
| 4 | 25% | 45% (n=876) | 42% (n=876) | 35% (n=876) | 30% (n=876) |
| 5+ | 20% | 62% (n=13) | 46% (n=13) | 38% (n=13) | 23% (n=13) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |
| 1.0 | 278 | 39.6% [33.7, 45.9] | 19.8% [15.0, 24.7] | +19.8% [+10.3, +29.2] | 26.1% | 39.6% |
| 0.25 | 278 | 30.9% [25.5, 36.9] | 21.9% [17.4, 26.5] | +9.0% [+1.0, +17.5] | 26.1% | 30.2% |
| 0.1 | 278 | 28.8% [23.6, 34.1] | 23.4% [18.5, 28.8] | +5.4% [-3.0, +13.5] | 26.1% | 27.3% |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1200 (169) | +21.1% [+17.9, +24.5] | [+18.3, +24.1] | 4.7 pts | effect |
| Δ Hit@1, b=0.5 vs 1.0 | 1200 (169) | -3.2% [-5.3, -0.9] | [-5.0, -1.3] | 3.2 pts | effect |
| Δ Hit@1, b=0.25 vs 1.0 | 1200 (169) | -9.8% [-13.2, -6.7] | [-12.5, -7.1] | 4.7 pts | effect |
| Δ Hit@1, b=0.1 vs 1.0 | 1200 (169) | -16.2% [-20.0, -12.0] | [-19.4, -13.0] | 5.5 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `complete`, rows 5634, started 2026-09-27T15:34:30+00:00, finished 2026-09-27T15:34:34+00:00
- Git `22e2c88cbde27eeeacfd1b1a0280145bee8ee273` (dirty tree); Python 3.13.5; PYTHONHASHSEED=0
- Reader `stub` digest ``
- Dataset `data/processed/ami.jsonl` sha256 `f15cc2fa6db2`
- Headroom gate **FAIL**: lift +0.7 pts [-1.6, +3.2] vs margin +5.0; lift lower bound -0.016 does not exceed margin +0.050; accuracy 0.283 does not clearly beat the frequency heuristic 0.346 (lower bound of the lead -0.098)
