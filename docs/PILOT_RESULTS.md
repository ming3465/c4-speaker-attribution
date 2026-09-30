# Pilot Results — C1, C2, C3, C4

Status as of 2026-09-23. The project is moving from pilot to a real
role-agnostic study: AMI and ELITR are being preprocessed (no suitable
multi-party dataset exists off the shelf), with silver labels from a LangChain
workflow plus manual verification. The AHN extension now trains — backprop
through the AHN kernel is fixed and running on GPU, with Xavier init for
cross-seed stability.

Every number below is a **pilot** number: small samples, one domain, and in
several cases a single seed. Treat all of them as directional.

---

## C1 — future-consumer prediction

| Metric | Value |
| --- | --- |
| Hit@1 | 0.9969 |
| MRR | 0.9984 |
| Hit@1 gain from provenance | +0.7443 |
| MRR gain from provenance | +0.4760 |

With provenance the controller recovers the target almost perfectly; the gain
implies roughly 0.25 Hit@1 without it. The provenance contribution is large and
controlled.

**Must be audited before it is published.** 0.9969 on a *future* prediction
task is extraordinary — a lexical predictor on comparable GroupMemBench data
scored 0.126 against a 0.083 floor. Five checks, about an hour:

1. Channel-only baseline — train on channel ID alone.
2. Group-wise train/test split — no channel or conversation in both splits.
3. Label-in-text scan — does the input text contain the target role string?
4. Shuffled-label control — must collapse to chance.
5. Majority-class baseline — report beside random.

If it survives all five it is a genuinely strong result and should be stated
with confidence.

## C2 — internal representation → AHN write adapter

| Metric | Value |
| --- | --- |
| Effect vs uniform | −0.0009 ± 0.0060 |

**This is a null result.** The point estimate is negative and about 0.15 SD
from zero; a 95% interval is roughly [−0.013, +0.011]. The accurate statement:

> Conditioning the AHN write adapter on the pre-final internal representation
> produced no measurable effect (−0.0009 ± 0.0060, indistinguishable from
> uniform).

A null is still worth reporting — it rules out a plausible mechanism cheaply.
If an effect is expected and the pilot was underpowered, say so and state the
sample size that would detect it.

## C3 — source-sensitive interpretation

| Split | Accuracy ranking |
| --- | --- |
| Validation | 0.6043 |
| Test | 0.5087 |

Open before write-up:

1. **Chance baseline.** If this is a binary ranking, chance is 0.5 and the test
   result is at chance.
2. **~10-point validation → test drop**, the shape of overfitting to the
   validation split. Check whether model selection used that split.

## C4 — compression-induced attribution failure

**Question.** After a memory is compressed, can a reader still tell *who*
said a statement in a multi-party conversation — and does the damage grow with
compression? (Re-scoped from the original failure decomposition, which WhenLoss
published first.)

**Result: a floor effect.** At full fidelity the reader (`qwen2.5:7b`) could
not be told apart from chance (+3.4 pts, 95% CI [−0.8, +7.4]; lifts above 7.4
pts are excluded), so there was no measurable attribution for compression to
destroy. The dose-response is flat because it starts at the
floor, not because compression is harmless. This is a clean, controlled
negative result, and it says the pilot's *data*, not only its reader, needs to
change before C4 can be measured.

### v2 — frozen probes (result of record)

542 probes from 161 questions, each fixed once from budget-1.0 retrieval and
re-rendered at every budget with only its text compressed (target: 65 → 44 →
30 → 15 → 6 words). Roster = the 2–4 speakers visible in the conversation, so
chance = 1/|roster| (mean 38.3%). Temperature 0, constrained decoding (answer
must be a roster name), deterministic under any hash seed. 3,682 graded rows,
0 errors, 0 invalid answers. Cluster bootstrap by question; exact McNemar.

| Budget | Hit@1 [95% CI] | Chance | Frequency heuristic | Lift over chance [95% CI] |
| ---: | --- | ---: | ---: | --- |
| 1.0 | 41.7% [37.1, 46.1] | 38.3% | 42.6% | +3.4 [−0.8, +7.4] |
| 0.5 | 41.7% [37.0, 46.2] | 38.3% | 42.6% | +3.4 [−0.7, +7.3] |
| 0.25 | 41.0% [36.2, 45.4] | 38.3% | 42.6% | +2.6 [−1.6, +6.7] |
| 0.1 | 39.7% [35.2, 44.1] | 38.3% | 42.6% | +1.4 [−2.7, +5.5] |

- **Paired dose-response**, 1.0 → 0.1 on the same 542 probes: −2.0 pts
  [−6.3, +2.0], 85 lost / 74 gained, McNemar p = 0.43.
- **Label-swap counterfactual** (A ↔ B labels swapped with equal counts, so
  presence and frequency heuristics are indifferent): the reader follows the
  swap 31–34% of the time — at chance (34.5%). Binding index −2.8 / 0.0 / −9.0
  pts at 1.0 / 0.25 / 0.1. No binding at any budget.
- **"Genuinely bound" probes** (correct and follows the swap at 1.0): 44,
  against 41 expected by chance. Their decay under compression is regression
  to chance, not evidence of binding loss.
- **By speaker count**: 2-speaker rosters sit slightly above chance (56% vs 50%
  at 1.0, 52% at 0.1); 3- and 4-speaker rosters are at chance throughout.
- **What the pilot can rule out** (Table 5 of the rendered tables): it could
  detect effects of about 5–6 pts at 80% power. The lift over chance and the
  1.0 → 0.1 change are *inconclusive* at a ±5 pt margin, not "no effect". The
  0.75 / 0.5 / 0.25 changes fall inside ±5 pts, but that margin was set after
  the pilot, so treat those as exploratory.

### Why the floor — the probes carry little speaker signal

A plain lexical attributor (TF-IDF similarity between the statement and each
speaker's visible messages) scores 45.8% against 38.3% chance on the same
uncompressed probes — only +7.5 pts, and it *beats* the LLM reader. A speaker's
own messages are barely more similar to their statement than anyone else's
(cosine gap +0.04). Two causes:

1. **Retrieval builds topically uniform contexts.** All snippets are retrieved
   for the same question, so every speaker in the set is on the same topic.
2. **GroupMemBench is synthetic.** One model generated every participant, so
   there is little individual voice to bind on.

The compressor also matters: salient word-dropping keeps high-IDF topic words,
exactly what lexical binding uses, so it is nearly harmless here (lexical
attributor 45.8% → 43.4% from 1.0 to 0.1).

### v1 — superseded, kept for the record

v1 re-drew the target and context at every budget, so budgets compared
different statements (only 6/98 targets matched between 1.0 and 0.1) — not a
dose-response. An adversarial audit (6 lenses, 38 findings) confirmed this 3/3,
and also found a grader bug: substring matching credited `User_10/12/13` as
`User_1`, which manufactured v1's only rise (the 0.5 bump). Strictly
re-graded, v1 reads 24.5 / 24.5 / 23.5 / 23.5 / 15.3%. v1's apparent
above-chance accuracy was the presence heuristic: its roster included
invisible distractors, and "pick someone visible" scored 42%.

### Reader behaviour worth noting

Without constrained decoding, the reader sometimes *invented a new
participant* — answering `User_4` for a roster of `User_1–User_3`, a name that
appears nowhere in the prompt. It treats the hidden speaker as someone not
present: the opposite of binding. This was 13% of unconstrained rows but
concentrated in 3 probes, so treat it as an observed failure mode, not a rate.

### What would make C4 measurable

Items 1–5 are now implemented (2026-09-27). The AMI study is registered in
[`C4_ANALYSIS_PLAN.md`](C4_ANALYSIS_PLAN.md) and adds two safeguards learned on
AMI: a turn-taking heuristic (label-only, about 7 pts above chance on meeting
windows) that the gate must beat significantly, and per-message compression so
long statements are not cut below the nominal budget.

1. **Real multi-party data — AMI / ELITR.** Real speakers have idiolects,
   roles and reply threads. The v2 probe needs only (utterance, speaker) pairs,
   so it ports with no annotation.
2. **Gate on headroom.** Run a stronger reader on uncompressed probes first; no
   compression sweep until the ceiling is clearly above chance.
3. **Summarization as a compressor**, not only word-dropping. Summaries rewrite
   voice and merge speakers, which is the realistic threat to attribution.
4. **Bigger groups** (top-10 or conversation windows), so "damage scales with
   group size" becomes testable — rosters of 2–4 cannot test it.
5. **Conversation windows instead of question retrieval**, for natural
   back-and-forth rather than five same-topic snippets.
6. **After the GPU:** the AHN version — push early speaker turns out of the
   sliding window into AHN's compressed memory and ask who said what.

### Files

| Path | Contents |
| --- | --- |
| `docs/C4_RUNBOOK.md` | **start here** — data contract, commands, headroom gate, pilot reproduction, code status |
| `src/evaluation/attribution_frozen.py` | v2 probe design, grading, deterministic constrained reader |
| `scripts/evaluation/run_attribution_frozen.py` | v2 runner (append-per-row, resumable) |
| `scripts/evaluation/analyze_attribution_frozen.py` | v2 tables: cluster bootstrap, paired McNemar, swap index |
| `results/comparisons/attribution_v2/attribution_v2_tables.md` | v2 tables |
| `results/proposed/attribution_v2/` | v2 per-row CSV |
| `src/evaluation/attribution_probe.py`, `scripts/evaluation/run_attribution_probe.py`, `analyze_attribution.py` | v1 (superseded; grader fixed) |

---

## How to produce benchmarks: follow WhenLoss's method, not its task

WhenLoss (arXiv 2605.24579) is worth copying for **methodology** and not for
**task**. Its benchmark (LongMemEval) is single-user, so it cannot express
either of the things this project measures — who will need a memory, or who
said it. But its experimental discipline is exactly what reviewers will expect:

| WhenLoss practice | Apply it here as |
| --- | --- |
| One fixed reader across all conditions | Fix the reader per table; never compare cells across readers |
| Controlled input conditions (TFC / OE / CSM / RM) | See the AHN mapping below |
| Gaps as differences between conditions | Report deltas, not raw scores |
| Pre-declared diagnosis margin (ε = 0.02) | Declare the margin before running, not after |
| Three readers, 500 questions | Multiple seeds (instability already observed) and ≥2 readers where possible |
| Budget sweep | Sweep memory budget / window size, not a single point |

**The AHN mapping.** WhenLoss's conditions port directly to AHN's layer:

| WhenLoss condition | AHN analogue | What it isolates |
| --- | --- | --- |
| OE (oracle evidence) | Full attention | Lossless reference |
| — | Sinks + SWA only | Window with *no* compressed memory |
| CSM (stored memory) | AHN | Window + compressed memory |
| — | AHN + this project's extension | The proposed method |

Two gaps then fall out, mirroring Δ_write and Δ_retr:

```
Δ_mem  = φ(AHN)  − φ(SWA)     what the compressed memory contributes
Δ_loss = φ(Full) − φ(AHN)     what compression still costs
```

AHN's own Table 5 (RULER-128k needle-in-a-haystack, Qwen2.5-7B) already gives
Δ_mem ≈ −0.02 — on exact recall the compressed memory contributes nothing over
the window alone — while Δ_mem is +1.20 on LV-Eval and +3.77 on InfiniteBench.
That spread is the baseline the extension should be measured against.

**Benchmarks to report on**

- *For comparability*: the ones AHN reports — LV-Eval, InfiniteBench,
  RULER-128k NIAH. Reviewers will look for these first.
- *For novelty*: the multi-party set being built from AMI / ELITR. This is the
  only place the consumer and provenance claims can be tested, and it is the
  part no prior paper covers.

**Reporting rules**

- Bootstrap or seed-based CIs on every number.
- Both a random floor and a majority baseline.
- Hold the reader fixed within any comparison; the same pipeline has shown a
  4-point swing from changing the reader alone.
- Declare the decision margin before the run.
