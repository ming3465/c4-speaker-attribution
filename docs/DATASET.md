# Datasets

## Dataset Roles

The project separates datasets into three roles:

- Primary evaluation: tests the core multi-party memory claim.
- Generalization evaluation: tests long-term memory beyond multi-party settings.
- Training or reproduction: supports controller training, AHN reproduction, or steering/router validation.

## Primary Evaluation Dataset

### GroupMemBench

Purpose:

- Primary benchmark for the proposed multi-party memory setting.
- Directly tests predicted-consumer-aware memory and provenance-conditioned interpretation.

Why it matters:

- Includes multi-party conversation structure.
- Evaluates knowledge updates, term ambiguity, multi-hop reasoning, temporal reasoning, and speaker-grounded understanding.
- Provides the clearest test of whether speaker identity and role-aware interpretation help.

Data notes from the source document:

- About 104,000 messages.
- 33 channels.
- 4 domains.
- About 159 MB.
- Hugging Face JSON.

Primary uses:

- Measure answer accuracy under memory budgets.
- Measure speaker attribution.
- Measure role-conditioned interpretation.
- Decompose failures into formation, retrieval, and interpretation errors.

## Generalization Evaluation Datasets

### LongMemEval-Cleaned

Purpose:

- Held-out general long-term conversational-memory benchmark.
- Used to test whether the method generalizes beyond group conversations.

Data notes from the source document:

- Three conditions: Oracle, S, and M.
- About 3.03 GB total.
- About 15.4 MB Oracle.
- About 277 MB S.
- About 2.74 GB M.
- Hugging Face JSON.

Main use:

- Decompose memory formation, retrieval, and use failures in long-term memory.

### LoCoMo

Purpose:

- Cheap held-out evaluation of long-term conversational memory and long-range dependencies.

Data notes from the source document:

- 10 long conversations.
- Includes QA and event-summarization annotations.
- About 2.68 MB.
- GitHub `locomo10.json` file.

Main use:

- Test long-range temporal and causal dependencies.

### SocialMemBench

Purpose:

- Additional external multi-party or social-memory evaluation if feasible.

Data notes from the source document:

- About 1,000 to 10,000 records across social or group conversation.
- About 2.13 MB Parquet conversion.
- Hugging Face Parquet.

Main use:

- Test multi-party social-memory generalization.

### LV-Eval

Purpose:

- Long-context evaluation benchmark used by AHN.

Data notes from the source document:

- 11 task families.
- Evaluated at context lengths up to 256K.
- About 1.4 GB.
- Hugging Face task and config files.

Main use:

- Evaluate long-context retention and compression performance at increasing context lengths.

### InfiniteBench

Purpose:

- Very-long-context benchmark relevant to AHN and memory-compression evaluation.

Data notes from the source document:

- 3,946 examples.
- Common JSONL and Parquet conversion.
- 12 tasks.
- About 2.5 GB official JSONL.
- About 506 MB Parquet.
- Hugging Face JSONL or Parquet conversion.

Main use:

- Evaluate memory and retrieval beyond 100K tokens.

### LongBench

Purpose:

- Additional general long-context benchmark.

Data notes from the source document:

- 4,750 test examples.
- 21 tasks.
- About 114 MB.
- Hugging Face task-specific configs.

Main use:

- Generalization across QA, summarization, retrieval, few-shot learning, and code tasks.

## Training And Reproduction Datasets

### Synthetic Multi-Party Training Dataset

Purpose:

- Train the future-consumer predictor and provenance-aware interpretation mechanism.

Required structure:

- Generated from structured multi-party conversation scenarios.
- Includes speaker identity, role, temporal information, importance, ground-truth evidence, and later participants who require each fact.
- Contains cases where fixed recency-based memory is likely to fail.

Initial target:

- About 10,000 multi-party conversations.
- Separate development and internal test sets.

### ChatQA2 Long-SFT

Purpose:

- Training or reproduction dataset used by AHN for its compressed long-context memory module.

Data notes from the source document:

- 195,480 rows.
- About 17.3 GB.
- Hugging Face JSON.

Main use:

- Reproduce or train AHN-style compressed memory components.

Limitation:

- Does not provide future-consumer supervision.

### MMLU

Purpose:

- Reproduction or validation of RISER-style steering/router machinery.

Data notes from the source document:

- 231,400 rows.
- About 270 MB.
- Hugging Face Parquet.

Limitation:

- Not directly useful for future-consumer conversational-memory training.

### MMLU-Pro

Purpose:

- Evaluation or reproduction of RISER-style routing and reasoning mechanisms.

Data notes from the source document:

- 12,102 questions.
- About 4.21 MB.
- Hugging Face.

Limitation:

- Not conversational-memory supervision.

## Evaluation Priority

1. GroupMemBench: primary test of the main proposal.
2. LongMemEval and LoCoMo: general long-term memory checks.
3. SocialMemBench: optional external social or group memory check.
4. LV-Eval, InfiniteBench, and LongBench: broader long-context checks if compute permits.
5. Synthetic dataset: controller training only, not scientific proof.
