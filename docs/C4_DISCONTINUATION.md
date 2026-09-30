# C4 Discontinued: Decision Record

**Date:** 2026-09-04
**Decision:** Stop Contribution 4 (failure-mode decomposition) as a paper contribution.
**Status of the work:** Complete and correct. Superseded by prior publication.

---

## 1. What failed

**Contribution 4 — unified failure-mode decomposition.** The instrument that
attributes every wrong answer to one of:

- `lost_at_write` — evidence destroyed during compression
- `not_retrieved` — evidence survived but retrieval missed it
- `answer_visible` — evidence survived and was retrieved
  - split by the reader pass into `correct` / `retrieved_but_misinterpreted`

It was built, it ran, and it produced a complete Table 3 across five policies
and five budgets. The work is not wrong. It is not new.

## 2. Why it failed

**WhenLoss: Diagnosing Write and Retrieval Bottlenecks in Long-Context Memory
Systems** — Jiangnan Yu, Kisson Songqi Lin, Jilong Wu. arXiv:2605.24579,
submitted 23 May 2026. Local copy: `~/Downloads/WhenLoss_2605.24579.pdf`
(9 pages, read in full).

Their four-condition protocol evaluates one fixed reader under truncated full
context (TFC), oracle evidence (OE), complete stored memory (CSM), and
retrieved memory (RM), then defines:

```
Δ_write = φ(OE)  − φ(CSM)     evidence lost during compression
Δ_retr  = φ(CSM) − φ(RM)      evidence stored but not retrieved
```

That is our decomposition, with our oracle reference, under our fixed-budget
setup. Their diagnosis rule (margin ε = 0.02, labels WRITE / RETRIEVAL / MIXED)
is the formal version of what our table reports informally.

**They also reproduce our headline finding.** From the abstract: *"write-side
gaps exceed retrieval-side gaps for most tested baselines, with four of six
baselines robustly write-dominant."* Our pilot found 60–67% lost-at-write
against 19–28% not-retrieved — the same asymmetry, at smaller scale.

**Scale comparison, ours vs theirs:**

| | Ours | WhenLoss |
| --- | --- | --- |
| Questions | 98 | 500 (+ LoCoMo replication) |
| Readers | 1 (local qwen2.5:7b, quantized) | 3 (GPT-5.2, Claude Sonnet 4, Gemini 2.5 Pro) |
| Memory systems | 5 policies | 7 systems |
| Extras | — | budget sweep, cost-matched comparison, ablations |

**C1 is hit by the same paper.** Their proposed method, Expected Predictive
Compression (EPC), *"moves the key decision — what information to retain — to
write time by using an LLM to anticipate likely future questions and preserve
the minimal supporting evidence under the token budget."* That is
predicted-need-aware allocation. C1 is now "EPC, but predicting *who* rather
than *what*" — a narrower claim than we had, and it must now be benchmarked
against EPC.

**Adjacent prior work found in the same search:**

- WritePolicyBench (arXiv:2602.02574, Jan 2026) — benchmarks memory write
  policies under byte budgets.
- Diagnosing Retrieval vs. Utilization Bottlenecks (arXiv:2603.02473, Mar 2026)
  — retrieval / utilization / hallucination split on LoCoMo. Explicitly does
  *not* measure write-time loss.
- EverMemBench (arXiv:2602.01313) — multi-party, role-conditioned personas, org
  hierarchy. Does *not* do future-need prediction.

**Neither ByteDance paper is the cause.** AHN (arXiv:2510.07318) reports
benchmark accuracy and efficiency; its only analysis is a token-level gradient
probe (§3.5). AgentViSS (arXiv:2606.15152) is multimodal social simulation and
is orthogonal. The collision came entirely from the memory-diagnostics
literature.

## 3. What survives from C4

Two things, and they are worth keeping.

**A finer split than theirs.** WhenLoss separates failures two ways. We
separate three, with `retrieved_but_misinterpreted` as its own bucket. They
concede their write-side gap is contaminated by exactly that: *"it can also
reflect format mismatch between stored memory and reader expectations, or loss
of contextual cues."* Our reader pass isolates it. On its own this is a
refinement of a published protocol — a workshop note, not a contribution.

**An unexpected result.** Misinterpretation rate tracked compression severity:

| Policy | Misread, as a share of evidence that reached the reader |
| --- | ---: |
| uniform_compression | 75.0% |
| amac_global_utility | 72.7% |
| speaker_partitioned_memory | 50.0% |
| recency_window | 38.5% |
| oracle_future_consumer | 34.5% |

WhenLoss treats survival as binary. This suggests a middle state — evidence
present but too degraded to use. Currently rests on n = 11–13 per policy, so it
is a hypothesis, not a result.

## 4. The replacement

**Test A — provenance sensitivity at read time.**

Every benchmark in the scooping literature is single-user: LongMemEval and
LoCoMo are one person talking to an assistant. In that setting "who said it"
and "who is asking" carry no information, so the question cannot be posed.
Ours is multi-party. That is the one gap the prior work structurally cannot
occupy.

**Design.** Identical questions, identical evidence, identical reader. Only the
identity information changes:

| Condition | Speaker + role in snippets | Asker shown |
| --- | --- | --- |
| `baseline` | shown | true asker |
| `no_speaker` | stripped | true asker |
| `wrong_asker` | shown | a different *real* participant |
| `neither` | stripped | removed |

`wrong_asker` names a real other participant from the same conversation rather
than random noise, so the prompt stays plausible and only the identity is wrong.

**Verified before running:** all four prompts are distinct, and the evidence
text is byte-identical across conditions. Any score difference is attributable
to identity information alone.

**How to read it.**

- Scores flat → identity is decorative. C2 and C3 lose their foundation, and we
  learn this on a laptop rather than after weeks of A100 time.
- Scores drop → provenance is load-bearing, and that is the opening claim of the
  paper — the thing WhenLoss cannot test.

Both outcomes are useful. That is the reason to run it.

## 5. Status and time

| Item | State |
| --- | --- |
| Ablation knobs in `src/evaluation/reader_pass.py` | **Done**, parses, verified |
| `scripts/evaluation/run_provenance_ablation.py` | **Done**, smoke-tested |
| Prompt manipulation correctness | **Verified** |
| Table with numbers | **Not done** — run stopped at ~10% |

The skeleton is finished. The numbers are not. The full run is 4 conditions ×
55 questions = **220 model calls**, roughly 60–90 minutes of uninterrupted local
inference. It needs to be restarted and left alone.

```bash
ollama serve                      # separate terminal
python3 scripts/evaluation/run_provenance_ablation.py --model qwen2.5:7b
```

Add `--limit 15` for a ~20-minute directional read on 60 calls instead of 220.

## 6. A caution on framing

This test is not built to confirm the hypothesis. It is built to decide it.
A flat result is a real possible outcome, and it would mean C2 and C3 need a
different justification. Anyone presenting this should not describe it in
advance as confirmation.

Sample size is the binding limit: n = 55 per condition. The script prints its
own noise floor — a swing under roughly 4 points is meaningless here. Treat any
result as directional, and re-run on the full 30,000-message corpus before it
goes in a paper.
