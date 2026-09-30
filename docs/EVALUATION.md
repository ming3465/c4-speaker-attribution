# Evaluation

## Model Setup

Primary model:

- Qwen2.5-3B-Instruct.

Reason:

- AHN already demonstrates compressed recurrent memory with Qwen2.5-3B-Instruct, making it a practical starting point for reproduction and extension.

Generalization models, if compute permits:

- Qwen2.5-7B-Instruct.
- Llama-3.2-3B-Instruct.

Training scope:

- Base models remain frozen.
- Train only the lightweight memory and interpretation components.

## Primary Evaluation

GroupMemBench is the primary evaluation because it directly matches the multi-party memory problem.

Focus categories:

- Knowledge updates.
- Term ambiguity.
- Multi-hop reasoning.
- Speaker-grounded questions.

Why these categories matter:

- Knowledge updates test whether new facts replace or modify old facts.
- Term ambiguity tests whether provenance-conditioned interpretation helps when meaning depends on source role.
- Multi-hop reasoning tests whether the system can combine information across memories and participants.
- Speaker-grounded questions test whether speaker identity and attribution survive compression.

## Secondary Evaluation

Use LongMemEval and LoCoMo to test whether the system improves general long-term memory beyond multi-party conversations.

Use SocialMemBench as an additional external multi-party or social-memory evaluation if implementation and dataset availability permit.

## Memory Budgets

Evaluate each system across multiple memory budgets rather than a single setting.

Suggested budgets relative to full-context memory:

- 10%.
- 25%.
- 50%.
- 75%.
- Full context as upper bound.

Purpose:

- Determine whether the proposed system is more efficient, not merely more accurate because it stores more information.
- Plot accuracy-memory and accuracy-latency Pareto frontiers.

## Matched-Budget Protocol

When comparing memory-allocation methods, keep the following identical wherever possible:

- Candidate memory units.
- Compressor.
- Retriever.
- Retrieval top-k.
- Answering LLM.
- Total memory budget.

Only change the policy that determines which information receives additional fidelity.

Memory accounting must include:

- Shared semantic core.
- Consumer-specific residuals.
- Any extra metadata required for speaker, role, or predicted-consumer information.

## Key Experiments

### Main Accuracy-Memory Comparison

Compare the full system against full context, sliding window, BM25 retrieval, dense retrieval, AHN, speaker-partitioned memory, query/task-conditioned compression, and other allocation baselines at matched budgets.

Primary result:

- Accuracy on GroupMemBench.

Secondary results:

- Repeat the same structure on LongMemEval and LoCoMo.

### AHN Comparison

Compare AHN and the proposed system at the same memory budget.

Claim tested:

- Predictive audience-aware compression outperforms fixed compression.

### Speaker-Partitioned Comparison

Compare speaker-partitioned compressed memory against the full system.

Claim tested:

- Predicting who will need information adds value beyond knowing who said it.

### Interpretation-Held-Fixed Comparison

Hold retrieved evidence fixed and vary interpretation mechanism.

Claim tested:

- Provenance-conditioned interpretation improves answers when retrieval is not the bottleneck.

### Oracle Future-Consumer Check

Use true future-consumer labels to allocate memory.

Claim tested:

- Consumer identity is useful for memory allocation before prediction error is introduced.

### Oracle Retrieval Check

Provide correct evidence directly to the model.

Claim tested:

- If the model still fails, the error is interpretation rather than retrieval.
- Repeating this with and without role-conditioned vectors tests whether the interpretation mechanism addresses residual failures.

## Ablation Plan

Remove or replace these components one at a time:

- Future-consumer predictor.
- Role-conditioned residual mechanism.
- Provenance-conditioned interpretation vectors.
- Speaker and role information in retrieval.
- Random routing instead of learned routing.
- Recency-only routing instead of learned routing.

Purpose:

- Show that gains come from the proposed mechanisms rather than from adding more components.

## Failure-Mode Decomposition

Classify each error into one of three categories:

### Memory-Formation Failure

The required information or provenance was lost during write-time allocation, compression, summarization, or storage.

Example:

- A compressed memory preserves the general topic but removes the identity or role of the person who made the statement.
- A shared core remains but consumer-specific detail needed later was discarded.

### Retrieval Failure

The required information exists in stored memory but is not selected when the question is asked.

Example:

- The read controller searches the wrong participant-related memory.
- The correct evidence is ranked below the selected top-k results.

### Interpretation Failure

The correct evidence and provenance are retrieved, but the model uses them incorrectly.

Example:

- The model retrieves a statement containing "token" but resolves the meaning incorrectly because it ignores whether the original speaker meant authentication, language-model tokenization, or project resources.

Restriction:

- Interpretation failure should be used only when the error genuinely depends on source provenance or context, not for ordinary arithmetic, factual recall, or unrelated reasoning mistakes.

## Qualitative Analysis

Track whether controller decisions correspond to meaningful conversational events.

Examples to inspect:

- Speaker commitments.
- Decisions.
- Updated facts.
- Technical details.
- Irrelevant conversational remarks.

Purpose:

- Determine whether the controller learns an importance policy rather than another recency heuristic.

## Statistical Analysis

Report:

- Paired performance differences.
- Bootstrap confidence intervals.
- Paired significance tests such as McNemar's test when the same questions are evaluated by two systems.
- Effect sizes, so small but statistically significant gains are not overstated.
