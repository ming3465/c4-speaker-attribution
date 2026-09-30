# Dataset Audit

Verified by download and schema inspection on 2026-08-31. `DATASET.md` records
what the proposal *says* about each dataset; this file records what each dataset
*actually contains*, and which claims it can support.

## What the failure decomposition needs

Contribution 4 separates memory-formation, retrieval, and interpretation
failures. To attribute a wrong answer to a stage, a dataset must provide:

1. **Gold evidence pointers** — which message(s) contain the answer. Without
   these, "lost at write" and "not retrieved" are indistinguishable.
2. **Question categories** — so the decomposition can be reported per type.
3. **Speaker attribution** on every unit — for provenance and the interpretation
   stage.
4. **A named asker** (multi-party only) — required for any *future-consumer*
   claim, because the signal to be predicted is "who will ask", not "will
   anyone ask".

## GroupMemBench

The proposal's primary benchmark is split across three repositories. The
earlier note in `configs/datasets/groupmembench_finance.json` that the
companion repo was unavailable was based on the wrong organisation name
(`KimperYang/GroupMemBench` 404s; the code repo is `UCSB-NLP-Chang`).

| Part | Location | Contents |
| --- | --- | --- |
| Conversations | HF `kimperyang/GroupMemBench` | 4 domains. Finance: 30,000 messages, 6 channels, 12 users, 7 roles, 48.8 MB. |
| Typed questions | GitHub `UCSB-NLP-Chang/GroupMemBench`, `questions/<Domain>/<type>.jsonl` | **745 questions**, 4 domains x 6 types. |
| Recovered evidence | HF `toddzheng024/groupmembench-agent-sessions`, `finance/questions_enhanced.jsonl` | Finance only: the same 214 questions plus `evidence_msg_ids`. |

Official question schema is `{id, question, answer, asking_user_id}` — there
are **no evidence pointers in the official release**. Question counts:

| Type | Finance | Technology | Healthcare | Manufacturing |
| --- | ---: | ---: | ---: | ---: |
| multi_hop | 48 | 41 | 48 | 45 |
| knowledge_update | 32 | 36 | 17 | 22 |
| temporal | 45 | 37 | 37 | 43 |
| term_ambiguity | 45 | 43 | 7 | 11 |
| user_implicit | 15 | 28 | 2 | 4 |
| abstention | 29 | 28 | 34 | 48 |

Finance and Technology are solvability-filtered; Healthcare and Manufacturing
are the raw generated set.

### Quality of the recovered evidence

Checked against the real Finance messages by `scripts/data/evidence_statistics.py`
and the validation in this audit:

- The 214 rows match the official Finance questions exactly (question, answer,
  and `asking_user_id` all 214/214).
- 185 rows carry evidence; all 185 resolve to real `msg_node` ids; the 29 rows
  without evidence are all `abstention`, which is correct.
- Author-declared confidence: 163 high, 22 low, 29 none.
- Mean best gold-answer token coverage inside the cited evidence is 0.530, and
  98/185 reach the 0.65 threshold used by the decomposition:

  | Category | n | Mean best coverage | Reaching 0.65 |
  | --- | ---: | ---: | ---: |
  | user_implicit | 15 | 0.838 | 13 |
  | multi_hop | 48 | 0.698 | 37 |
  | knowledge_update | 32 | 0.694 | 21 |
  | term_ambiguity | 45 | 0.461 | 21 |
  | temporal | 45 | 0.200 | 6 |

  `temporal` is far the weakest because those answers are dates that must be
  derived rather than quoted — only 9/45 temporal answers appear verbatim in an
  evidence timestamp. Treat `temporal` as unusable for lexically graded
  formation analysis.

**Consequence:** the evidence labels are third-party and imperfect, so the
decomposition grades only questions whose answer is recoverable from the gold
evidence at full fidelity. Otherwise a weak label is scored as a memory failure.

### Structural statistics that constrain what can be claimed

| Statistic | GroupMemBench / Finance | LoCoMo |
| --- | ---: | ---: |
| Corpus units | 30,000 | 5,882 |
| Distinct evidence units | 288 | 1,425 |
| Evidence density (share of corpus ever asked about) | **0.96%** | 24.2% |
| Evidence units cited by more than one question | **5.6%** | 52.6% |
| (question, evidence) pairs where asker != author | **87.6%** | not measurable |

Three consequences:

- **The cross-consumer premise holds.** In 87.6% of pairs the asker did not
  write the evidence, so there is a genuine consumer-vs-producer distinction to
  predict. It is strongest for `term_ambiguity` (98%) and weakest for
  `user_implicit` (30%, where people mostly ask about their own messages).
- **An oracle future-consumer policy is nearly free here.** It only has to
  protect 0.96% of the corpus, so it wins the formation stage at every budget
  for reasons unrelated to the hypothesis. A Phase-0 oracle gate run on
  GroupMemBench alone will pass almost automatically.
- **94.4% of the oracle's advantage is per-question memorisation.** Only 5.6%
  of evidence units are wanted by more than one question, so a leave-one-out
  oracle — which is the honest test of whether future demand is *predictable* —
  would lose most of the benefit. This is the main threat to Contribution 1.

## LoCoMo

- GitHub `snap-research/locomo`, `data/locomo10.json`, 2.8 MB.
- 10 conversations, 5,882 turns, 1,986 QA, **1,982 with `evidence` turn ids**.
- Categories: 1 multi-hop (282), 2 temporal (321), 3 open-domain (96),
  4 single-hop (841), 5 adversarial (446).
- Every turn carries `speaker` and `dia_id`.
- **Two speakers per conversation and no asker id.** LoCoMo can validate the
  failure decomposition at scale, but cannot test any future-consumer claim.

## LongMemEval

- HF `xiaowu0162/longmemeval`: `longmemeval_oracle` 15.4 MB (500 questions),
  `longmemeval_s` 278 MB, `longmemeval_m` 2.7 GB.
- Types: temporal-reasoning 133, multi-session 133, knowledge-update 78,
  single-session-user 70, single-session-assistant 56, preference 30.
- Evidence is available at two granularities: `answer_session_ids`, and a
  per-turn `has_answer` flag inside the haystack sessions.
- Two parties (user / assistant), so again no multi-party consumer structure.

## SocialMemBench

- HF `anon4data/socialmembench` (the `MemoryAgentBench/SocialMemBench` id is
  gated and returns 401).
- 43 group networks, 430 personas, 7,355 conversation turns, 1,031 QA. ~2.1 MB.
- **Genuinely multi-party**, with `speaker_persona_id`, `reply_to_turn_id`,
  session indices, per-persona attributes (occupation, communication profile,
  preferences) and an explicit relationship network between members.
- QA carries `evidence_anchors_json`: `turn_id`, speaker, message excerpt, and a
  written relevance rationale — the richest evidence annotation of the datasets
  reviewed here.
- Caveats: answers are long-form or multiple-choice social inferences, so
  grading needs an LLM judge rather than lexical matching; there is **no asking
  participant**; and the repository is anonymous, so licence and citation are
  unclear.

## DialSim

- HF `jiho283/dialsim-friends` / `-bigbang` / `-theoffice`. Multi-party TV
  transcripts with per-episode multiple-choice questions and `..._idxes` fields
  for the easy questions only. Evidence pointers are partial and the format
  nests JSON inside string columns. Low priority.

## Verdict

| Dataset | Evidence pointers | Categories | Multi-party | Named asker | Use for |
| --- | :---: | :---: | :---: | :---: | --- |
| GroupMemBench + recovered evidence | Finance only | yes | yes | yes | Primary: Table 3 and every future-consumer claim. |
| LoCoMo | yes (1,982) | yes | no | no | Scale check on the decomposition. |
| LongMemEval | yes (session + turn) | yes | no | no | Held-out generalisation; strongest `knowledge_update` set. |
| SocialMemBench | yes (rich) | yes | yes | no | Best second multi-party set; needs an LLM judge. |
| DialSim | partial | yes | yes | no | Optional. |

**The binding constraint on the whole proposal is that only 185 questions, in
one GroupMemBench domain, currently have both an asker and gold evidence.**
Recovering evidence for the other three domains (531 questions) is the single
highest-value data task remaining.
