# File Structure Proposal

This structure is meant to keep the research project easy to retrieve, reproduce, and extend. The current `docs/` folder should stay as the high-level knowledge base, while future implementation, data, experiments, and outputs live in separate top-level folders.

## Recommended Repository Layout

```text
.
|-- docs/
|   |-- README.md
|   |-- FILE_STRUCTURE.md
|   |-- IDEA.md
|   |-- PRIOR_WORK.md
|   |-- METHOD.md
|   |-- TRAINING.md
|   |-- DATASET.md
|   |-- BASELINE.md
|   |-- EVALUATION.md
|   |-- METRICS.md
|   |-- TABLES.md
|   |-- LIMITATIONS.md
|   `-- RESULTS.md
|-- data/
|   |-- raw/
|   |-- interim/
|   |-- processed/
|   |-- synthetic/
|   `-- README.md
|-- configs/
|   |-- models/
|   |-- datasets/
|   |-- training/
|   |-- evaluation/
|   `-- ablations/
|-- src/
|   |-- memory/
|   |-- controllers/
|   |-- retrieval/
|   |-- steering/
|   |-- training/
|   |-- evaluation/
|   |-- datasets/
|   `-- utils/
|-- scripts/
|   |-- data/
|   |-- training/
|   |-- evaluation/
|   `-- analysis/
|-- experiments/
|   |-- baselines/
|   |-- proposed/
|   |-- ablations/
|   |-- sweeps/
|   `-- notes/
|-- results/
|   |-- baselines/
|   |-- proposed/
|   |-- ablations/
|   |-- comparisons/
|   |-- tables/
|   |-- figures/
|   |-- logs/
|   `-- reports/
|-- references/
|   |-- papers/
|   |-- citations/
|   `-- notes/
|-- pyproject.toml
|-- README.md
`-- .gitignore
```

## Folder Responsibilities

### `docs/`

Human-readable research memory. Keep this folder concise, stable, and retrieval-friendly.

Use it for:

- Research idea and hypotheses.
- Prior work summaries.
- Method design.
- Dataset and baseline inventory.
- Evaluation plans.
- Metrics and tables.
- Limitations and expected results.

Do not use it for:

- Raw data.
- Generated experiment logs.
- Large figures.
- Implementation code.

### `data/`

All dataset files and generated training/evaluation artifacts.

Recommended subfolders:

- `raw/`: downloaded datasets exactly as received.
- `interim/`: partially transformed files.
- `processed/`: finalized model-ready datasets.
- `synthetic/`: generated multi-party training data and structured dependency graphs.

Rule:

- Large files should usually be gitignored or tracked with a data/versioning tool.

### `configs/`

Declarative experiment configuration.

Recommended subfolders:

- `models/`: model names, checkpoints, tokenizer settings.
- `datasets/`: dataset paths, splits, preprocessing options.
- `training/`: optimizer, batch size, learning rate, stage settings.
- `evaluation/`: benchmark, metric, memory-budget, and retrieval settings.
- `ablations/`: component-removal and baseline configs.

Rule:

- Every important run should be reproducible from a config file.

### `src/`

Research implementation code.

Recommended subfolders:

- `memory/`: memory units, shared semantic core, residual detail, memory accounting.
- `controllers/`: future-consumer predictor, write controller, read controller.
- `retrieval/`: BM25, dense retrieval, speaker/role-aware retrieval.
- `steering/`: provenance router, interpretation vectors, steering application.
- `training/`: supervised training and optional joint refinement loops.
- `evaluation/`: benchmark runners, scoring, failure-mode decomposition.
- `datasets/`: loaders, synthetic data generator, preprocessing.
- `utils/`: shared helpers.

Rule:

- Keep model-agnostic logic separate from model-specific integration where possible.

### `scripts/`

Small command-line entrypoints for common tasks.

Recommended subfolders:

- `data/`: download, preprocess, and validate datasets.
- `training/`: launch training stages.
- `evaluation/`: run benchmarks and ablations.
- `analysis/`: generate tables, figures, and failure breakdowns.

Rule:

- Scripts should call code from `src/` rather than containing core logic.

### `experiments/`

Run organization and lightweight experiment notes. This folder should separate fixed baseline runs from proposed-system trial runs, because the proposed architecture is expected to change while testing predictor and controller variants.

Recommended subfolders:

- `baselines/`: run manifests for established baselines such as AHN, BM25, dense retrieval, sliding window, full context, A-MAC-style allocation, and speaker-partitioned memory.
- `proposed/`: run manifests for trial versions of the proposed architecture.
- `ablations/`: runs where specific proposed components are removed or replaced.
- `sweeps/`: hyperparameter, memory-budget, and architecture-variant sweep definitions.
- `notes/`: short observations, debugging notes, and decisions.

Rule:

- Store only lightweight metadata here; large logs should go in `results/logs/`.
- Each run folder should include the exact config used, a short note on what was being tested, and a pointer to the result files.

Suggested proposed-run structure:

```text
experiments/proposed/
|-- predictor_mlp_pairwise/
|-- predictor_shallow_transformer/
|-- predictor_role_aware_attention/
|-- controller_budget_variants/
|-- retrieval_fidelity_variants/
`-- provenance_router_variants/
```

Suggested baseline-run structure:

```text
experiments/baselines/
|-- full_context/
|-- sliding_window/
|-- bm25/
|-- dense_retrieval/
|-- ahn/
|-- a_mac_global_utility/
|-- speaker_partitioned/
`-- collaborative_memory_style/
```

### `results/`

Generated outputs from experiments.

Recommended subfolders:

- `baselines/`: raw outputs from baseline runs.
- `proposed/`: raw outputs from proposed-system trial runs.
- `ablations/`: raw outputs from component-removal experiments.
- `comparisons/`: merged comparison files that directly compare baseline and proposed runs.
- `tables/`: CSV, Markdown, or LaTeX tables.
- `figures/`: Pareto plots and failure-mode charts.
- `logs/`: run logs and evaluation traces.
- `reports/`: generated summaries or paper-ready result drafts.

Rule:

- Keep result filenames tied to run IDs or config names.
- Keep baseline and proposed outputs separate until comparison scripts merge them.

### `references/`

Source material that supports the research.

Recommended subfolders:

- `papers/`: downloaded PDFs if licensing and storage allow.
- `citations/`: BibTeX, CSL JSON, or citation metadata.
- `notes/`: per-paper notes that are too detailed for `docs/PRIOR_WORK.md`.

## Naming Conventions

- Docs: uppercase topic files, such as `METHOD.md` and `BASELINE.md`.
- Configs: lowercase descriptive names, such as `qwen25_3b_groupmembench.yaml`.
- Runs: include date, short method name, and budget, such as `2026-08-24_full_system_25pct`.
- Baseline runs: prefix with `baseline_`, such as `baseline_ahn_25pct`.
- Proposed runs: prefix with the variant name, such as `predictor_mlp_pairwise_25pct`.
- Ablation runs: prefix with `ablation_`, such as `ablation_no_future_consumer_25pct`.
- Results: mirror the run or table name, such as `table1_groupmembench_accuracy_memory.csv`.
- Scripts: verb-first names, such as `run_evaluation.py` or `build_synthetic_data.py`.

## Build Order

Recommended order for growing the repo:

1. Keep refining `docs/` until the research plan is stable.
2. Add `configs/` for datasets, models, and evaluation budgets.
3. Add `data/README.md` and dataset download/preprocessing scripts.
4. Implement synthetic data generation in `src/datasets/`.
5. Implement memory units and memory accounting in `src/memory/`.
6. Implement future-consumer predictor and controllers in `src/controllers/`.
7. Implement retrieval and baselines.
8. Implement evaluation runners and metrics.
9. Generate `results/tables/` and `results/figures/`.
10. Compare baseline and proposed runs in `results/comparisons/`.
