# Results And Success Criteria

## Ideal Result

The ideal result is that the proposed method achieves higher multi-party memory accuracy than AHN and standard retrieval systems while using the same or less memory.

Strongest primary evidence:

- Consistent improvements on GroupMemBench knowledge-update tasks.
- Consistent improvements on GroupMemBench term-ambiguity tasks.
- Consistent improvements on GroupMemBench speaker-grounded tasks.
- Follow-up improvements on LongMemEval and LoCoMo.

## Retrieval Is Not The Whole Story

A particularly important result would be:

- Similar retrieval recall to a strong retrieval baseline.
- Higher final answer accuracy.

Interpretation:

- The contribution is not merely better retrieval.
- The system is using and interpreting retrieved information better.

## Role-Conditioned Interpretation Success

The interpretation component succeeds if:

- It improves performance on deliberately constructed role-ambiguous examples.
- It leaves ordinary role-independent questions largely unchanged.
- Oracle-retrieval experiments show that role-conditioned vectors fix errors that remain when correct evidence is already supplied.

## Future-Consumer Prediction Success

The future-consumer prediction component succeeds if:

- Its largest improvements occur on questions requiring information that was predicted for and preserved at higher fidelity for a particular participant or role.
- Removing the future-consumer signal causes a measurable drop specifically on those questions.
- The predictor preserves high-fidelity detail for information later queried by predicted consumers.
- It compresses more aggressively for information no predicted participant ends up needing.

## Pareto Frontier Success

The strongest overall result is a better accuracy-memory Pareto frontier than:

- AHN.
- Sliding-window memory.
- Speaker-partitioned compression without prediction.
- Standard retrieval.
- Query/task-conditioned compression.

Success condition:

- Higher accuracy at the same memory budget, or comparable accuracy at substantially lower memory cost.

## Main Hypothesis Support

The main hypothesis is supported if the complete system consistently demonstrates:

- Predicting future consumer roles preserves more task-relevant information at lower memory cost than compression driven by recency or content alone.
- Provenance-conditioned interpretation reduces misinterpretation of correctly retrieved information.
- The full system improves multi-party memory tasks that existing compressed-memory systems do not directly address.

## Expected Failure-Mode Pattern

On GroupMemBench:

- Lost-at-write-time errors should shrink on knowledge-update and speaker-grounded tasks.
- Retrieved-but-misinterpreted errors should shrink on term-ambiguity and speaker-grounded tasks.
- Retrieval-only gains are not sufficient unless answer accuracy and failure decomposition show the proposed mechanisms helped.

## Stop Or Reconsider Conditions

Reconsider full integration if:

- Oracle future-consumer allocation does not beat uniform compression at the same budget.
- Oracle retrieval plus provenance-conditioned interpretation does not beat oracle retrieval without interpretation on role-ambiguous cases.
- Future-consumer predictions are poorly calibrated and do not correlate with later queries.
- Memory savings disappear after counting shared cores, residuals, provenance metadata, and predicted-consumer metadata.
