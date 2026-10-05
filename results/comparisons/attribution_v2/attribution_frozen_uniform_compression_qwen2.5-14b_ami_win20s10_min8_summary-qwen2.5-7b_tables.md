# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1200 frozen probes from 1126 contexts in 169 clusters; 5634 graded rows. Dataset `utterances`, contexts `window`, compressor `summary`, scope `both`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1200 | 28.4 | 40.5% [37.2, 43.8] | 27.6% | 34.6% | 33.8% | 48.8% | +12.9% [+9.7, +16.2] | 100% |
| 0.5 | 1200 | 9.0 | 35.2% [32.4, 38.1] | 27.6% | 34.6% | 33.8% | 37.3% | +7.6% [+4.8, +10.6] | 100% |
| 0.25 | 1200 | 5.8 | 32.0% [29.3, 34.7] | 27.6% | 34.6% | 33.8% | 35.1% | +4.4% [+1.7, +7.1] | 100% |
| 0.1 | 1200 | 2.7 | 32.6% [29.8, 35.5] | 27.6% | 34.6% | 33.8% | 32.6% | +5.0% [+2.3, +7.7] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0.5 | 1200 | 40.5% | 35.2% | -5.2% [-8.3, -2.2] | 207 / 144 | 0.000909 |
| 0.25 | 1200 | 40.5% | 32.0% | -8.5% [-11.5, -5.4] | 244 / 142 | 2.34e-07 |
| 0.1 | 1200 | 40.5% | 32.6% | -7.9% [-11.3, -4.5] | 245 / 150 | 2.02e-06 |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 | b=0.5 | b=0.25 | b=0.1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 50% | 56% (n=36) | 47% (n=36) | 42% (n=36) | 58% (n=36) |
| 3 | 33% | 44% (n=275) | 39% (n=275) | 34% (n=275) | 43% (n=275) |
| 4 | 25% | 39% (n=876) | 33% (n=876) | 31% (n=876) | 28% (n=876) |
| 5+ | 20% | 46% (n=13) | 46% (n=13) | 54% (n=13) | 31% (n=13) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |
| 1.0 | 278 | 33.8% [28.3, 39.7] | 27.3% [22.7, 32.5] | +6.5% [-2.6, +15.9] | 26.1% | 33.1% |
| 0.25 | 278 | 26.3% [21.6, 31.5] | 24.1% [19.2, 29.1] | +2.2% [-5.6, +10.2] | 26.1% | 25.5% |
| 0.1 | 278 | 25.9% [21.3, 30.5] | 25.5% [20.8, 31.0] | +0.4% [-8.1, +8.2] | 26.1% | 23.7% |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1200 (169) | +12.9% [+9.7, +16.2] | [+10.2, +15.6] | 4.7 pts | effect |
| Δ Hit@1, b=0.5 vs 1.0 | 1200 (169) | -5.2% [-8.3, -2.2] | [-7.8, -2.6] | 4.4 pts | effect |
| Δ Hit@1, b=0.25 vs 1.0 | 1200 (169) | -8.5% [-11.5, -5.4] | [-11.1, -5.8] | 4.4 pts | effect |
| Δ Hit@1, b=0.1 vs 1.0 | 1200 (169) | -7.9% [-11.3, -4.5] | [-10.8, -5.1] | 4.8 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `complete`, rows 5634, started 2026-10-04T19:08:25+00:00, finished 2026-10-05T00:23:17+00:00
- Git `86f22005fb255e85121a118da801b755b51f4173`; Python 3.13.12; PYTHONHASHSEED=0
- Reader `qwen2.5:14b` digest `7cdf5a0187d5`
- Dataset `data/processed/ami.jsonl` sha256 `f15cc2fa6db2`
- Summaries generated 36501, clipped to budget 17704
- Headroom gate **PASS**: lift +12.9 pts [+9.7, +16.2] vs margin +5.0; headroom confirmed
