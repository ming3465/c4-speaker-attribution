# Failure-Mode Decomposition: Results

Run on 2026-08-31. Reproduce with
`experiments/proposed/failure_decomposition/README.md`. Method and caveats:
`docs/FAILURE_DECOMPOSITION.md`. Dataset provenance: `docs/DATASET_AUDIT.md`.

Setup: BM25 top-5 over every message in the domain, `tau=0.65`, one message per
memory unit, `salient` compressor, budgets matched to the stated fraction of
full-context words. Columns are percentages of graded questions and sum to 100.

## GroupMemBench / Finance (98 graded of 185 evidence-linked)

| Budget | System | Lost at write | Not retrieved | Answer visible |
| ---: | --- | ---: | ---: | ---: |
| 10% | uniform compression | 77.6 | 20.4 | 2.0 |
| 10% | recency window | 85.7 | 12.2 | 2.0 |
| 10% | speaker-partitioned memory | 86.7 | 12.2 | 1.0 |
| 10% | A-MAC-style global utility | 82.7 | 15.3 | 2.0 |
| 10% | oracle future consumer | 0.0 | 82.7 | 17.3 |
| 25% | uniform compression | 60.2 | 33.7 | 6.1 |
| 25% | recency window | 65.3 | 26.5 | 8.2 |
| 25% | speaker-partitioned memory | 64.3 | 26.5 | 9.2 |
| 25% | A-MAC-style global utility | 60.2 | 33.7 | 6.1 |
| 25% | oracle future consumer | 0.0 | 68.4 | 31.6 |
| 50% | uniform compression | 40.8 | 43.9 | 15.3 |
| 50% | recency window | 43.9 | 42.9 | 13.3 |
| 50% | speaker-partitioned memory | 44.9 | 40.8 | 14.3 |
| 50% | A-MAC-style global utility | 38.8 | 50.0 | 11.2 |
| 50% | oracle future consumer | 0.0 | 66.3 | 33.7 |
| 75% | uniform compression | 20.4 | 54.1 | 25.5 |
| 75% | recency window | 19.4 | 61.2 | 19.4 |
| 75% | speaker-partitioned memory | 19.4 | 62.2 | 18.4 |
| 75% | A-MAC-style global utility | 12.2 | 68.4 | 19.4 |
| 75% | oracle future consumer | 0.0 | 69.4 | 30.6 |
| 100% | all policies (identical) | 0.0 | 70.4 | 29.6 |

## LoCoMo (944 graded of 1,977 evidence-linked)

LoCoMo has no asker id, so `oracle future consumer` degenerates to an oracle
*global* utility policy there. Included as a scale check on the decomposition,
not as a test of the consumer hypothesis.

| Budget | System | Lost at write | Not retrieved | Answer visible |
| ---: | --- | ---: | ---: | ---: |
| 10% | uniform compression | 82.5 | 16.2 | 1.3 |
| 10% | recency window | 90.0 | 9.3 | 0.6 |
| 10% | speaker-partitioned memory | 90.3 | 9.1 | 0.6 |
| 10% | A-MAC-style global utility | 87.7 | 10.8 | 1.5 |
| 10% | oracle | 74.7 | 21.5 | 3.8 |
| 25% | uniform compression | 57.3 | 33.6 | 9.1 |
| 25% | recency window | 67.6 | 28.9 | 3.5 |
| 25% | speaker-partitioned memory | 67.6 | 28.9 | 3.5 |
| 25% | A-MAC-style global utility | 66.6 | 29.4 | 3.9 |
| 25% | oracle | 39.5 | 52.4 | 8.1 |
| 50% | uniform compression | 24.2 | 51.7 | 24.2 |
| 50% | oracle | 3.9 | 69.3 | 26.8 |
| 75% | uniform compression | 10.5 | 56.4 | 33.2 |
| 75% | oracle | 0.0 | 65.9 | 34.1 |
| 100% | all policies (identical) | 0.0 | 62.2 | 37.8 |

## Findings

### 1. Retrieval, not compression, is the binding constraint

With the full conversation stored uncompressed, BM25 top-5 still fails to
surface the gold evidence for **70.4%** of Finance questions and 62.2% of LoCoMo
questions. Every compression policy is competing over the ~30% of questions that
retrieval can reach at all.

This is not an artifact of retrieval depth or memory-unit size. At full fidelity
on Finance:

| Retrieval depth (1 message per unit) | Not retrieved |
| --- | ---: |
| top-5 | 70.4% |
| top-10 | 57.1% |
| top-20 | 46.9% |
| top-50 | 35.7% |

| Memory unit size (top-5) | Units | Not retrieved |
| --- | ---: | ---: |
| 1 message | 30,000 | 70.4% |
| 4 messages | 7,503 | 63.1% |
| 16 messages | 1,877 | 52.7% |

Even with thread-sized memories, or ten times the retrieval depth, more than a
third of questions never see their evidence.

### 2. Formation and retrieval failures trade off against each other

As the budget rises, `lost at write` falls and `not retrieved` rises — for every
policy, on both datasets. Shorter stored text is easier for BM25 to match
against a short question; longer text preserves the answer but competes worse
under length normalisation. Reporting either column alone makes a system look
better or worse than it is, which is the argument for the decomposition.

The oracle is the clearest case. It eliminates formation failure (0.0% at every
budget on Finance) and yet at 75% budget has the *worst* retrieval column
(69.4%), finishing only 5.1 points above uniform compression on answer
visibility. **Perfect write-time allocation does not survive the read stage.**

### 3. The oracle's advantage on GroupMemBench is nearly free, and mostly memorisation

Only 0.96% of the Finance corpus is ever asked about, so protecting every gold
evidence message costs almost nothing at any budget. And only 5.6% of evidence
units are wanted by more than one question, so roughly 94% of the oracle's
advantage is per-question memorisation rather than learnable structure.

On LoCoMo, where 24.2% of the corpus is cited, the oracle cannot protect
everything and its formation column is non-zero at low budgets (74.7% at 10%).
The contrast shows the GroupMemBench oracle result is a property of evidence
sparsity, not of the idea being tested.

**A leave-one-out oracle is needed before the Phase-0 gate can be read as
support for future-consumer prediction.**

### 4. Per-category patterns at 25% budget (Finance)

| Category | n | Uniform: lost at write | Oracle: lost at write | Oracle: answer visible |
| --- | ---: | ---: | ---: | ---: |
| knowledge_update | 21 | 100.0 | 0.0 | 9.5 |
| user_implicit | 13 | 100.0 | 0.0 | 61.5 |
| term_ambiguity | 21 | 47.6 | 0.0 | 19.0 |
| multi_hop | 37 | 40.5 | 0.0 | 45.9 |
| temporal | 6 | 0.0 | 0.0 | 0.0 |

- `knowledge_update` is the most formation-fragile category: uniform compression
  loses **100%** of it at write time. Superseded facts are exactly what a
  budget-constrained store drops. This is the strongest category-level support
  for the proposal's write-time claim.
- But `knowledge_update` is also where the oracle converts that gain least
  (9.5% visible), because its evidence is then lost at retrieval.
- `user_implicit` is where the oracle helps most (61.5% visible) — and it is the
  category with the *lowest* cross-consumer rate (30%). The oracle's biggest win
  is therefore on questions people ask about their own messages, which is
  evidence *against* the cross-consumer reading of the result.
- `temporal` (n=6) is too small to support any claim.

### 5. The cross-consumer premise itself holds

In 87.6% of (question, evidence) pairs the asker did not write the evidence, so
a future-consumer signal genuinely exists to be predicted. This is the one
structural assumption of the proposal that these runs confirm rather than
complicate.

## What these numbers do not show

- No reader model was run, so `answer visible` is an upper bound on accuracy and
  the interpretation failure mode is unmeasured.
- Only BM25 was tested. A dense retriever could change finding 1 substantially.
- Only GroupMemBench Finance has both an asker and gold evidence, so n=98 for
  every multi-party claim, and 13-37 per category.
- The oracle row is an upper bound built with knowledge of the graded question.
- The formation test is lexical; a summary that preserves a fact in different
  words is scored as loss.
