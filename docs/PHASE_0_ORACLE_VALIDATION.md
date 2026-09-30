# Phase 0: Oracle Validation

Phase 0 answers the question: should we train a future-consumer predictor at all?

The key trick is to temporarily skip prediction. Instead, use oracle labels for who later needs each memory and test whether that information improves memory allocation.

## Why This Comes First

Training a predictor only matters if perfect future-consumer knowledge would help.

If oracle future-consumer allocation does not beat simpler memory policies, then the project should pivot before spending time on synthetic data generation or model training.

## Phase 0 Inputs

Start with GroupMemBench.

Required fields:

- Message ID.
- Message content.
- Author.
- Author role.
- Timestamp.
- Topic or channel.
- Noise flag if available.
- Decision/update flag if available.
- Question ID.
- Question asker.
- Question type.
- Answer.
- Evidence message ID or evidence span if available.

If evidence IDs are not available, use a smaller hand-labeled sample first.

## Oracle Label Definition

For a memory fact introduced at time `t`, the oracle future consumer is the later participant who asks or requires that fact.

Minimal label:

```text
memory_message_id -> future_consumer_user_id
```

Better label:

```text
memory_message_id -> future_consumer_user_id -> question_id -> required_evidence
```

Best label:

```text
fact_id -> source_user -> source_role -> future_consumers[] -> later_questions[] -> evidence_messages[]
```

## What To Compare

### Uniform Compression

Every memory gets the same compression budget.

Example:

```text
shared summary only, 40 tokens per memory
```

Purpose:

- Tests whether differentiated fidelity is useful at all.

### Speaker-Partitioned Memory

Memories are grouped or indexed by the speaker who produced them.

Purpose:

- Tests whether knowing who said something is enough.

### Oracle Future-Consumer Allocation

Use ground-truth future consumers to allocate more fidelity to memories needed by later askers.

Purpose:

- Tests the maximum possible value of future-consumer-aware allocation before prediction error.

## Simple Oracle Allocation Rule

Start with a rule, not a learned model.

Example:

```text
if memory is needed by future asker:
    keep shared core + detailed residual
else:
    keep shared core only
```

Budgeted version:

```text
shared_core_tokens = 40
oracle_consumer_residual_tokens = 80
non_consumer_residual_tokens = 0
```

For group-relevant information:

```text
shared_core_tokens = 60
residual_tokens spread across all future consumers
```

## Minimal Experiment Loop

1. Select a small GroupMemBench subset.
2. Extract or manually label question-to-evidence links.
3. Convert evidence messages into candidate memory units.
4. Create three memory stores:
   - Uniform compression store.
   - Speaker-partitioned store.
   - Oracle future-consumer store.
5. Run the same retriever and answer model for all stores.
6. Compare answer accuracy, retrieval recall, and memory cost.
7. Classify errors into formation, retrieval, or interpretation failures.

## What Counts As Success

Oracle future-consumer allocation is useful if it:

- Improves answer accuracy at the same memory budget.
- Preserves comparable accuracy with lower memory cost.
- Reduces lost-at-write-time errors.
- Helps most on speaker-grounded and knowledge-update questions.

## What Counts As Failure

Do not train the predictor yet if:

- Oracle allocation is no better than uniform compression.
- Oracle allocation is no better than speaker-partitioned memory.
- Gains only appear because the oracle store uses more memory.
- Most errors are retrieval or answer-model errors unrelated to memory fidelity.

## Required Phase 0 Artifacts

Create these before moving to Phase 1:

- A small labeled sample of question/evidence/future-consumer links.
- A memory-budget accounting rule.
- A simple compression rule for shared cores and residuals.
- Baseline outputs for uniform compression and speaker-partitioned memory.
- Oracle allocation outputs.
- A short decision report.

## Suggested File Outputs Later

When implementation begins, store outputs like this:

```text
experiments/proposed/oracle_future_consumer/
|-- README.md
|-- config.yaml
|-- sample_labels.jsonl
`-- run_notes.md

results/proposed/oracle_future_consumer/
|-- predictions.jsonl
|-- metrics.json
`-- failure_modes.csv

results/comparisons/phase_0_oracle_validation/
|-- summary.md
|-- table_accuracy_memory.csv
`-- failure_breakdown.csv
```

## Phase 0 Decision

Proceed to predictor training only if the oracle result shows that future-consumer information has measurable value.

If the oracle result is weak, revise the idea before building the synthetic generator.

## Current Bootstrap Result

A deterministic proxy comparison has been run on 40 bootstrap labels derived from GroupMemBench Finance decision-change metadata.

An expanded deterministic proxy comparison has also been run on 108 bootstrap labels across Finance, Technology, Healthcare, and Manufacturing.

Formation proxy results:

| Strategy | Avg answer coverage | Formation success rate | Avg stored words |
| --- | ---: | ---: | ---: |
| Uniform compression | 0.3951 | 0.0250 | 79.12 |
| Speaker-partitioned memory | 0.4085 | 0.0750 | 85.25 |
| Random-consumer allocation | 0.5139 | 0.2750 | 104.12 |
| A-MAC-style metadata utility | 0.7763 | 0.8500 | 150.12 |
| Query/task-conditioned compression | 0.7763 | 0.8500 | 150.12 |
| Recency window | 0.7696 | 0.8500 | 132.97 |
| Oracle future-consumer allocation | 0.7763 | 0.8500 | 150.12 |

Retrieval-aware proxy results:

| Strategy | Recall@5 | Avg answer coverage in top-5 | Retrieval-visible success rate |
| --- | ---: | ---: | ---: |
| Uniform compression | 0.7000 | 0.4455 | 0.0750 |
| Speaker-partitioned memory | 0.6750 | 0.4839 | 0.1750 |
| Random-consumer allocation | 0.8250 | 0.5552 | 0.3500 |
| A-MAC-style metadata utility | 0.9250 | 0.7530 | 0.8750 |
| Query/task-conditioned compression | 0.9500 | 0.7799 | 0.8750 |
| Recency window | 0.9500 | 0.7754 | 0.9000 |
| Oracle future-consumer allocation | 0.9250 | 0.7562 | 0.9000 |

All-domain retrieval-aware proxy results:

| Strategy | Recall@5 | Avg answer coverage in top-5 | Retrieval-visible success rate |
| --- | ---: | ---: | ---: |
| Uniform compression | 0.7407 | 0.4746 | 0.1296 |
| Speaker-partitioned memory | 0.7407 | 0.5053 | 0.1852 |
| Random-consumer allocation | 0.8519 | 0.5669 | 0.3519 |
| A-MAC-style metadata utility | 0.9352 | 0.7297 | 0.7963 |
| Query/task-conditioned compression | 0.9444 | 0.7426 | 0.8056 |
| Recency window | 0.9444 | 0.7395 | 0.8148 |
| Oracle future-consumer allocation | 0.9352 | 0.7297 | 0.8148 |

Caveat:

- This is not a final benchmark; it is a lexical smoke test over bootstrap labels.
- This decision-change sample makes metadata, task, and recency baselines unusually strong.
- The next step is to add official typed question rows or an LLM answer-generation pass.

## Current Real LLM Pilot

A real LLM answer-generation pilot has been run on 4 stratified bootstrap labels across all domains.

| Strategy | LLM accuracy | Gold evidence retrieval rate |
| --- | ---: | ---: |
| Uniform compression | 0.25 | 0.75 |
| Speaker-partitioned memory | 0.25 | 0.75 |
| A-MAC-style metadata utility | 1.00 | 1.00 |
| Query/task-conditioned compression | 1.00 | 1.00 |
| Recency window | 1.00 | 1.00 |
| Oracle future-consumer allocation | 1.00 | 1.00 |

Conclusion:

- The LLM pilot confirms that future-consumer allocation can support correct answering.
- It does not yet prove superiority over metadata/task/recency baselines because the sampled labels are all decision-change cases.
- The next truthful pilot needs a balanced small set with speaker-grounded, term-ambiguity, and multi-hop cases.
