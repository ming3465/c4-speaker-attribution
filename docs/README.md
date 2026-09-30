# Research Docs Index

Source: `Prathamas, Sutolimin, Ryan Research Doc Template Summer 2026 (3).pdf`

Extraction note: struck-out text from the PDF was intentionally excluded. These files organize the retained proposal content into retrieval-friendly topics.

## File Map

| File | Use it for |
| --- | --- |
| `FILE_STRUCTURE.md` | Proposed repository layout for docs, data, configs, source code, experiments, and results. |
| `EXPERIMENT_ROADMAP.md` | Step-by-step plan from oracle validation to full system evaluation. |
| `PHASE_0_ORACLE_VALIDATION.md` | Detailed first experiment for testing the idea before predictor training. |
| `LLM_PILOT.md` | Real LLM answer-generation pilot design and run command. |
| `ORACLE_LABEL_SCHEMA.md` | JSONL contract for Phase 0 question/evidence/future-consumer labels. |
| `IDEA.md` | Main idea, motivation, thesis, research question, hypotheses, and contribution claims. |
| `PRIOR_WORK.md` | Related papers, overlap risks, and how each paper should be used in the proposal. |
| `METHOD.md` | System architecture, memory structure, future-consumer prediction, controllers, interpretation routing, and pipeline. |
| `TRAINING.md` | Training stages, synthetic training data, labels, and held-out evaluation rule. |
| `DATASET.md` | Dataset inventory, benchmark purpose, sizes, storage, and access format. |
| `DATASET_AUDIT.md` | What each dataset **actually** contains, verified by download; which claims each can support. |
| `BASELINE.md` | Baseline systems, controlled variants, and interpretation-specific baselines. |
| `PRACTICAL_BASELINES.md` | Easy, medium, and heavy baseline implementation plan from relevant papers. |
| `EVALUATION.md` | Experimental setup, evaluation tasks, budget matching, ablations, and failure analysis. |
| `METRICS.md` | Accuracy, retrieval, attribution, prediction, memory, latency, and statistical metrics. |
| `TABLES.md` | Planned result tables and schemas. |
| `LIMITATIONS.md` | Practical risks, conceptual tradeoffs, and known failure modes. |
| `RESULTS.md` | Ideal results, success criteria, and what would support the main hypothesis. |
| `FAILURE_DECOMPOSITION.md` | Contribution 4: bucket definitions, eligibility gate, budget matching, and known limits. |

## Retrieval Keywords

- Core claim: future-consumer-aware memory compression.
- Memory unit: shared semantic core plus role-conditioned residual detail.
- Write-time signal: predicted future participants who will require a memory.
- Read-time signal: provenance-conditioned interpretation using speaker and role metadata.
- Main benchmark: GroupMemBench.
- Main architectural baseline: AHN.
- Major baseline categories: full context, sliding window, BM25, dense retrieval, AHN, A-MAC-style global future utility, speaker-partitioned memory, Collaborative Memory-style private/shared memory, random-consumer allocation, oracle future-consumer allocation.
- Main failure decomposition: memory formation, retrieval, interpretation.
- GroupMemBench questions: GitHub `UCSB-NLP-Chang/GroupMemBench`, not the Hugging Face data repo.
- Gold evidence for GroupMemBench Finance: HF `toddzheng024/groupmembench-agent-sessions`.
