# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1000 frozen probes from 810 contexts in 189 clusters; 6000 graded rows. Dataset `utterances`, contexts `window`, compressor `salient`, scope `both`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1000 | 59.5 | 49.7% [46.5, 53.3] | 20.7% | 10.0% | 27.9% | 43.7% | +29.0% [+25.9, +32.4] | 100% |
| 0.25 | 1000 | 14.9 | 21.9% [19.4, 24.5] | 20.7% | 10.0% | 27.9% | 38.9% | +1.2% [-1.3, +3.7] | 100% |
| 0.1 | 1000 | 6.0 | 19.9% [17.4, 22.5] | 20.7% | 10.0% | 27.9% | 31.0% | -0.8% [-3.3, +1.9] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.25 | 1000 | 49.7% | 21.9% | -27.8% [-31.4, -24.4] | 334 / 56 | 2.65e-49 |
| 0.1 | 1000 | 49.7% | 19.9% | -29.8% [-33.4, -26.4] | 358 / 60 | 9.27e-53 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 33% | 72% (n=106) | 30% (n=106) | 31% (n=106) |
| 4 | 25% | 57% (n=175) | 27% (n=175) | 30% (n=175) |
| 5+ | 18% | 45% (n=719) | 19% (n=719) | 16% (n=719) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |
| 1.0 | 1000 | 48.8% [45.6, 52.1] | 10.6% [8.7, 12.4] | +38.2% [+34.2, +42.4] | 20.7% | 49.7% |
| 0.25 | 1000 | 21.3% [19.1, 23.7] | 16.5% [14.2, 19.1] | +4.8% [+1.1, +8.5] | 20.7% | 21.9% |
| 0.1 | 1000 | 19.7% [17.4, 22.1] | 17.6% [15.0, 20.4] | +2.1% [-2.0, +6.0] | 20.7% | 19.9% |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1000 (189) | +29.0% [+25.9, +32.4] | [+26.3, +31.7] | 4.6 pts | effect |
| Δ Hit@1, b=0.25 vs 1.0 | 1000 (189) | -27.8% [-31.4, -24.4] | [-30.8, -24.9] | 5.0 pts | effect |
| Δ Hit@1, b=0.1 vs 1.0 | 1000 (189) | -29.8% [-33.4, -26.4] | [-32.8, -26.9] | 5.0 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `complete`, rows 6000, started 2026-10-05T15:44:15+00:00, finished 2026-10-05T17:37:03+00:00
- Git `a558fb04f7b8e40b9fc1199ba3354bd2ebdfadcc`; Python 3.13.12; PYTHONHASHSEED=0
- Reader `qwen2.5:32b` digest `9f13ba1299af`
- Dataset `data/processed/supreme.jsonl` sha256 `2e3d0f5318af`
- Headroom gate **PASS**: lift +29.0 pts [+25.9, +32.4] vs margin +5.0; headroom confirmed
