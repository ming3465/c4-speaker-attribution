# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1200 frozen probes from 1126 contexts in 169 clusters; 4800 graded rows. Dataset `utterances`, contexts `window`, compressor `salient`, scope `target`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1200 | 28.4 | 42.2% [39.2, 45.3] | 27.6% | 34.6% | 33.8% | 48.8% | +14.6% [+11.6, +17.7] | 100% |
| 0.5 | 1200 | 14.2 | 37.2% [34.5, 40.1] | 27.6% | 34.6% | 33.8% | 46.2% | +9.6% [+7.0, +12.5] | 100% |
| 0.25 | 1200 | 7.1 | 35.2% [32.5, 37.9] | 27.6% | 34.6% | 33.8% | 40.9% | +7.6% [+4.8, +10.4] | 100% |
| 0.1 | 1200 | 2.9 | 33.1% [30.3, 36.2] | 27.6% | 34.6% | 33.8% | 34.4% | +5.5% [+2.7, +8.5] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.5 | 1200 | 42.2% | 37.2% | -4.9% [-7.1, -2.8] | 123 / 64 | 1.91e-05 |
| 0.25 | 1200 | 42.2% | 35.2% | -7.0% [-9.6, -4.5] | 164 / 80 | 8.09e-08 |
| 0.1 | 1200 | 42.2% | 33.1% | -9.1% [-11.4, -6.9] | 172 / 63 | 7.12e-13 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.5 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 50% | 67% (n=36) | 72% (n=36) | 58% (n=36) | 64% (n=36) |
| 3 | 33% | 44% (n=275) | 40% (n=275) | 35% (n=275) | 35% (n=275) |
| 4 | 25% | 40% (n=876) | 35% (n=876) | 34% (n=876) | 31% (n=876) |
| 5+ | 20% | 46% (n=13) | 23% (n=13) | 38% (n=13) | 31% (n=13) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1200 (169) | +14.6% [+11.6, +17.7] | [+12.1, +17.2] | 4.4 pts | effect |
| Δ Hit@1, b=0.5 vs 1.0 | 1200 (169) | -4.9% [-7.1, -2.8] | [-6.8, -3.1] | 3.1 pts | effect |
| Δ Hit@1, b=0.25 vs 1.0 | 1200 (169) | -7.0% [-9.6, -4.5] | [-9.1, -4.9] | 3.6 pts | effect |
| Δ Hit@1, b=0.1 vs 1.0 | 1200 (169) | -9.1% [-11.4, -6.9] | [-11.0, -7.3] | 3.1 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `complete`, rows 4800, started 2026-10-05T19:00:19+00:00, finished 2026-10-05T19:54:34+00:00
- Git `400197815779eb9041ab20dc581fed49a7f1a2d0`; Python 3.13.12; PYTHONHASHSEED=0
- Reader `qwen2.5:32b` digest `9f13ba1299af`
- Dataset `data/processed/ami.jsonl` sha256 `f15cc2fa6db2`
- Headroom gate **PASS**: lift +14.6 pts [+11.6, +17.7] vs margin +5.0; headroom confirmed
