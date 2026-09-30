# Metrics

## Primary Task Metric

### Answer Accuracy

Measures whether the final answer is correct.

Use:

- Primary headline metric.
- Must be interpreted alongside memory cost and latency.

## Retrieval Metrics

### Retrieval Recall@1, Recall@5, Recall@10

Measures whether the correct evidence appears in the retrieved set.

Use:

- Distinguish retrieval failures from formation or interpretation failures.

### Mean Reciprocal Rank

Measures whether relevant evidence appears near the top of retrieval results.

Use:

- Detect whether the system retrieves correct evidence but ranks it too low.

## Speaker And Role Metrics

### Speaker Attribution Accuracy

Measures whether the system correctly identifies who provided a piece of information.

Use:

- Tests whether speaker identity survives compression and retrieval.

### Speaker-Level F1

Measures precision and recall for speaker attribution.

Use:

- More robust than accuracy when speakers or classes are imbalanced.

### Role-Conditioned Interpretation Accuracy

Measures whether the system interprets role-dependent terms or facts correctly.

Use:

- Applied to examples where the same terminology has different meanings depending on source role.
- Key metric for provenance-conditioned interpretation.

## Future-Consumer Prediction Metrics

### Future-Consumer Prediction Accuracy

Compares the predicted future-consumer distribution against the roles or participants that actually later query or require the fact.

Use:

- Measures whether the predictive signal driving fidelity allocation is accurate independent of final answer accuracy.

### Top-1 Consumer Accuracy

Measures whether the highest-probability predicted consumer is actually a later consumer.

### Top-3 Consumer Recall

Measures whether any actual later consumer appears in the top three predicted consumers.

### Distributional Error

Measures distance between predicted consumer distribution and empirical consumer distribution.

Candidate forms:

- KL divergence.
- Jensen-Shannon divergence.
- Earth mover's distance if consumer ordering or role similarity is defined.

### Calibration Error

Measures whether predicted probabilities match observed future-consumer frequencies.

Use:

- Important because budget allocation depends on probability quality, not only ranking.

## Memory And Efficiency Metrics

### Memory Compression Ratio

Measures how much the original conversation has been compressed.

### Memory Cost

Measures effective memory required relative to full-context inference.

Include:

- Shared semantic cores.
- Role-conditioned residuals.
- Provenance metadata.
- Predicted-consumer metadata.

### Latency

Measure:

- End-to-end inference time.
- Memory-operation cost.
- Retrieval cost.
- Interpretation-routing cost.

### Token Usage

Measures how much context is inserted or generated.

Use:

- Prevents a retrieval system from looking efficient while secretly using much more prompt context.

## Pareto Metrics

### Accuracy-Memory Pareto Frontier

Most important overall comparison.

Success condition:

- Higher accuracy at the same memory budget, or similar accuracy at much lower memory cost.

### Accuracy-Latency Pareto Frontier

Secondary efficiency comparison.

Success condition:

- Higher accuracy at the same latency, or similar accuracy with lower inference time.

## Failure-Mode Metrics

For each system and GroupMemBench category, track:

- Lost at write time.
- Not retrieved.
- Retrieved but misinterpreted.
- Correct.

Use:

- Shows why each system fails, not just how often.
- The proposal should reduce write-time loss on knowledge-update and speaker-grounded tasks.
- The proposal should reduce misinterpretation on term-ambiguity and speaker-grounded tasks.

## Statistical Reporting

Report:

- Paired differences.
- Bootstrap confidence intervals.
- McNemar's test where systems answer the same questions.
- Effect sizes.
