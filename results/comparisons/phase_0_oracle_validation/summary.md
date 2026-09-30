# Phase 0 Proxy Comparison Summary

## Status

Completed deterministic proxy comparisons on 40 bootstrap oracle labels derived from GroupMemBench Finance decision-change metadata.

Expanded run completed on 108 bootstrap oracle labels across all four GroupMemBench domains: Finance, Technology, Healthcare, and Manufacturing.

This is not a final benchmark. It is a smoke test for whether oracle future-consumer allocation exposes more answer-relevant information to the later consumer than simpler allocation strategies.

## Inputs

- Labels: `data/processed/groupmembench/oracle_labels.bootstrap.jsonl`
- Config: `configs/experiments/phase0_oracle_validation.json`
- Label source: decision-change metadata from GroupMemBench Finance messages.
- Label caveat: bootstrap labels are generated from structured decision-change rows, not official GroupMemBench typed question rows.

## Formation Proxy Metric

The formation proxy measures answer-token coverage:

```text
gold answer terms visible to the question asker / gold answer terms
```

Formation success is counted when answer coverage is at least `0.65`.

## Formation Proxy Results

### Finance-Only, 40 Labels

| Strategy | Avg answer coverage | Formation success rate | Avg stored words |
| --- | ---: | ---: | ---: |
| Uniform compression | 0.3951 | 0.0250 | 79.12 |
| Speaker-partitioned memory | 0.4085 | 0.0750 | 85.25 |
| Random-consumer allocation | 0.5139 | 0.2750 | 104.12 |
| A-MAC-style metadata utility | 0.7763 | 0.8500 | 150.12 |
| Query/task-conditioned compression | 0.7763 | 0.8500 | 150.12 |
| Recency window | 0.7696 | 0.8500 | 132.97 |
| Oracle future-consumer allocation | 0.7763 | 0.8500 | 150.12 |

### All Domains, 108 Labels

| Strategy | Avg answer coverage | Formation success rate | Avg stored words |
| --- | ---: | ---: | ---: |
| Uniform compression | 0.4637 | 0.1019 | 71.31 |
| Speaker-partitioned memory | 0.4707 | 0.1204 | 75.07 |
| Random-consumer allocation | 0.5567 | 0.3241 | 89.24 |
| A-MAC-style metadata utility | 0.7491 | 0.8056 | 123.27 |
| Query/task-conditioned compression | 0.7491 | 0.8056 | 123.13 |
| Recency window | 0.7437 | 0.8056 | 112.23 |
| Oracle future-consumer allocation | 0.7491 | 0.8056 | 123.27 |

## Retrieval-Aware Proxy Metric

The retrieval proxy builds a lexical index over messages in the same channel, synthesizes a query from decision-change metadata, retrieves top-5 visible memory units, and measures:

- Whether any gold evidence message appears in top-5.
- Gold-answer token coverage in the retrieved visible text.
- Whether retrieval plus visible content reaches the `0.65` coverage threshold.

## Retrieval-Aware Proxy Results

### Finance-Only, 40 Labels

| Strategy | Recall@5 | Avg answer coverage in top-5 | Retrieval-visible success rate | Avg indexed words |
| --- | ---: | ---: | ---: | ---: |
| Uniform compression | 0.7000 | 0.4455 | 0.0750 | 193600.73 |
| Speaker-partitioned memory | 0.6750 | 0.4839 | 0.1750 | 220192.12 |
| Random-consumer allocation | 0.8250 | 0.5552 | 0.3500 | 228446.08 |
| A-MAC-style metadata utility | 0.9250 | 0.7530 | 0.8750 | 254474.08 |
| Query/task-conditioned compression | 0.9500 | 0.7799 | 0.8750 | 260956.80 |
| Recency window | 0.9500 | 0.7754 | 0.9000 | 257248.90 |
| Oracle future-consumer allocation | 0.9250 | 0.7562 | 0.9000 | 193671.73 |

### All Domains, 108 Labels

| Strategy | Recall@5 | Avg answer coverage in top-5 | Retrieval-visible success rate | Avg indexed words |
| --- | ---: | ---: | ---: | ---: |
| Uniform compression | 0.7407 | 0.4746 | 0.1296 | 135518.37 |
| Speaker-partitioned memory | 0.7407 | 0.5053 | 0.1852 | 150654.52 |
| Random-consumer allocation | 0.8519 | 0.5669 | 0.3519 | 156071.08 |
| A-MAC-style metadata utility | 0.9352 | 0.7297 | 0.7963 | 170913.12 |
| Query/task-conditioned compression | 0.9444 | 0.7426 | 0.8056 | 171093.63 |
| Recency window | 0.9444 | 0.7395 | 0.8148 | 171141.49 |
| Oracle future-consumer allocation | 0.9352 | 0.7297 | 0.8148 | 135570.32 |

## Interpretation

On this bootstrap sample, oracle future-consumer allocation makes much more of the gold answer visible to the later consumer than uniform compression or speaker-partitioned allocation.

The important early comparison is speaker-partitioned memory versus oracle future-consumer allocation. Speaker-partitioned residuals are attached to the source speaker, while oracle residuals are attached to the future consumer. The oracle version therefore exposes substantially more answer-relevant detail to the later asker.

Adding easy baselines makes the result more nuanced. Because the bootstrap labels are all decision-change cases, A-MAC-style metadata utility, query/task-conditioned compression, and recency-window baselines are strong. In the all-domain retrieval proxy, oracle future-consumer allocation ties the best success rate while using far fewer indexed words than metadata, task, or recency baselines. This suggests the consumer-aware allocation signal may be memory-efficient, but the next fair test needs more diverse question types, not only decision changes.

## Caveats

- This is a deterministic lexical proxy, not an LLM answer-generation evaluation.
- The labels are bootstrap labels from decision-change metadata, not official GroupMemBench question rows.
- The current expanded sample is 108 labels across all four domains.
- Retrieval queries are synthesized from decision-change metadata.
- The current comparison does not test provenance-conditioned interpretation.
- This sample favors decision/recency/task baselines because every label is generated from decision-change metadata.

## Next Decision

The result is strong enough to justify the next Phase 0 step:

1. Add official GroupMemBench typed question rows if the companion repo is available.
2. Expand beyond Finance or manually label additional domains.
3. Add an LLM answer-generation pass over retrieved visible memories.
4. Add provenance-conditioned interpretation cases separately.

## Real LLM Pilot

A real LLM answer-generation pilot has now been run on 4 stratified bootstrap labels.

| Strategy | LLM accuracy | Gold evidence retrieval rate |
| --- | ---: | ---: |
| Uniform compression | 0.25 | 0.75 |
| Speaker-partitioned memory | 0.25 | 0.75 |
| A-MAC-style metadata utility | 1.00 | 1.00 |
| Query/task-conditioned compression | 1.00 | 1.00 |
| Recency window | 1.00 | 1.00 |
| Oracle future-consumer allocation | 1.00 | 1.00 |

Report: `results/comparisons/phase_0_oracle_validation/llm_pilot/report.md`.

Truthful conclusion:

- Future-consumer allocation works in this real LLM pilot.
- It does not yet beat the strongest easy baselines on decision-change-only data.
- A balanced pilot set is needed before making a novelty claim over A-MAC-style, task-conditioned, or recency baselines.
