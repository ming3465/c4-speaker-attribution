# Practical Baselines

This file separates relevant-paper baselines into what is easy to run now, what is medium effort, and what should wait until the proposal has a stronger implementation.

## Easy Baselines To Try Now

### Uniform Compression

Source idea:

- Generic fixed compression baseline.

Implementation:

- Keep the same shared core length for every message.
- No residual detail.

Why easy:

- Already implemented in the Phase 0 proxy runners.

Tests:

- Whether differentiated fidelity is useful.

### Speaker-Partitioned Memory

Source idea:

- Collaborative Memory, MuPPET, AFA-style speaker/user-specific memory structure.

Implementation:

- Store residual detail under the source speaker.
- The later asker only sees residual detail if they are the same person as the source speaker.
- Otherwise they see only the shared core.

Why easy:

- Already implemented in the Phase 0 proxy runners.

Tests:

- Whether knowing who said something is enough.

### BM25 / Lexical Retrieval

Source idea:

- Standard retrieval baseline; GroupMemBench reports BM25 can be strong.

Implementation:

- Use lexical token overlap or BM25-style scoring over compressed visible memories.
- Retrieve top-k memory units.

Why easy:

- A simple lexical retrieval proxy already exists.
- A true BM25 version can be added without training.

Tests:

- Whether the proposed memory structure improves evidence visibility beyond retrieval alone.

### Recency Window

Source idea:

- Sliding-window memory baseline.

Implementation:

- Only index the most recent `N` messages before the query.
- Older messages are unavailable.

Why easy:

- No model training.
- Uses message timestamps already in GroupMemBench.

Tests:

- Whether long-term memory is needed at all.

### Random-Consumer Allocation

Source idea:

- Control baseline for consumer-specific residuals.

Implementation:

- Assign residual detail to a random participant instead of the oracle future consumer.
- Keep the same residual budget as oracle allocation.

Why easy:

- No model training.
- Tests whether any consumer-specific residual helps, or whether the right consumer matters.

Tests:

- Whether oracle gains are due to meaningful future-consumer assignment rather than extra residual storage.

### A-MAC-Style Global Future Utility

Source idea:

- Adaptive Memory Admission Control.

Implementation:

- Score messages using available metadata such as `is_decision_point`, `decision_type`, `is_noise`, and recency.
- Allocate residual detail to globally important messages, independent of who later needs them.

Why easy:

- GroupMemBench has structured fields that can serve as a simple future-utility proxy.
- No trained admission model required for the first version.

Tests:

- Whether consumer-specific future utility beats global future utility.

### Query/Task-Conditioned Compression

Source idea:

- WhenLoss-like future-question or task-conditioned memory allocation.

Implementation:

- Allocate residual detail to messages whose topic, phase, or decision metadata overlaps the synthetic query.
- Do not use the future consumer identity.

Why easy:

- Can be implemented as a lexical overlap/rule baseline.

Tests:

- Whether predicting the future person adds value beyond predicting the future question/task.

## Easy Analogue Of RISER

RISER itself is not a memory baseline. It routes activation-steering vectors for reasoning skills, not long-term memory allocation.

However, an easy RISER-inspired baseline is useful for the second module:

### Static Provenance Prompting

Implementation:

- Give retrieved evidence plus source speaker and role in the prompt.
- No steering vectors.
- No learned router.

Tests:

- Whether provenance alone solves interpretation without activation steering.

### Rule-Based Provenance Router

Implementation:

- If query or evidence contains ambiguous terms, include provenance.
- Otherwise omit provenance.

Tests:

- Whether a simple provenance gate is enough.

### Static Role-Vector Placeholder

Implementation:

- Do not implement activation steering yet.
- Represent this as a planned later baseline after an LLM answer-generation loop exists.

Why wait:

- Real RISER-style steering needs model internals and activation access.
- It is not needed for the current Phase 0 memory allocation test.

## Medium-Effort Baselines

### Dense Retrieval

Implementation:

- Use sentence-transformer or model embeddings over visible memory units.
- Retrieve top-k by cosine similarity.

Why medium:

- Needs embedding model dependency and possibly GPU/CPU runtime decisions.

Tests:

- Whether memory allocation still matters with semantic retrieval.

### Collaborative Memory-Style Private/Shared Store

Implementation:

- Store shared core for everyone.
- Store private residuals under source speaker.
- Optionally promote decision-point messages to shared memory.

Why medium:

- Needs careful memory accounting to compare fairly.

Tests:

- Whether predicted-consumer allocation beats private/shared organization.

### A-MAC Learned Admission

Implementation:

- Train or fit a small classifier/ranker for global future utility.

Why medium:

- Needs labels and training setup.

Tests:

- Stronger global-utility baseline.

## Heavy Baselines To Delay

### AHN

Why relevant:

- Main fixed compressed-memory architecture baseline.

Why delay:

- Requires reproducing AHN-style compressed recurrent memory and model integration.
- Much heavier than lexical or metadata-based baselines.

When to run:

- After Phase 0 shows the future-consumer signal is worth pursuing.

### AtomMem

Why relevant:

- Closest dynamic CRUD-style memory-management prior work.

Why delay:

- Requires policy training and memory-operation orchestration.
- Not necessary for proving the future-consumer signal.

When to run:

- Later, as a stronger adaptive memory baseline.

### RISER-Style Activation Steering

Why relevant:

- Useful precedent for router-selected steering vectors.

Why delay:

- Applies to the provenance interpretation module, not the memory allocation module.
- Requires activation intervention in the base model.

When to run:

- After prompt-based provenance interpretation shows there is an interpretation gap.

## Recommended Immediate Additions

These have now been added to the Phase 0 proxy runners:

1. Recency window.
2. Random-consumer allocation.
3. A-MAC-style metadata utility.
4. Query/task-conditioned compression.

These four are easy, relevant, and directly test whether oracle future-consumer allocation is beating simple alternatives.

Current lesson:

- On decision-change-only bootstrap labels, A-MAC-style metadata utility, query/task-conditioned compression, and recency-window baselines are strong.
- The next fair baseline test should include non-decision question types, especially term ambiguity, speaker-grounded facts, and cross-speaker multi-hop questions.
