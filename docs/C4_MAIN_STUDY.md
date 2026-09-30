# C4 Main Study: Speaker Attribution in Compressed Meeting Memory

*As of 2026-09-28. Branch `ming/c4-failure-decomposition`.*

**Result.** We built 1,200 frozen probes from 169 real AMI meetings.
Compressing each statement to a tenth of its words cut `qwen2.5:14b`'s speaker
attribution by **9.2 pts [−12.3, −6.0]** (McNemar p = 2.8 × 10⁻⁸). This was
the registered primary outcome. The study moves C4 past the pilot on three
fronts:

- real meeting data instead of synthetic chat;
- an analysis plan committed before any output;
- a safeguard against each failure the pilot exposed.

## What changed after the pilot

| Pilot problem | Change in the main study |
| --- | --- |
| Synthetic GroupMemBench chat: one model wrote every speaker, so there was little individual voice to bind | AMI Meeting Corpus: 171 real meetings, 83,868 utterances (CC BY 4.0) |
| Retrieved contexts all shared one topic | 20-turn conversation windows inside one meeting |
| The reader sat at the floor, so the sweep could only measure a floor | A headroom gate before any sweep, and a larger reader when the gate fails |
| Analysis choices could be made after seeing data | Analysis plan committed to git before any AMI output (`2ff180c`) |
| Label-only shortcuts can beat chance without reading content | Frequency (+7.0 pts over chance on AMI) and turn-taking (+6.2 pts) shortcuts recorded per row. The gate requires a significant lead over the stronger of the two |
| One word budget per conversation cut long meeting turns to about 27% at budget "0.5" | A per-message budget: every message keeps round(b × words) words, the same rule as the LLM summarizer |
| The lexical baseline lived in a one-off script | A lexical TF-IDF attributor is scored on every row, on the same compressed text the reader sees |
| "At chance" was claimed from non-significant tests | Every estimate reports its smallest detectable effect and one reading: effect, no effect beyond the margin, or inconclusive |

## Method

| Component | Setting |
| --- | --- |
| Data | AMI manual annotations v1.6.2. One utterance per transcriber segment, ordered by start time. Speakers are shown as `Speaker_A`–`E`, with no names or roles |
| Probe | One statement of at least 8 words (mean 28.4), its label hidden inside a 20-turn window. The reader picks its speaker from the visible roster: 2–5 speakers, chance 27.6% |
| Sample | 1,200 probes from a deterministic shuffle (seed 0), covering 1,126 windows in 169 meetings. 278 of them have a label-swap counterfactual |
| Compression | Salient word-drop per message: keep the round(b × words) highest-IDF words, in their original order. b = 1.0, 0.5, 0.25, 0.1, giving 28.4 → 14.2 → 7.1 → 2.9 target words |
| Readers | `qwen2.5:7b` and `qwen2.5:14b` through Ollama. Temperature 0, seed 0, answers constrained to the roster |
| Baselines | Chance; frequency shortcut (34.6%); turn-taking shortcut (33.8%); lexical TF-IDF attributor |
| Headroom gate | Sweep only if two lower 95% bounds clear their bars: lift over chance above +5 pts, and lead over the stronger shortcut above 0 |
| Primary outcome | Paired change in Hit@1 from budget 1.0 to 0.1, on the same probes |
| Statistics | Cluster bootstrap by meeting (2,000 resamples) and exact McNemar, with a ±5 pt margin read through two one-sided tests (TOST) |

## Results

**Headroom (uncompressed).**

| Attributor | Hit@1 [95% CI] | Lead over chance | Lead over the stronger shortcut | Gate |
| --- | --- | --- | --- | --- |
| Lexical TF-IDF | 48.8% [45.3, 52.1] | +21.1 pts [+17.9, +24.5] | +14.2 pts | clear |
| `qwen2.5:14b` | 40.4% [37.3, 43.6] | +12.8 pts [+9.7, +16.0] | +5.8 pts (lower bound +2.1) | pass, swept |
| `qwen2.5:7b` | 37.6% [35.0, 40.3] | +10.0 pts [+7.4, +12.7] | +3.0 pts (lower bound −0.1) | fail, not swept |

**Dose-response.** Each cell is paired against the same probes at budget 1.0.

| Budget (words kept) | 14B Hit@1 | 14B change [95% CI] | Lexical Hit@1 | Lexical change [95% CI] |
| --- | --- | --- | --- | --- |
| 1.0 (28.4) | 40.4% | — | 48.8% | — |
| 0.5 (14.2) | 35.8% | −4.6 pts [−7.3, −1.9] | 45.6% | −3.2 pts [−5.3, −0.9] |
| 0.25 (7.1) | 31.3% | −9.1 pts [−12.2, −6.1] | 39.0% | −9.8 pts [−13.2, −6.7] |
| 0.1 (2.9) | 31.2% | **−9.2 pts [−12.3, −6.0]** | 32.6% | −16.2 pts [−20.0, −12.0] |

Every change reads as an **effect** at the ±5 pt margin, with McNemar p < 0.01.

- **Timing of the loss.** The 14B reader loses most of its lead by budget
  0.25. From there it sits at 31%, below both label-only shortcuts.
- **Lexical attributor.** It keeps losing all the way down. About three
  quarters of its lead over chance is gone at budget 0.1.
- **Binding (label swap, 278 probes).** The lexical attributor links a
  statement to its author's other lines: +19.8 pts [+10.3, +29.2]
  uncompressed, falling to +5.4 pts at 0.1. The 14B reader's binding index is
  +5.4 pts [−3.2, +14.4], which is inconclusive at this sample size.
- **Group size.** In 3- and 4-speaker windows, both attributors lose roughly
  three quarters of their above-chance margin by budget 0.1. The 2- and
  5+-speaker windows are too few to read (36 and 13 probes).
- **Data quality.** There were 0 reader errors and 0 invalid answers across
  5,634 rows in the 14B run.

## Deviations from the plan

- `qwen2.5:7b` failed the gate, so no 7B sweep was run. Per the plan,
  `qwen2.5:14b` was run instead.
- The lexical curve needs no LLM. It was computed over the same 1,200 frozen
  probes with the stub reader and `--skip-gate`. The stub's own answers are
  ignored.
- Everything else ran as registered in [`C4_ANALYSIS_PLAN.md`](C4_ANALYSIS_PLAN.md).

## Limitations

- **One passing reader.** 32B and 72B readers are untested and need the GPU
  machine.
- **Word-drop only.** The LLM-summary compressor is built but not run at
  scale.
- **Small swap arm.** 278 probes are too few to settle whether the LLM binds.
- **Text only.** The transcripts are manual, not ASR output, and there is no
  audio.
- **Per-message compression.** Merged multi-speaker summaries are not tested.

## Reproduce

```bash
curl -LO https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
unzip ami_public_manual_1.6.2.zip -d data/raw/ami
uv run python scripts/data/convert_ami.py
A="--dataset utterances --utterances data/processed/ami.jsonl --contexts window \
   --window-size 20 --window-stride 10 --min-target-words 8 --budgets 1.0 0.5 0.25 0.1 \
   --allocation per-message --limit 1200"
PYTHONHASHSEED=0 uv run python scripts/evaluation/run_attribution_frozen.py $A --model qwen2.5:14b
uv run python scripts/evaluation/analyze_attribution_frozen.py \
  --csv results/proposed/attribution_v2/attribution_frozen_uniform_compression_qwen2.5-14b_ami_win20s10_min8_per-message.csv
```

On an M1 Pro laptop (16 GB), the 14B gate took about 2 h and its sweep about
6 h. The lexical curve takes seconds: add `--reader stub --skip-gate` to the
run, then `--score lexical` to the analysis. Rendered tables are in
`results/comparisons/attribution_v2/`.

## Commits past the pilot

| Commit | What it added |
| --- | --- |
| `57a83b5` | Main result: 14B gate pass and sweep; results appended to the plan |
| `c373157` | 7B gate failure; lexical curve; `--score lexical` |
| `2ff180c` | Analysis plan, registered before any AMI output |
| `80962d0` | Lexical attributor on every row |
| `22368ac` | AMI converter, turn-taking shortcut, stricter gate, per-message compression |
| `1dc8bc9` | Detectable effect and equivalence reading per estimate |
| `a4db947`, `342d136` | Frozen-probe instrument and its 62-test harness (79 tests now) |
