# LLM Pilot

This pilot uses an actual LLM answer-generation loop instead of lexical proxy scoring.

## What It Tests

The pilot tests Contribution 1:

```text
future-consumer-aware memory allocation
```

It asks whether retrieved visible memories under each allocation strategy let an LLM answer the current updated decision question.

## What It Does Not Test

- It does not test the full trained future-consumer predictor.
- It does not test provenance-conditioned interpretation.
- It does not use official GroupMemBench typed question rows.
- It does not prove final benchmark performance.

## Current LLM Runner

The local pilot uses Codex CLI as the answer model:

```text
model: gpt-5.6-sol
```

Each strategy gets a separate LLM call so the model cannot see another strategy's retrieved context.

## Run Command

```bash
python scripts/evaluation/run_phase0_llm_pilot.py \
  --sample-size 4 \
  --top-k 5
```

Outputs:

```text
results/comparisons/phase_0_oracle_validation/llm_pilot/predictions.jsonl
results/comparisons/phase_0_oracle_validation/llm_pilot/predictions.csv
results/comparisons/phase_0_oracle_validation/llm_pilot/summary.json
results/comparisons/phase_0_oracle_validation/llm_pilot/judge_raw.txt
results/comparisons/phase_0_oracle_validation/llm_pilot/report.md
```

## Scoring

The model first answers from retrieved snippets only.

Then an LLM judge compares the model answer to the gold updated decision and marks whether the answer is semantically correct.

Correct means:

- The answer captures the same current updated decision as the gold answer.

Incorrect means:

- The answer is missing.
- The answer contradicts the gold answer.
- The answer only states old or outdated information.

## Current Result

A 4-label stratified pilot has been run across Finance, Healthcare, Manufacturing, and Technology.

| Strategy | LLM accuracy | Gold evidence retrieval rate |
| --- | ---: | ---: |
| Uniform compression | 0.25 | 0.75 |
| Speaker-partitioned memory | 0.25 | 0.75 |
| A-MAC-style metadata utility | 1.00 | 1.00 |
| Query/task-conditioned compression | 1.00 | 1.00 |
| Recency window | 1.00 | 1.00 |
| Oracle future-consumer allocation | 1.00 | 1.00 |

Interpretation:

- Future-consumer allocation works on this small pilot.
- Metadata, task-conditioned, and recency baselines also work because the sample is decision-change-only.
- The next fair LLM pilot needs non-decision cases such as speaker-grounded, term-ambiguity, and cross-speaker multi-hop questions.
