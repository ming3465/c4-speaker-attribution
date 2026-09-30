# Failure-Mode Decomposition Runbook (Contribution 4)

Produces Table 3: every question attributed to memory-formation failure,
retrieval failure, or "answer visible to the reader", at matched memory budgets.

Method: `docs/FAILURE_DECOMPOSITION.md`. Data provenance: `docs/DATASET_AUDIT.md`.
Results: `results/comparisons/failure_decomposition/summary.md`.

## 1. Get the data

Pure standard library; no dependencies to install.

```bash
# GroupMemBench conversations (48 MB per domain)
python - <<'PY'
import urllib.request
B='https://huggingface.co/datasets/kimperyang/GroupMemBench/resolve/main/data/final/'
for d in ['Finance']:
    u=B+f'{d}/synthetic_domain_channels_rolevariants_{d}.json'
    open(f'data/raw/groupmembench/synthetic_domain_channels_rolevariants_{d}.json','wb').write(
        urllib.request.urlopen(u, timeout=600).read())
PY

# Official typed questions (code repo, not the HF dataset repo)
for d in Finance Technology Healthcare Manufacturing; do
  mkdir -p data/raw/groupmembench/questions/$d
  for t in multi_hop knowledge_update temporal term_ambiguity user_implicit abstention; do
    curl -sL -o data/raw/groupmembench/questions/$d/$t.jsonl \
      https://raw.githubusercontent.com/UCSB-NLP-Chang/GroupMemBench/main/questions/$d/$t.jsonl
  done
done

# Recovered gold evidence for the 214 Finance questions
mkdir -p data/raw/gmb_agent_sessions/finance
curl -sL -o data/raw/gmb_agent_sessions/finance/questions_enhanced.jsonl \
  https://huggingface.co/datasets/toddzheng024/groupmembench-agent-sessions/resolve/main/finance/questions_enhanced.jsonl

# LoCoMo (2.8 MB)
mkdir -p data/raw/locomo
curl -sL -o data/raw/locomo/locomo10.json \
  https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json
```

## 2. Check the structural statistics first

Decides what the run is allowed to claim: evidence density, evidence sharing,
and cross-consumer rate.

```bash
python scripts/data/evidence_statistics.py
```

## 3. Run the decomposition

```bash
python scripts/evaluation/run_failure_decomposition.py \
    --dataset groupmembench --domain Finance --budgets 0.1 0.25 0.5 0.75 1.0

python scripts/evaluation/run_failure_decomposition.py \
    --dataset locomo --budgets 0.1 0.25 0.5 0.75 1.0
```

Each run takes well under a minute and writes a per-question CSV plus a
per-category summary JSON to `results/proposed/failure_decomposition/`.

Sensitivity checks used in the results summary:

```bash
# retrieval depth
python scripts/evaluation/run_failure_decomposition.py --budgets 1.0 \
    --policies uniform_compression --top-k 50

# memory unit granularity
python scripts/evaluation/run_failure_decomposition.py --budgets 1.0 \
    --policies uniform_compression --chunk-size 16
```

## 4. Render Table 3

```bash
python scripts/evaluation/render_failure_tables.py \
    --summary results/proposed/failure_decomposition/summary_groupmembench_Finance.json \
    --budget 0.25 \
    --out results/comparisons/failure_decomposition/table3_groupmembench_Finance_budget0.25.md
```

## Sanity checks before trusting a run

- `--budgets 1.0` must give identical numbers for every policy.
- `stored_words` must be equal across policies at each budget.
- The eligible-question count must be reported alongside every table.

## Not yet implemented

- The reader pass that splits `answer visible` into `correct` and
  `retrieved but misinterpreted`. The Codex CLI on this machine rejects every
  model (`invalid_request_error: model not supported with a ChatGPT account`),
  so an OpenRouter or local-model backend is needed.
- A leave-one-out oracle. See `docs/DATASET_AUDIT.md` for why this matters.
- Dense retrieval, and the AHN row of Table 3.
