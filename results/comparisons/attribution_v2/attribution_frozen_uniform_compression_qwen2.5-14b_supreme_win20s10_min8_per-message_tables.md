# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1200 frozen probes from 1055 contexts in 192 clusters; 5562 graded rows. Dataset `utterances`, contexts `window`, compressor `salient`, scope `both`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1200 | 62.7 | 58.4% [55.7, 61.2] | 23.7% | 42.6% | 35.3% | 51.7% | +34.7% [+31.9, +37.5] | 100% |
| 0.5 | 1200 | 31.3 | 41.8% [39.0, 44.7] | 23.7% | 42.6% | 35.3% | 50.0% | +18.1% [+15.2, +20.8] | 100% |
| 0.25 | 1200 | 15.7 | 33.4% [30.9, 36.1] | 23.7% | 42.6% | 35.3% | 44.5% | +9.7% [+7.2, +12.2] | 100% |
| 0.1 | 1200 | 6.3 | 30.2% [27.6, 32.9] | 23.7% | 42.6% | 35.3% | 38.8% | +6.4% [+3.9, +9.2] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.5 | 1200 | 58.4% | 41.8% | -16.6% [-19.7, -13.6] | 281 / 82 | 1.26e-26 |
| 0.25 | 1200 | 58.4% | 33.4% | -25.0% [-28.2, -21.8] | 379 / 79 | 4.81e-48 |
| 0.1 | 1200 | 58.4% | 30.2% | -28.2% [-31.5, -25.1] | 430 / 91 | 1.09e-53 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.5 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 50% | 58% (n=43) | 56% (n=43) | 51% (n=43) | 47% (n=43) |
| 3 | 33% | 61% (n=192) | 48% (n=192) | 40% (n=192) | 38% (n=192) |
| 4 | 25% | 57% (n=338) | 41% (n=338) | 31% (n=338) | 25% (n=338) |
| 5+ | 18% | 59% (n=627) | 39% (n=627) | 32% (n=627) | 30% (n=627) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |
| 1.0 | 254 | 46.9% [40.9, 53.1] | 9.4% [6.0, 13.2] | +37.4% [+29.8, +44.9] | 20.7% | 47.6% |
| 0.25 | 254 | 24.4% [19.2, 30.2] | 21.7% [16.9, 26.6] | +2.8% [-5.1, +10.8] | 20.7% | 28.0% |
| 0.1 | 254 | 24.0% [19.3, 29.3] | 15.7% [11.0, 20.7] | +8.3% [+0.4, +16.4] | 20.7% | 24.8% |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1200 (192) | +34.7% [+31.9, +37.5] | [+32.4, +37.0] | 4.0 pts | effect |
| Δ Hit@1, b=0.5 vs 1.0 | 1200 (192) | -16.6% [-19.7, -13.6] | [-19.2, -14.1] | 4.4 pts | effect |
| Δ Hit@1, b=0.25 vs 1.0 | 1200 (192) | -25.0% [-28.2, -21.8] | [-27.7, -22.3] | 4.6 pts | effect |
| Δ Hit@1, b=0.1 vs 1.0 | 1200 (192) | -28.2% [-31.5, -25.1] | [-31.0, -25.6] | 4.5 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `complete`, rows 5562, started 2026-10-05T10:41:57+00:00, finished 2026-10-05T10:43:26+00:00
- Git `f82a05cf9d35cd8161b7da81e43acfb3aaed8d54`; Python 3.13.12; PYTHONHASHSEED=0
- Reader `qwen2.5:14b` digest `7cdf5a0187d5`
- Dataset `data/processed/supreme.jsonl` sha256 `2e3d0f5318af`
- Headroom gate **PASS**: lift +34.7 pts [+31.9, +37.5] vs margin +5.0; headroom confirmed
