# C4 Analysis Plan — AMI Meeting Study

**Registered:** 2026-09-27, committed to git **before any reader output on AMI
existed**. The commit that adds this file is the timestamp. Anything changed
afterwards goes under *Deviations* at the bottom, with the reason.

## Question

After a memory is compressed, can a reader still tell who said a statement in
a real multi-party meeting, and does that ability fall as compression grows?

## Why this study

The GroupMemBench pilot hit a floor: uncompressed, `qwen2.5:7b` could not be
told apart from chance (+3.4 pts, 95% CI [−0.8, +7.4]), so it could not
measure loss from compression. GroupMemBench is synthetic (one model wrote
every speaker) and its contexts were retrieved for one topic. AMI is real
speech from real people in real meetings.

## Data

- AMI Meeting Corpus manual annotations v1.6.2 (CC BY 4.0), zip sha256
  `b56e5babb2496b87…`, converted with `scripts/data/convert_ami.py`: 171
  meetings, 83,868 utterances (one per transcriber segment), output sha256
  `f15cc2fa6db2ca48…`. Speakers are labelled `Speaker_A…E`; real names and
  roles are not shown to the reader.
- **Contexts:** windows of 20 consecutive turns, stride 10, never crossing a
  meeting.
- **Targets:** at least 8 words (mean 28.4), and the author must speak elsewhere
  in the window. Roster = the speakers visible in the window.
- **Sample:** the first 1,200 probes of a deterministic shuffle (seed 0):
  1,126 windows from 169 meetings. The label-swap arm uses the 278 of these
  that have a speaker with an equal label count.

## Conditions

- **Reader:** `qwen2.5:7b` (Ollama digest `845dbda0ea48`), temperature 0, seed 0.
  Decoding is constrained to the roster.
- **Compressor:** salient word-drop with **per-message** allocation. Each
  message keeps `max(1, round(b × words))` of its highest-IDF words, in their
  original order. This is the same rule as the summary compressor.
- **Budgets:** 1.0, 0.5, 0.25, 0.1, giving target lengths of 28.4, 14.2, 7.1
  and 2.9 words. The swap arm runs at 1.0, 0.25 and 0.1.
- **Baselines** (computed per row, no model):
  - chance (27.6%);
  - the frequency heuristic (34.6%);
  - the turn-taking heuristic (33.8%);
  - the lexical TF-IDF attributor.

## Decision rules (fixed now)

1. **Headroom gate**, on the uncompressed probes. PASS iff both hold:
   - the lower 95% bound of (Hit@1 − chance) is above **+5 pts**;
   - the lower 95% bound of (Hit@1 − the stronger label-only heuristic) is
     above 0.

   If the gate fails, no compression sweep is run with that reader. The
   headroom result is itself the finding.
2. **Primary outcome:** the paired change in Hit@1 from budget 1.0 to 0.1 on
   the same probes (main arm).
3. **Margin:** ±5 pts. Each estimate gets exactly one reading:
   - **effect**: the 95% CI excludes 0;
   - **no effect beyond the margin**: the 90% CI lies inside ±5 pts (two
     one-sided tests, α = .05);
   - **inconclusive**: neither holds.
4. **Secondary outcomes (reported, not decisive):**
   - the changes at 0.5 and 0.25;
   - the lexical attributor's curve;
   - the swap-arm binding index;
   - results by roster size.
5. **Statistics:** cluster bootstrap by **meeting** (2,000 resamples, seed
   20260923) and exact McNemar on discordant pairs. The primary outcome is a
   single test, so no correction is applied; secondary outcomes are labelled
   exploratory.
6. **Exclusions:** rows with reader errors are dropped and counted. There are
   no other exclusions.

## Power

In the pilot, 29% of probes changed answer between 1.0 and 0.1. At that rate
and n = 1,200, the smallest drop detectable at 80% power is about **4.4 pts**
(2.80 × √(0.29/1200)), before clustering. Table 5 reports the detectable
effect computed from the actual data.

## More readers

If `qwen2.5:7b` fails the gate, the same gate is run with a larger reader:
`qwen2.5:14b` locally, and `qwen2.5:32b`/`72b` on the GPU machine when
available. Each reader is reported separately and never pooled. A reader that
passes the gate gets the full sweep.

## Commands

```bash
uv run python scripts/data/convert_ami.py
A="--dataset utterances --utterances data/processed/ami.jsonl --contexts window \
   --window-size 20 --window-stride 10 --min-target-words 8 --budgets 1.0 0.5 0.25 0.1 \
   --allocation per-message --limit 1200"
PYTHONHASHSEED=0 uv run python scripts/evaluation/run_attribution_frozen.py $A --controls
PYTHONHASHSEED=0 uv run python scripts/evaluation/run_attribution_frozen.py $A --model qwen2.5:7b
uv run python scripts/evaluation/analyze_attribution_frozen.py \
  --csv results/proposed/attribution_v2/attribution_frozen_uniform_compression_qwen2.5-7b_ami_win20s10_min8_per-message.csv
```

## Decided after the pilot, before any AMI outcome

These choices were made after seeing the pilot but before any AMI outcome:

- Per-message allocation. The pooled allocation cut long AMI statements to
  about 27% at budget "0.5".
- The turn-taking heuristic, and the requirement that the gate beat it
  significantly. Label-only shortcuts sit about 7 pts above chance on AMI
  windows.
- 20-turn windows and a minimum of 8 words. Shorter settings give weaker
  content and stronger label shortcuts.

## Deviations

- **2026-09-27, 7B gate result.** `qwen2.5:7b` failed the gate. Its lift
  over chance was +10.0 pts [+7.4, +12.7], but its lead over the frequency
  heuristic, +3.0 pts, had a lower bound of −0.1. As planned, no LLM sweep
  was run with this reader, and the gate was started with `qwen2.5:14b`.
- **2026-09-27, how the lexical curve was computed.** The lexical attributor's
  curve is a planned secondary outcome, and it needs no LLM. The LLM sweep did
  not run, so the curve was computed separately:
  - same 1,200 frozen probes and budgets, and the same per-message compression;
  - run with `--reader stub --skip-gate` into `results/proposed/attribution_v2_lexical/`;
  - scored with `analyze_attribution_frozen.py --score lexical`.

  The stub's own answers, and the gate line it prints, are ignored. The
  attributor's own headroom was clear: 48.8% uncompressed, against a best
  label-only heuristic of 34.6%.

### 2026-09-30, three more corpora

The study extends from AMI to three further multi-party corpora, each read
through the identical registered design -- 20-turn windows, stride 10, targets
of at least 8 words, budgets 1.0 / 0.5 / 0.25 / 0.1, per-message allocation,
the first 1,200 probes of the seed-0 shuffle -- with the same decision rules,
the same +-5 pt margin and every reader reported separately.

| Corpus | Licence | Conversations | Utterances | Speakers per conversation |
| --- | --- | ---: | ---: | --- |
| ICSI core NXT v1.0 | CC BY 4.0 | 75 | 108,984 | 3-10 |
| ELITR Minuting (English) | CC BY-NC-SA 4.0 | 119 | 33,298 | 2-14 |
| Supreme Court (ConvoKit, 2017-2019) | none stated | 194 | 46,010 | 8-13 |

Construction checks, run with `--controls` before any reader saw these corpora:

| Corpus | Probes | Contexts | Clusters | Chance | Frequency | Turn-taking | Target words | Swap-eligible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AMI | 1,200 | 1,126 | 169 | 27.6% | 34.6% | 33.8% | 28.4 | 278 |
| ICSI | 1,200 | 1,132 | 75 | 30.8% | **55.2%** | 18.7% | 15.2 | 189 |
| ELITR | 1,200 | 998 | 119 | 33.5% | 36.1% | **54.9%** | 41.4 | 185 |
| Supreme Court | 1,200 | 1,055 | 192 | 23.7% | **42.6%** | 35.3% | 62.7 | 254 |

Zero invariant violations on all four.

**Read the gate against those shortcuts, not against chance.** The gate already
requires a significant lead over the stronger label-only heuristic, and on the
three new corpora that heuristic sits 18.9 to 24.4 points above chance, against
7.0 on AMI. A gate failure is the result for that reader on that corpus, and no
sweep follows it. This is recorded before the runs so that a failure cannot
later be reported as a surprise.

The two extremes have identifiable causes, and neither is a defect:

- **ICSI, frequency 55.2%.** Meetings run to 10 speakers but are dominated by
  one or two, so "name the most-labelled speaker" is strong.
- **ELITR, turn-taking 54.9%.** The converter makes one utterance per speaker
  marker, so adjacent turns always have different speakers and "not the
  neighbours" becomes genuinely informative. Splitting per line instead would
  weaken the shortcut, at the cost of dropping mean target length from 24.0
  words to 9.6. Length was preferred; the consequence is recorded here.

**ELITR also keeps in-text entity placeholders.** `[PERSON20]` and the like
survive in the text, drawn from the same numbering as the speaker markers.
Speakers are relabelled `Speaker_<letter>` per meeting, so no placeholder
matches any roster label and none can leak an answer literally.

**Supreme Court speakers are anonymised.** The source names them; the design
shows the reader `Speaker_<letter>` and nothing else. Justice / Advocate is
carried as `role`, which never reaches the prompt.

### 2026-09-30, the LLM-summary compressor arm

The registered design is run again with `--compressor summary`
(`qwen2.5:7b` writes the summaries, the reader reads them) at the same budgets
and on the same frozen probes, so word-drop and summary compression are paired
probe by probe at matched word budgets. Reported as a second compressor, never
pooled with the word-drop arm.

### 2026-09-30, a swap-only option for the label-swap arm

The binding index was the one estimate the main study could not read: +5.4 pts
[-3.2, +14.4] for `qwen2.5:14b`, inconclusive on 278 probes. Only probes with a
speaker of equal visible label count qualify, about a quarter of any sample, so
the arm could previously grow only by re-running the whole sweep.

`--swap-only` keeps just the eligible probes, restricts budgets to
`--swap-budgets` (1.0, 0.25, 0.1) and runs both conditions on them. `--limit`
then counts eligible probes. AMI has 14,554 eligible probes across 171
meetings, so the planned `--limit 1000` is a random subsample of them under the
same seed-0 shuffle, not a different construction.

**The headroom gate still applies.** Eligible probes are a different population
from the registered 1,200, so the gate is re-evaluated on them and a failure is
reported as a result rather than overridden. The arm remains a secondary,
exploratory outcome, as registered.

### 2026-09-30, the reader's context window

The reader now sends `num_ctx` explicitly instead of accepting Ollama's
default of 4,096, which truncates longer prompts silently and from the left --
where the instructions and the candidate roster sit, so a truncated probe would
still have been graded.

Nothing in the AMI result is affected: its longest prompt estimates at 1,759
tokens, and ICSI's at 936. The fix matters for the new corpora, where 6 of
1,200 Supreme Court probes and 9 of 1,200 ELITR probes exceed 4,096 at budget
1.0. The default is 8,192 and the runs on those two corpora use 16,384.
`--controls` now reports the longest prompt and warns when it will not fit.


## Results (2026-09-28)

These are reported against the rules above. Rendered tables are in
`results/comparisons/attribution_v2/`.

- **Headroom gate.**
  - `qwen2.5:7b` failed (see Deviations).
  - `qwen2.5:14b` passed: 40.4% [37.3, 43.6] against 27.6% chance, a lift
    of +12.8 pts [+9.7, +16.0], and a lead of +5.8 pts (lower bound +2.1)
    over the frequency heuristic (34.6%).
- **Primary outcome** (`qwen2.5:14b`, paired 1.0 → 0.1): **−9.2 pts
  [−12.3, −6.0]**, 250 lost / 140 gained, McNemar p = 2.8 × 10⁻⁸.
  Reading: **effect**.
- **Secondary outcomes.**
  - The 14B's changes at 0.5 and 0.25 are −4.6 pts [−7.3, −1.9] and
    −9.1 pts [−12.2, −6.1]; both read as effects. Accuracy is flat from
    0.25 to 0.1 (31.3%, 31.2%), below both label-only heuristics.
  - Lexical attributor: 48.8% → 45.6% → 39.0% → 32.6%, a change of
    −16.2 pts [−20.0, −12.0] at 0.1.
  - Label swap, 14B: the binding index is +5.4 pts [−3.2, +14.4]
    uncompressed and near 0 when compressed. That arm has only 278 probes,
    so it is inconclusive. The lexical attributor binds significantly:
    +19.8 pts [+10.3, +29.2] uncompressed.
  - By roster size, the 14B loses most of its above-chance margin by 0.1
    in both 3- and 4-speaker windows. The 2- and 5+-speaker groups are too
    small (n = 36 and n = 13) to read.
- **Errors and exclusions:** no reader errors and no invalid answers in
  5,634 rows.

## Results, `qwen2.5:32b` (2026-10-04)

Run on a rented A40, against the *More readers* clause registered above, so
this is not a deviation. Rendered tables are in
`results/comparisons/attribution_v2/`.

- **Headroom gate: PASS.** 42.3% [39.4, 45.3] against 27.6% chance — a lift of
  **+14.7 pts [+11.9, +17.7]** — and a lead of +7.7 pts (lower bound +4.7) over
  the frequency heuristic at 34.6%. Stronger headroom than the 14B on both
  tests. **This is the second passing reader the main study said it lacked.**
- **Primary outcome** (paired 1.0 → 0.1): **−9.3 pts [−12.1, −6.5]**, 204 lost
  / 92 gained, McNemar p = 6.6 × 10⁻¹¹. Reading: **effect**.
- **The 14B result replicates almost exactly.** 14B lost −9.2 pts
  [−12.3, −6.0]; 32B loses −9.3 pts [−12.1, −6.5]. A reader with more headroom
  to lose loses the same amount, which is the direct answer to the obvious
  objection that the main result is an artefact of a reader that was barely
  above chance to begin with.
- **Secondary outcomes.** −5.6 pts [−7.8, −3.2] at 0.5 and −8.1 pts
  [−10.7, −5.5] at 0.25; both read as effects. At 0.1 the 32B sits at 33.0%,
  **below the 34.6% frequency shortcut** — the same crossing the 14B showed at
  31.2%, so neither reader keeps a content-based advantage at a tenth of the
  words.
- **Label swap**, 278 probes: binding index +5.0 pts [−3.0, +13.2]
  uncompressed, falling to −3.6 pts [−11.8, +4.2] at 0.1. Inconclusive at this
  sample size, exactly as for the 14B (+5.4 pts [−3.2, +14.4]); this is the
  estimate the `--swap-only` arm exists to settle.
- **Errors and exclusions:** no reader errors, no invalid answers, 100% valid
  across 5,634 rows.
- **Provenance:** git `dc8da1d`, clean; `qwen2.5:32b` digest `9f13ba1299af`;
  `data/processed/ami.jsonl` sha256 `f15cc2fa6db2…`, unchanged from the
  registered value; Python 3.13.12, `PYTHONHASHSEED=0`.
