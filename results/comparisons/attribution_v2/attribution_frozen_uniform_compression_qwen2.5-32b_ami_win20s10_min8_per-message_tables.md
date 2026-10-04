# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1200 frozen probes from 1126 contexts in 169 clusters; 5634 graded rows. Dataset `utterances`, contexts `window`, compressor `salient`, scope `both`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1200 | 28.4 | 42.3% [39.4, 45.3] | 27.6% | 34.6% | 33.8% | 48.8% | +14.7% [+11.9, +17.7] | 100% |
| 0.5 | 1200 | 14.2 | 36.8% [34.0, 39.8] | 27.6% | 34.6% | 33.8% | 45.6% | +9.1% [+6.4, +12.2] | 100% |
| 0.25 | 1200 | 7.1 | 34.2% [31.7, 37.1] | 27.6% | 34.6% | 33.8% | 39.0% | +6.6% [+4.0, +9.5] | 100% |
| 0.1 | 1200 | 2.9 | 33.0% [30.2, 36.1] | 27.6% | 34.6% | 33.8% | 32.6% | +5.4% [+2.7, +8.4] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.5 | 1200 | 42.3% | 36.8% | -5.6% [-7.8, -3.2] | 140 / 73 | 5.17e-06 |
| 0.25 | 1200 | 42.3% | 34.2% | -8.1% [-10.7, -5.5] | 180 / 83 | 2.14e-09 |
| 0.1 | 1200 | 42.3% | 33.0% | -9.3% [-12.1, -6.5] | 204 / 92 | 6.6e-11 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.5 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 50% | 67% (n=36) | 69% (n=36) | 58% (n=36) | 64% (n=36) |
| 3 | 33% | 45% (n=275) | 39% (n=275) | 34% (n=275) | 35% (n=275) |
| 4 | 25% | 40% (n=876) | 35% (n=876) | 33% (n=876) | 31% (n=876) |
| 5+ | 20% | 46% (n=13) | 23% (n=13) | 31% (n=13) | 38% (n=13) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |
| 1.0 | 278 | 30.6% [25.4, 36.0] | 25.5% [20.7, 30.5] | +5.0% [-3.0, +13.2] | 26.1% | 33.1% |
| 0.25 | 278 | 28.1% [23.2, 33.3] | 26.6% [21.8, 31.5] | +1.4% [-6.9, +9.6] | 26.1% | 30.9% |
| 0.1 | 278 | 22.7% [17.8, 27.4] | 26.3% [21.2, 31.9] | -3.6% [-11.8, +4.2] | 26.1% | 25.5% |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1200 (169) | +14.7% [+11.9, +17.7] | [+12.4, +17.2] | 4.2 pts | effect |
| Δ Hit@1, b=0.5 vs 1.0 | 1200 (169) | -5.6% [-7.8, -3.2] | [-7.4, -3.6] | 3.2 pts | effect |
| Δ Hit@1, b=0.25 vs 1.0 | 1200 (169) | -8.1% [-10.7, -5.5] | [-10.3, -5.9] | 3.7 pts | effect |
| Δ Hit@1, b=0.1 vs 1.0 | 1200 (169) | -9.3% [-12.1, -6.5] | [-11.7, -7.0] | 4.0 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `complete`, rows 5634, started 2026-10-04T17:42:36+00:00, finished 2026-10-04T19:01:31+00:00
- Git `dc8da1d3edd69ae2eb6acfdecdb63c171973504f`; Python 3.13.12; PYTHONHASHSEED=0
- Reader `qwen2.5:32b` digest `9f13ba1299af`
- Dataset `data/processed/ami.jsonl` sha256 `f15cc2fa6db2`
- Headroom gate **PASS**: lift +14.7 pts [+11.9, +17.7] vs margin +5.0; headroom confirmed
