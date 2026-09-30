# Experiment Roadmap

This roadmap starts before synthetic training data exists. The goal is to validate the idea in small, controlled stages before committing to training a full predictor or controller.

## Core Question

Does future-consumer-aware memory allocation improve long-term multi-party memory compared with fixed compression, speaker-partitioned memory, and generic future-utility memory admission?

## Research Components

The proposal has two system components:

1. Future-consumer-aware memory compression.
2. Provenance-conditioned interpretation.

It also has one analysis component:

1. Failure-mode decomposition into memory formation, retrieval, and interpretation errors.

## Phase 0: Oracle Validation Before Training

Purpose:

- Test whether the core idea works if future-consumer labels are known.
- Avoid training a predictor before proving the signal is useful.

Dataset:

- Start with GroupMemBench because it is public, synthetic, multi-party, role-labeled, and already targets group memory failures.

Main comparison:

- Uniform compression.
- Speaker-partitioned memory.
- Oracle future-consumer allocation.

Key question:

- If we know which participant later needs a fact, can we preserve less total memory while improving or maintaining answer accuracy?

Expected output:

- A small oracle experiment report.
- A clear go/no-go decision for training the future-consumer predictor.

Decision gate:

- Proceed only if oracle future-consumer allocation improves the accuracy-memory tradeoff or reduces write-time information loss at matched memory budget.

Detailed checklist:

- See `PHASE_0_ORACLE_VALIDATION.md`.

## Phase 1: Weak Labels From Existing Public Data

Purpose:

- Derive provisional future-consumer labels from GroupMemBench question/evidence metadata.
- Build a prototype training/evaluation loop without generating new synthetic data yet.

Inputs to extract:

- Question asker.
- Question type.
- Gold answer.
- Evidence message or evidence span.
- Source speaker.
- Source role.
- Later participant who required the earlier fact.

Weak label:

```text
memory fact introduced at time t -> later required by asker u_q
```

Limitations:

- These labels are likely incomplete.
- They may identify only the final asker, not all possible future consumers.
- They should be used for prototyping, not final scientific claims.

Expected output:

- A weak-label dataset schema.
- A small labeled sample suitable for debugging predictors and memory allocation.

Decision gate:

- Proceed if the weak labels are consistent enough to run oracle and predictor smoke tests.

## Phase 2: Hand-Authored Toy Dataset

Purpose:

- Create a tiny but perfectly controlled dataset to debug the architecture.
- Test edge cases that public benchmarks may not isolate cleanly.

Recommended size:

- 20 to 50 conversations.

Required cases:

- Term ambiguity.
- Knowledge updates.
- Speaker-grounded questions.
- Future-consumer mismatch.
- Cross-speaker multi-hop reasoning.
- Cases where provenance matters.
- Cases where provenance should not matter.

Expected output:

- A human-readable debugging dataset.
- Unit-like examples for each architectural failure mode.

Decision gate:

- Proceed if the memory writer, oracle allocator, retriever, and interpretation prompt behave correctly on the toy set.

## Phase 3: Synthetic Data Generator

Purpose:

- Generate structured multi-party conversations with perfect labels for training.

The generator must produce:

- Participants.
- Roles.
- Facts.
- Source speaker for each fact.
- Source role for each fact.
- Conversation timestamps.
- Future consumers for each fact.
- Later questions.
- Required evidence.
- Term ambiguity labels.
- Knowledge-update labels.
- Noise and distractor messages.

Expected output:

- Synthetic training data for the future-consumer predictor.
- Contrastive examples for provenance-conditioned interpretation.
- Held-out synthetic dev and internal test splits.

Decision gate:

- Proceed if generated conversations are realistic enough for controller training and labels are reliable.

## Phase 4: Future-Consumer Predictor Training

Purpose:

- Train the first real predictor after the oracle and weak-label experiments show the signal is useful.

Start simple:

- Pairwise MLP or bi-encoder predictor as a baseline.

Then scale:

- Two-stage predictor: cheap candidate selection plus cross-encoder reranking.
- Set-based predictor for variable participant counts.
- Attention-based predictor using memory, context, and participant representations.

Metrics:

- Top-1 consumer accuracy.
- Top-k consumer recall.
- Calibration error.
- Distributional error.
- Downstream accuracy-memory tradeoff.

Decision gate:

- Proceed if the trained predictor captures enough of the oracle gain to justify full integration.

## Phase 5: Provenance-Conditioned Interpretation

Purpose:

- Test whether retrieved evidence is interpreted better when source provenance is used.

Start simple:

- Prompt baseline with explicit provenance.
- Router baseline that predicts whether provenance matters.

Then scale:

- Provenance-conditioned interpretation vectors.
- Router-controlled steering strength.

Training data:

- Synthetic contrast pairs where the same term has different meanings under different source roles.

Evaluation:

- Oracle retrieval with and without provenance.
- Oracle retrieval with prompt-based provenance.
- Oracle retrieval with router/steering.

Decision gate:

- Proceed only if provenance-conditioned interpretation improves role-ambiguous cases without hurting ordinary cases.

## Phase 6: Full System Evaluation

Purpose:

- Compare the integrated system against baselines at matched memory budgets.

Main benchmarks:

- GroupMemBench.
- LongMemEval.
- LoCoMo.

Main baselines:

- Full context.
- Sliding window.
- BM25 retrieval.
- Dense retrieval.
- AHN.
- A-MAC-style global future utility.
- Speaker-partitioned memory.
- Collaborative Memory-style private/shared memory.
- Random-consumer allocation.
- Oracle future-consumer allocation.

Main result:

- Accuracy-memory Pareto frontier.

Supporting results:

- Accuracy-latency Pareto frontier.
- Failure-mode decomposition.
- Future-consumer prediction accuracy.
- Interpretation accuracy.

## Recommended Immediate Next Step

Start with Phase 0:

1. Inspect GroupMemBench schema.
2. Confirm whether question sets include evidence IDs or enough metadata to identify supporting messages.
3. Build a tiny oracle-label sample.
4. Compare uniform compression, speaker-partitioned memory, and oracle future-consumer allocation on that sample.
