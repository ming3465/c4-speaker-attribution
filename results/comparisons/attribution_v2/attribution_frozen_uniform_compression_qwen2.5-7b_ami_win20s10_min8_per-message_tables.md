# C4 Pilot v2 — Compression-Induced Attribution Failure (frozen probes)

1200 frozen probes from 1126 contexts in 169 clusters; 1200 graded rows. Dataset `utterances`, contexts `window`, compressor `salient`, scope `both`.
Each probe is fixed once; only the text of the same messages is compressed at each budget. Roster = the speakers visible in the context, so chance = 1/|roster|. Cluster bootstrap by conversation/question, 2000 resamples. Full configuration under Provenance.

## Table 1 — attribution accuracy by budget

| Budget | n | Target words | Hit@1 [95% CI] | Chance | Frequency heuristic | Turn-taking heuristic | Lexical attributor | Hit@1 − chance [95% CI] | Valid |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1.0 | 1200 | 28.4 | 37.6% [35.0, 40.3] | 27.6% | 34.6% | 33.8% | 48.8% | +10.0% [+7.4, +12.7] | 100% |

*Frequency heuristic* = always answer the most frequently labelled visible speaker. Labels do not change with the budget, so it is constant; it is the non-binding strategy to beat.

*Turn-taking heuristic* = guess uniformly among the speakers not labelled on the turns right before and after the statement. Also label-only and constant across budgets; on conversation windows it beats chance because the next turn usually belongs to someone else. *Lexical attributor* = the speaker whose visible lines are most TF-IDF-similar to the statement, computed on the same compressed text the reader sees; a non-LLM reference for the same dose-response.

## Table 2 — paired dose-response (same probes, 1.0 vs b)

| Budget vs 1.0 | Paired n | Hit@1 at 1.0 | Hit@1 at b | Δ (b − 1.0) [95% CI] | Lost / gained | McNemar p |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |

Lost = correct at 1.0, wrong at b. Gained = the reverse. McNemar is exact and two-sided on these counts.

## Table 3 — accuracy by number of speakers in the conversation

| Speakers (roster) | Chance | b=1.0 |
| ---: | ---: | ---: |
| 2 | 50% | 69% (n=36) |
| 3 | 33% | 42% (n=275) |
| 4 | 25% | 35% (n=876) |
| 5+ | 20% | 31% (n=13) |

## Table 4 — label-swap counterfactual (binding vs prior)

Labels A ↔ B swapped on the non-target messages, with B chosen to have exactly as many labels as A. Presence and label counts are unchanged, so neither a presence nor a frequency heuristic prefers B. Following the swap = binding the statement to its author's other messages. Answering A = a content prior about A that survives the relabel. Binding index = follow − prior.

| Budget | n | Follows swap (binding) [95% CI] | Original author (prior) [95% CI] | Binding index [95% CI] | Chance | Same probes, no swap |
| ---: | ---: | --- | --- | --- | ---: | ---: |

## Table 5 — what the data can rule out

| Comparison | n (clusters) | Estimate [95% CI] | 90% CI | Detectable at 80% power | Reading (margin ±5 pts) |
| --- | ---: | --- | --- | ---: | --- |
| Hit@1 − chance at b=1.0 | 1200 (169) | +10.0% [+7.4, +12.7] | [+7.8, +12.2] | 3.7 pts | effect |

*Detectable at 80% power* = the smallest true effect this design finds 80% of the time at two-sided α = .05: (1.96 + 0.84) × cluster-bootstrap SE. Smaller true effects are likely to be missed. *Reading*: **effect** = the 95% CI excludes 0; **no effect beyond the margin** = the 90% CI lies inside ±margin (two one-sided tests, α = .05); **inconclusive** = neither, so the data cannot decide. The equivalence reading is valid only if the margin was fixed before the run.

## Provenance

- Status `stopped_at_gate`, rows 1200, started 2026-09-27T14:34:11+00:00, finished 2026-09-27T15:32:37+00:00
- Git `2ff180ca378dd7cf3360bc60e95df93405209863` (dirty tree); Python 3.13.5; PYTHONHASHSEED=0
- Reader `qwen2.5:7b` digest `845dbda0ea48`
- Dataset `data/processed/ami.jsonl` sha256 `f15cc2fa6db2`
- Headroom gate **FAIL**: lift +10.0 pts [+7.4, +12.7] vs margin +5.0; accuracy 0.376 does not clearly beat the frequency heuristic 0.346 (lower bound of the lead -0.001)
