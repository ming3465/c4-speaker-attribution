# Baselines

## Baseline Purpose

Baselines should answer three questions:

1. Does predicted-consumer-aware compression beat fixed or general-purpose memory methods at matched memory budgets?
2. Does predicting who will need information add value beyond knowing who said it?
3. Does provenance-conditioned interpretation add value beyond retrieving evidence or prompting with provenance?

## Core End-to-End Baselines

### Full-Context Inference

Retains the complete conversation whenever possible.

Purpose:

- Upper reference point for memory experiments.
- Shows performance when no compression or retrieval bottleneck is imposed.

### Sliding Window

Keeps only recent context and discards older information.

Purpose:

- Lower reference point.
- Tests how much performance is lost when long-term memory is absent.

### AHN

Uses the original AHN-style fixed compressed-memory architecture.

Purpose:

- Primary architectural long-context baseline.
- Tests whether predictive audience-aware compression improves over fixed compression at the same memory budget.

### BM25 Retrieval

Retrieves older information using sparse lexical matching.

Purpose:

- Strong simple retrieval baseline.
- Important because GroupMemBench reports that BM25 can perform surprisingly well.

### Dense Retrieval

Retrieves older information using dense semantic similarity.

Purpose:

- Standard retrieval-based memory baseline.
- Tests whether the proposal improves beyond semantic retrieval.

## Memory-Allocation Baselines

### Uniform Compression

Applies the same compression or fidelity policy to every memory under the same total memory budget.

Purpose:

- Simplest comparison against differentiated consumer-aware allocation.

### Recency-Based Allocation

Allocates memory based on how recent information is.

Purpose:

- Tests whether future-consumer prediction beats a simple temporal heuristic.

### A-MAC-Style Global Future Utility

Allocates memory according to predicted future usefulness without modeling which participant will need the memory.

Purpose:

- Critical comparison against the proposal.
- Tests whether consumer-specific future demand adds information beyond global future utility.

### Speaker-Partitioned Memory

Compresses and separates information by speaker, similar to existing multi-user memory designs, without predicting who will need information later.

Purpose:

- Tests whether simply preserving source speaker is enough.
- Main comparison for the future-consumer component.

### Collaborative Memory-Style Private/Shared Memory

Maintains shared information plus source-user-specific information, without future-consumer prediction.

Purpose:

- Tests whether the proposal improves over private/shared memory organization.
- Ensures gains are not merely from user-specific storage.

### Query/Task-Conditioned Compression

Compresses or allocates memory based on anticipated future question or task, but not predicted future participant.

Purpose:

- Tests whether predicting the future consumer is better than predicting only the future information need.

### Random-Consumer Allocation

Assigns extra residual fidelity to randomly selected participants while preserving the same total memory budget.

Purpose:

- Controls for the possibility that consumer-specific residual representations help even without meaningful prediction.

### Oracle Future-Consumer Allocation

Uses ground-truth participants who later require each memory.

Purpose:

- Upper bound on the possible benefit of perfect future-consumer prediction.
- Tests whether consumer identity is useful for allocation before prediction error is introduced.

## Controlled System Variants

Use these ablations to isolate the contribution of each proposed component:

- Full system.
- Remove future-consumer prediction.
- Remove role-conditioned residual detail.
- Remove provenance-conditioned interpretation.
- Remove both compression residual and interpretation components.
- Remove speaker or role information from retrieval.
- Random-routing baseline.
- Recency-only routing baseline.

## Interpretation-Specific Baselines

These should be evaluated while holding retrieved evidence fixed:

- Retrieved evidence without provenance.
- Retrieved evidence with explicit provenance included in the prompt, but no activation steering.
- Static role-based steering without a provenance-aware router.
- Dynamic steering without source provenance.
- Full provenance-conditioned interpretation mechanism.
- Oracle interpretation condition.

The explicit-provenance prompting baseline is especially important because it tests whether activation steering adds value beyond simply telling the model who produced the retrieved evidence.

## Most Important Comparisons

### AHN vs Full System

Matched memory budget comparison. Tests whether predictive audience-aware compression improves over fixed compressed memory.

### Speaker-Partitioned Memory vs Full System

Tests whether predicting who will need information adds value beyond knowing who said it.

### Evidence-Held-Fixed Interpretation Comparison

Tests whether provenance-conditioned interpretation improves answers when retrieval is not the bottleneck.

### A-MAC-Style Global Future Utility vs Full System

Tests whether consumer-specific future demand adds value beyond generic predicted future utility.

## Practical Baseline Plan

For implementation order, see `PRACTICAL_BASELINES.md`.

Immediate low-effort baselines:

- Uniform compression.
- Speaker-partitioned memory.
- BM25 or lexical retrieval.
- Recency window.
- Random-consumer allocation.
- A-MAC-style metadata utility.
- Query/task-conditioned compression.

Baselines to delay until later:

- AHN reproduction.
- AtomMem-style dynamic CRUD memory.
- RISER-style activation steering.
