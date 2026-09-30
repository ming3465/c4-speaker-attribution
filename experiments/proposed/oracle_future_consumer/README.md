# Oracle Future-Consumer Experiment

This is the first Phase 0 experiment. It checks whether future-consumer information is useful before training a predictor.

## Step 1: Inspect GroupMemBench Schema

If the Finance domain JSON is already local:

```bash
python scripts/data/inspect_groupmembench_schema.py \
  --domain Finance \
  --input data/raw/groupmembench/synthetic_domain_channels_rolevariants_Finance.json
```

If it is not local yet, download it from Hugging Face:

```bash
python scripts/data/inspect_groupmembench_schema.py \
  --domain Finance \
  --download
```

Expected outputs:

```text
data/processed/groupmembench/schema_summary.json
data/processed/groupmembench/message_sample.json
```

## Step 2: Build Oracle Labels

Create:

```text
data/processed/groupmembench/oracle_labels.jsonl
```

Use the schema in:

```text
docs/ORACLE_LABEL_SCHEMA.md
```

For the first pass, a small hand-labeled sample is enough. The goal is not scale yet. The goal is to confirm that evidence messages can be connected to later askers.

If typed question sets are unavailable, create a manual labeling template from decision-change messages:

```bash
python scripts/data/create_oracle_label_template.py \
  --domain Finance \
  --mode decision_changes \
  --limit 25
```

Expected output:

```text
data/processed/groupmembench/oracle_label_template.jsonl
```

Then manually convert completed rows into:

```text
data/processed/groupmembench/oracle_labels.jsonl
```

## Step 3: Validate Oracle Labels

```bash
python scripts/data/validate_oracle_labels.py \
  --input data/processed/groupmembench/oracle_labels.jsonl
```

Expected output:

```text
results/comparisons/phase_0_oracle_validation/oracle_label_validation.json
```

## Step 4: Run Memory Allocation Comparison

Run the deterministic formation proxy comparison:

```bash
python scripts/evaluation/run_phase0_proxy_comparison.py
```

It compares:

- Uniform compression.
- Speaker-partitioned memory.
- Oracle future-consumer allocation.

The config is:

```text
configs/experiments/phase0_oracle_validation.json
```

Expected outputs:

```text
results/comparisons/phase_0_oracle_validation/proxy_summary.json
results/comparisons/phase_0_oracle_validation/proxy_rows.csv
results/comparisons/phase_0_oracle_validation/summary.md
```

Run the retrieval-aware proxy comparison:

```bash
python scripts/evaluation/run_phase0_retrieval_proxy.py --top-k 5
```

Expected outputs:

```text
results/comparisons/phase_0_oracle_validation/retrieval_proxy_summary.json
results/comparisons/phase_0_oracle_validation/retrieval_proxy_rows.csv
```

## Current Status

- Schema inspection script exists.
- Oracle label schema exists.
- Oracle label validator exists.
- Oracle label template generator exists.
- Bootstrap oracle-label generator exists.
- Proxy memory allocation comparison runner exists.
- Retrieval-aware proxy comparison runner exists.
- First 40-label proxy comparisons have been run.
