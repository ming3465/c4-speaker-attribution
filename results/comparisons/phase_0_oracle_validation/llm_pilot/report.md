# Phase 0 LLM Pilot Report

## Status

Completed a real LLM answer-generation pilot on 4 stratified bootstrap labels across Finance, Healthcare, Manufacturing, and Technology.

This pilot uses actual LLM answers, not lexical proxy scoring. Each strategy is evaluated in a separate LLM call so the model cannot see another strategy's context.

## Setup

- Answer model: `gpt-5.6-sol` through Codex CLI.
- Judge model: `gpt-5.6-sol` through Codex CLI.
- Labels: `data/processed/groupmembench/oracle_labels.bootstrap_all_domains.jsonl`.
- Sample size: 4 labels.
- Strategies: 6.
- Total predictions: 24.
- Retrieval: top-5 lexical retrieval over visible memory units.

## Strategies Tested

| Strategy | Description |
| --- | --- |
| Uniform compression | Shared core only. |
| Speaker-partitioned memory | Residual detail is visible when the asker is the source speaker. |
| A-MAC-style metadata utility | Residual detail is retained for decision-point messages. |
| Query/task-conditioned compression | Residual detail is retained when topic/task terms overlap the query. |
| Recency window | Residual detail is retained for recent/current messages. |
| Oracle future-consumer allocation | Residual detail is retained for the known future consumer. |

## LLM Accuracy Results

| Strategy | LLM accuracy | Gold evidence retrieval rate |
| --- | ---: | ---: |
| Uniform compression | 0.25 | 0.75 |
| Speaker-partitioned memory | 0.25 | 0.75 |
| A-MAC-style metadata utility | 1.00 | 1.00 |
| Query/task-conditioned compression | 1.00 | 1.00 |
| Recency window | 1.00 | 1.00 |
| Oracle future-consumer allocation | 1.00 | 1.00 |

## Interpretation

The real LLM pilot confirms the proxy pattern on this tiny decision-change sample:

- Uniform compression and speaker-partitioned memory often do not expose enough detail for the LLM to answer correctly.
- Oracle future-consumer allocation gives the LLM enough information on all four sampled labels.
- A-MAC-style metadata utility, query/task-conditioned compression, and recency-window baselines also solve all four labels.

The result is therefore not "oracle future-consumer wins overall." The accurate conclusion is narrower:

```text
On this small decision-change pilot, future-consumer allocation works, but strong metadata/task/recency baselines also work.
```

The reason is that every sampled task asks about a changed decision. Decision metadata and recency are highly aligned with the correct answer, so these baselines are unusually strong.

## What This Means For Novelty

This pilot does not yet prove the main novelty over A-MAC-style or task-conditioned baselines.

It does support continuing because oracle future-consumer allocation reaches perfect accuracy in this sample. But the next truthful test must include cases where:

- The relevant fact is not simply the newest decision.
- The relevant fact is useful to one future participant but not globally important.
- Metadata utility and recency are insufficient.
- Speaker partitioning preserves the wrong dimension.

## Caveats

- Only 4 labels.
- Bootstrap questions derived from decision-change metadata, not official GroupMemBench typed question rows.
- Answer and judge use the same model family.
- The pilot tests only Contribution 1: future-consumer-aware memory allocation.
- It does not test provenance-conditioned interpretation.

## Next Step

Create or label a small balanced pilot set with:

- 4 decision-change questions.
- 4 speaker-grounded questions.
- 4 term-ambiguity questions.
- 4 cross-speaker multi-hop questions.

Then rerun the same LLM pilot. That is the first fair test of whether future-consumer allocation beats metadata, task, and recency baselines.
