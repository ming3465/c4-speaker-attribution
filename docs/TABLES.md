# Tables

## Table 1: Main Results - Accuracy vs Memory Budget

Purpose:

- Headline result.
- Shows whether the full system beats baselines at matched memory cost.
- Can be plotted as an accuracy-memory Pareto frontier.

Primary dataset:

- GroupMemBench.

Secondary versions:

- LongMemEval.
- LoCoMo.

Schema:

| System | 10% budget | 25% budget | 50% budget | 75% budget | Full-context upper bound |
| --- | --- | --- | --- | --- | --- |
| Sliding window |  |  |  |  |  |
| BM25 retrieval |  |  |  |  |  |
| Dense retrieval |  |  |  |  |  |
| AHN |  |  |  |  |  |
| Speaker-partitioned compressed memory, no prediction |  |  |  |  |  |
| Query/task-conditioned compression |  |  |  |  |  |
| Full system |  |  |  |  |  |
| Full system reference |  |  |  |  |  |

Cell values:

- Answer accuracy.

## Table 2: Ablation - Component Contributions

Purpose:

- Shows whether each contribution does real work.
- Prevents the result from being only "the whole system is better."

Schema:

| Variant | Answer accuracy | Speaker attribution F1 | Interpretation accuracy | Memory cost |
| --- | --- | --- | --- | --- |
| Full system |  |  |  |  |
| Remove future-consumer predictor, shared core only |  |  |  |  |
| Remove role-conditioned residual, uniform compression |  |  |  |  |
| Remove provenance-conditioned interpretation |  |  |  |  |
| Remove both compression residual and interpretation |  |  |  |  |
| Query/task-conditioned compression |  |  |  |  |
| Random-routing baseline |  |  |  |  |
| Recency-only routing baseline |  |  |  |  |

## Table 3: Failure-Mode Decomposition

Purpose:

- Shows why each system fails.
- Separates write-time loss, retrieval failure, and interpretation failure.

Run separately for each GroupMemBench category:

- Knowledge-update.
- Term-ambiguity.
- Multi-hop.
- Speaker-grounded.

Schema:

| System | Lost at write time (%) | Not retrieved (%) | Retrieved but misinterpreted (%) | Correct (%) |
| --- | --- | --- | --- | --- |
| AHN |  |  |  |  |
| Speaker-partitioned compressed memory, no prediction |  |  |  |  |
| Query/task-conditioned compression |  |  |  |  |
| Full system |  |  |  |  |

Expected pattern:

- Misinterpreted column should shrink for the full system on term-ambiguity and speaker-grounded tasks.
- Lost-at-write-time column should shrink for the full system on speaker-grounded and knowledge-update tasks.

## Table 4: Oracle Validation Gates

Purpose:

- Cheap sanity-check table before full training.
- Tests whether each mechanism is worth building before RL or full system integration.

Schema:

| Check | Condition | Answer accuracy | Interpretation accuracy | Decision |
| --- | --- | --- | --- | --- |
| Oracle consumer allocation | True future-consumer labels |  |  | Proceed or stop |
| Baseline without consumer info | Uniform compression, same memory budget |  |  | Proceed or stop |
| Oracle retrieval, no interpretation | Correct evidence supplied, no steering |  |  | Proceed or stop |
| Oracle retrieval plus interpretation | Correct evidence supplied, with steering |  |  | Proceed or stop |

Decision rule:

- If an oracle row does not clearly beat its baseline row, do not proceed to full training for that mechanism.

## Table 5: Main Results - Accuracy vs Inference Cost

Purpose:

- Same role as Table 1, but with latency or inference cost instead of memory budget.

Suggested schema:

| System | Low cost | Medium cost | High cost | Full-context upper bound | Notes |
| --- | --- | --- | --- | --- | --- |
| Sliding window |  |  |  |  |  |
| BM25 retrieval |  |  |  |  |  |
| Dense retrieval |  |  |  |  |  |
| AHN |  |  |  |  |  |
| Speaker-partitioned compressed memory, no prediction |  |  |  |  |  |
| Query/task-conditioned compression |  |  |  |  |  |
| Full system |  |  |  |  |  |

Cell values:

- Answer accuracy.

## Table 6: Future-Consumer Prediction Accuracy

Purpose:

- Proves whether the predictor is actually accurate.
- Evaluates prediction quality independently from final answer quality.

Protocol:

- At each memory-write event, the model predicts a probability distribution over future participant roles or participants that will require the memory.
- Compare this prediction against the empirical distribution of roles or participants that subsequently query or require the corresponding information.

Schema:

| Method | Top-1 consumer accuracy | Top-3 consumer recall | Distributional error | Calibration error |
| --- | --- | --- | --- | --- |
| Random |  |  |  |  |
| Recency-based |  |  |  |  |
| Query/task-conditioned |  |  |  |  |
| Future-consumer predictor |  |  |  |  |
| Oracle | 100% | 100% | 0 | 0 |

## Optional Dataset Inventory Table

Purpose:

- Summarizes benchmark size, storage format, and project use.

Recommended source:

- Use `DATASET.md` as the canonical dataset inventory.
