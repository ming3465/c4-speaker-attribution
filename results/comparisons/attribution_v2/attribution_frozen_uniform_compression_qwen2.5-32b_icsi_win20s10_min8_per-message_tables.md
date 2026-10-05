# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1200 frozen probes from 1132 contexts in 75 clusters; 5367 graded rows. Dataset `utterances`, contexts `window`, compressor `salient`, scope `both`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1200 | 15.2 | 61.1% [58.0, 64.2] | 30.8% | 55.2% | 18.7% | 56.7% | +30.3% [+28.0, +32.5] | 100% |
| 0.5 | 1200 | 7.6 | 55.5% [52.0, 59.1] | 30.8% | 55.2% | 18.7% | 52.3% | +24.7% [+22.2, +27.3] | 100% |
| 0.25 | 1200 | 3.8 | 55.6% [52.1, 58.9] | 30.8% | 55.2% | 18.7% | 43.9% | +24.8% [+22.2, +27.2] | 100% |
| 0.1 | 1200 | 1.5 | 54.2% [50.7, 57.8] | 30.8% | 55.2% | 18.7% | 36.8% | +23.4% [+21.0, +25.8] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.5 | 1200 | 61.1% | 55.5% | -5.6% [-7.5, -3.7] | 122 / 55 | 5.19e-07 |
| 0.25 | 1200 | 61.1% | 55.6% | -5.5% [-7.9, -3.3] | 139 / 73 | 6.84e-06 |
| 0.1 | 1200 | 61.1% | 54.2% | -6.9% [-9.4, -4.5] | 174 / 91 | 3.83e-07 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.5 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 50% | 85% (n=221) | 82% (n=221) | 82% (n=221) | 79% (n=221) |
| 3 | 33% | 66% (n=387) | 60% (n=387) | 60% (n=387) | 59% (n=387) |
| 4 | 25% | 57% (n=322) | 51% (n=322) | 49% (n=322) | 47% (n=322) |
| 5+ | 18% | 39% (n=270) | 33% (n=270) | 34% (n=270) | 35% (n=270) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |
| 1.0 | 189 | 38.6% [32.4, 46.5] | 13.8% [9.3, 18.7] | +24.9% [+16.4, +34.6] | 22.8% | 33.9% |
| 0.25 | 189 | 29.6% [23.8, 36.3] | 18.0% [11.7, 25.5] | +11.6% [+0.5, +21.5] | 22.8% | 29.1% |
| 0.1 | 189 | 32.3% [26.6, 39.2] | 16.4% [11.7, 21.6] | +15.9% [+7.3, +24.7] | 22.8% | 32.3% |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1200 (75) | +30.3% [+28.0, +32.5] | [+28.4, +32.2] | 3.2 pts | effect |
| Δ Hit@1, b=0.5 vs 1.0 | 1200 (75) | -5.6% [-7.5, -3.7] | [-7.1, -4.0] | 2.8 pts | effect |
| Δ Hit@1, b=0.25 vs 1.0 | 1200 (75) | -5.5% [-7.9, -3.3] | [-7.5, -3.6] | 3.2 pts | effect |
| Δ Hit@1, b=0.1 vs 1.0 | 1200 (75) | -6.9% [-9.4, -4.5] | [-9.0, -4.9] | 3.5 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `complete`, rows 5367, started 2026-10-05T04:03:56+00:00, finished 2026-10-05T05:15:08+00:00
- Git `21e6f06ed105e905bf818bc54d4a0ec192076eee`; Python 3.13.12; PYTHONHASHSEED=0
- Reader `qwen2.5:32b` digest `9f13ba1299af`
- Dataset `data/processed/icsi.jsonl` sha256 `aadbdafe1fa3`
- Headroom gate **PASS**: lift +30.3 pts [+28.0, +32.5] vs margin +5.0; headroom confirmed
