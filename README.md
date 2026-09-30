# LLM Research Workspace

This repository is being prepared for research on future-consumer-aware memory compression and provenance-conditioned interpretation.

Start with:

```text
docs/README.md
```

## Phase 0 Quick Start

Inspect one GroupMemBench domain:

```bash
python scripts/data/inspect_groupmembench_schema.py --domain Finance --download
```

Validate oracle labels:

```bash
python scripts/data/validate_oracle_labels.py \
  --input data/processed/groupmembench/oracle_labels.jsonl
```

Phase 0 runbook:

```text
experiments/proposed/oracle_future_consumer/README.md
```

## Failure-Mode Decomposition (Contribution 4)

Attributes every wrong answer to memory formation, retrieval, or interpretation
at matched memory budgets.

```bash
python scripts/data/evidence_statistics.py
python scripts/evaluation/run_failure_decomposition.py --dataset groupmembench --domain Finance
```

- Runbook and data download: `experiments/proposed/failure_decomposition/README.md`
- Method and caveats: `docs/FAILURE_DECOMPOSITION.md`
- What each dataset actually contains: `docs/DATASET_AUDIT.md`
- Results: `results/comparisons/failure_decomposition/summary.md`
