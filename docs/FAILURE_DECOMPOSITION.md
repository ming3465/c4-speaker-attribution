# Failure-Mode Decomposition (Contribution 4)

Method specification for the unified failure analysis. Implemented in
`src/evaluation/failure_decomposition.py`; run with
`scripts/evaluation/run_failure_decomposition.py`; results in
`results/comparisons/failure_decomposition/`.

## Why the decomposition needs its own definition

The proposal claims three distinct failure modes. Answer accuracy alone cannot
separate them, and neither can retrieval recall: a system can retrieve the right
message and still have compressed the answer out of it. The decomposition is
therefore defined over the *stored* text, not the original message.

## Definitions

For question `q` with gold evidence units `E`, and a memory store `S` built
under a fixed word budget:

- `support(e) = |answer content tokens present in S[e]| / |answer content tokens|`,
  with date variants expanded so `2025-07-14` also matches `07-14`.
- `e` **survives** if `support(e) >= tau` (default 0.65).

Every question is assigned to exactly one bucket, in this order:

1. **Lost at write time** — no unit in `E` survives. The write policy dropped
   the unit or compressed the answer-bearing content out of it.
2. **Not retrieved** — at least one unit survives, but no surviving unit is in
   the retriever's top-k.
3. **Answer visible to the reader** — a surviving unit was retrieved. The
   answer is in front of the model.

The order matters: it makes the buckets mutually exclusive and the rows sum to
100%. A unit that is retrieved but no longer contains the answer counts as a
formation failure, not a retrieval success.

## Splitting the third bucket

Bucket 3 is the upper bound on accuracy, not accuracy itself. Splitting it into
`correct` and `retrieved but misinterpreted` requires running a reader model
over the retrieved context and grading the answer, then classifying the
residual errors:

- **Interpretation failure** proper: the answer depends on the provenance or
  role of the original speaker and the model resolved it wrongly. This is the
  only category that supports the Contribution 3 claim.
- Ordinary reading errors: arithmetic, multi-hop composition, hallucination.
  These must be excluded, otherwise "interpretation failure" absorbs every
  remaining error and the term stops meaning anything.

The reader step is not yet run — the Codex CLI in this workspace rejects every
model on the current account. The harness is otherwise complete; only the
grading call is missing.

## The eligibility gate

Some questions are not answerable from their own gold evidence even when that
evidence is stored uncompressed — the label is weak, or the answer must be
derived (most `temporal` questions). Grading those would score a labelling
problem as a memory failure.

The runner therefore first builds a full-fidelity store, and grades only the
questions that reach bucket 2 or 3 there. On GroupMemBench Finance this keeps
98 of 185; on LoCoMo, 944 of 1,977. Report both numbers: the gate is a real
limitation of the evidence labels, not a free filter.

## Budget matching

Every policy receives the same word budget, computed as a fraction of the
full-context word count of the group. Each unit first gets an equal shared
core; the remainder is spent as residual detail in policy order. Uniform
compression has no residual claim and spends its whole budget on equal cores.
The runner prints `stored_words` per configuration so budget matching can be
checked — this is what makes "at matched memory cost" a real claim rather than
a description.

Two implementation choices worth stating in the paper:

- **Compressor.** `salient` keeps the highest-IDF words in their original
  order, as a stand-in for what a summariser preserves. `prefix` truncation is
  available and is strictly worse; using it would overstate formation failure.
- **Memory unit granularity.** One message per unit by default. `--chunk-size`
  merges consecutive messages into thread-sized units. This materially changes
  the retrieval result and must be held constant across compared systems.

## Sanity checks the harness must pass

- At `--budgets 1.0` every policy produces identical numbers, because no
  compression happens. Verified.
- `lost_at_write` is 0% at full fidelity for every graded question, by
  construction of the eligibility gate. Verified.
- `stored_words` is equal across policies at each budget. Verified.

## Known limitations

- The formation test is lexical. A summary that preserves a fact in different
  words is scored as loss. This biases every system's `lost_at_write` upward,
  though it biases them equally.
- Retrieval is BM25 only. A dense retriever will move mass out of the
  `not_retrieved` column and the conclusions below should be re-checked.
- The oracle policy is built from all questions in the group, including the one
  being graded. It is an upper bound, not a system. See the leave-one-out note
  in `docs/DATASET_AUDIT.md`.
