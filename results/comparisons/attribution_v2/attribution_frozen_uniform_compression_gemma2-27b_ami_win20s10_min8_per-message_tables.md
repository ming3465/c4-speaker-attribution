# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1200 frozen probes from 1126 contexts in 169 clusters; 5634 graded rows. Dataset `utterances`, contexts `window`, compressor `salient`, scope `both`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1200 | 28.4 | 45.8% [42.9, 48.7] | 27.6% | 34.6% | 33.8% | 48.8% | +18.1% [+15.3, +21.0] | 100% |
| 0.5 | 1200 | 14.2 | 39.5% [36.7, 42.6] | 27.6% | 34.6% | 33.8% | 45.6% | +11.9% [+9.1, +15.0] | 100% |
| 0.25 | 1200 | 7.1 | 33.8% [31.0, 37.0] | 27.6% | 34.6% | 33.8% | 39.0% | +6.2% [+3.4, +9.3] | 100% |
| 0.1 | 1200 | 2.9 | 31.9% [29.1, 34.8] | 27.6% | 34.6% | 33.8% | 32.6% | +4.3% [+1.5, +7.3] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.5 | 1200 | 45.8% | 39.5% | -6.2% [-8.6, -3.8] | 174 / 99 | 6.62e-06 |
| 0.25 | 1200 | 45.8% | 33.8% | -11.9% [-14.8, -9.1] | 254 / 111 | 5.07e-14 |
| 0.1 | 1200 | 45.8% | 31.9% | -13.8% [-16.7, -11.1] | 278 / 112 | 2.13e-17 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.5 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 50% | 67% (n=36) | 64% (n=36) | 56% (n=36) | 53% (n=36) |
| 3 | 33% | 51% (n=275) | 43% (n=275) | 35% (n=275) | 33% (n=275) |
| 4 | 25% | 43% (n=876) | 37% (n=876) | 32% (n=876) | 31% (n=876) |
| 5+ | 20% | 38% (n=13) | 46% (n=13) | 46% (n=13) | 46% (n=13) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |
| 1.0 | 278 | 38.8% [32.6, 45.3] | 22.7% [18.3, 27.2] | +16.2% [+7.4, +25.5] | 26.1% | 42.4% |
| 0.25 | 278 | 30.6% [25.0, 36.2] | 25.2% [20.3, 30.6] | +5.4% [-4.0, +14.5] | 26.1% | 29.1% |
| 0.1 | 278 | 24.5% [19.4, 29.7] | 29.9% [24.4, 35.9] | -5.4% [-14.4, +3.3] | 26.1% | 26.3% |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1200 (169) | +18.1% [+15.3, +21.0] | [+15.7, +20.6] | 4.1 pts | effect |
| Δ Hit@1, b=0.5 vs 1.0 | 1200 (169) | -6.2% [-8.6, -3.8] | [-8.3, -4.2] | 3.4 pts | effect |
| Δ Hit@1, b=0.25 vs 1.0 | 1200 (169) | -11.9% [-14.8, -9.1] | [-14.3, -9.5] | 4.0 pts | effect |
| Δ Hit@1, b=0.1 vs 1.0 | 1200 (169) | -13.8% [-16.7, -11.1] | [-16.3, -11.5] | 4.1 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `complete`, rows 5634, started 2026-10-05T19:55:31+00:00, finished 2026-10-05T21:45:23+00:00
- Git `400197815779eb9041ab20dc581fed49a7f1a2d0`; Python 3.13.12; PYTHONHASHSEED=0
- Reader `gemma2:27b` digest `53261bc9c192`
- Dataset `data/processed/ami.jsonl` sha256 `f15cc2fa6db2`
- Headroom gate **PASS**: lift +18.1 pts [+15.3, +21.0] vs margin +5.0; headroom confirmed
