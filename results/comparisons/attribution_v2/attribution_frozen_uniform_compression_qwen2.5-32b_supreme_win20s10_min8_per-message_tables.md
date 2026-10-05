# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1200 frozen probes from 1055 contexts in 192 clusters; 5198 graded rows. Dataset `utterances`, contexts `window`, compressor `salient`, scope `both`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1198 | 62.7 | 62.5% [59.9, 65.1] | 23.8% | 42.6% | 35.4% | 51.6% | +38.8% [+36.2, +41.5] | 100% |
| 0.5 | 1098 | 31.0 | 42.3% [39.4, 45.2] | 23.7% | 42.1% | 35.2% | 50.5% | +18.5% [+15.7, +21.4] | 100% |
| 0.25 | 1097 | 15.5 | 26.9% [24.3, 29.5] | 23.7% | 42.1% | 35.2% | 44.8% | +3.2% [+0.6, +5.8] | 100% |
| 0.1 | 1097 | 6.2 | 25.1% [22.5, 27.8] | 23.7% | 42.1% | 35.2% | 38.8% | +1.4% [-1.3, +4.1] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.5 | 1096 | 62.0% | 42.3% | -19.6% [-22.5, -16.7] | 268 / 53 | 1.01e-35 |
| 0.25 | 1095 | 61.9% | 26.8% | -35.1% [-38.5, -31.7] | 430 / 46 | 3.26e-79 |
| 0.1 | 1095 | 61.9% | 25.0% | -36.9% [-40.4, -33.3] | 465 / 61 | 5.27e-78 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.5 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 50% | 77% (n=43) | 55% (n=38) | 50% (n=38) | 34% (n=38) |
| 3 | 33% | 64% (n=192) | 49% (n=171) | 23% (n=171) | 26% (n=171) |
| 4 | 25% | 63% (n=338) | 39% (n=316) | 28% (n=315) | 26% (n=315) |
| 5+ | 18% | 61% (n=625) | 41% (n=573) | 26% (n=573) | 24% (n=573) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |
| 1.0 | 236 | 54.2% [48.3, 60.4] | 9.3% [5.7, 13.4] | +44.9% [+36.5, +53.3] | 20.8% | 54.2% |
| 0.25 | 236 | 23.3% [17.4, 29.4] | 16.1% [11.4, 21.1] | +7.2% [-1.9, +16.1] | 20.8% | 22.9% |
| 0.1 | 236 | 19.9% [15.3, 24.9] | 18.2% [13.2, 23.5] | +1.7% [-5.5, +9.3] | 20.8% | 20.3% |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1198 (192) | +38.8% [+36.2, +41.5] | [+36.5, +41.0] | 3.7 pts | effect |
| Δ Hit@1, b=0.5 vs 1.0 | 1096 (192) | -19.6% [-22.5, -16.7] | [-22.0, -17.2] | 4.0 pts | effect |
| Δ Hit@1, b=0.25 vs 1.0 | 1095 (192) | -35.1% [-38.5, -31.7] | [-38.0, -32.2] | 4.9 pts | effect |
| Δ Hit@1, b=0.1 vs 1.0 | 1095 (192) | -36.9% [-40.4, -33.3] | [-39.8, -34.0] | 5.0 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `running`, rows None, started 2026-10-05T10:48:55+00:00, finished None
- Git `f82a05cf9d35cd8161b7da81e43acfb3aaed8d54`; Python 3.13.12; PYTHONHASHSEED=0
- Reader `qwen2.5:32b` digest `9f13ba1299af`
- Dataset `data/processed/supreme.jsonl` sha256 `2e3d0f5318af`
- Headroom gate **PASS**: lift +38.7 pts [+36.0, +41.3] vs margin +5.0; headroom confirmed
