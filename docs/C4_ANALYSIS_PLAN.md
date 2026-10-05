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


### 2026-10-05, a swap arm on Supreme Court

Registered before the run. The AMI swap arm failed its gate, and the cause is
specific to AMI rather than to the swap design: the gate is re-read on the
swap-eligible subpopulation, and on AMI that subset is hard. Measured on
existing rows, with no new model calls:

| Corpus | Reader on swap-eligible | Best shortcut there | Lead |
| --- | ---: | ---: | ---: |
| AMI, 32B | 33.1% | 35.9% | −2.8 pts (the failure) |
| ICSI, 32B | 33.9% | 19.9% | +14.0 pts |
| Supreme Court, 14B | 47.6% | 27.9% | +19.8 pts |
| Supreme Court, 32B | 54.2% | 28.0% | +26.3 pts |

Selecting probes whose author has an equal-count partner collapses the
frequency shortcut by construction, so the arm is gated on turn-taking. On AMI
turn-taking *rises* on that subset (33.8% → 35.9%) while the reader falls
(42.3% → 33.1%). On Supreme Court the reader holds 54.2% against 28.0%.

So the binding index is run again on **Supreme Court with `qwen2.5:32b`**,
`--swap-only --limit 1000` at the registered swap budgets (1.0, 0.25, 0.1).
Supreme Court has 12,244 swap-eligible probes, so the limit is a random
subsample under the same seed-0 shuffle, not a different construction.

The gate still applies and is still read first. If it fails here too, that is
the result and the binding index stays open. Reported as a secondary,
exploratory outcome, as the swap arm always has been.

### 2026-10-05, a word-drop arm at matched realised length

Registered before the run. The summary arm undershoots its nominal budget, so
the two compressors are only comparable at 1.0 and 0.1. Rather than change the
summarizer, the word-drop arm is re-run at budgets chosen so its **realised**
length matches the summarizer's. The budgets were picked with `--controls`,
which needs no model calls, and before any reader saw them:

| Word-drop budget | Realised words | Matches the summary arm at |
| ---: | ---: | --- |
| 0.32 | 9.1 | 0.5 (9.0 words) |
| 0.20 | 5.7 | 0.25 (5.8 words) |

Run on AMI with `qwen2.5:14b` — the same reader as the summary arm, so the
compressor is the only thing that varies — at `--budgets 1.0 0.32 0.20`, into
its own `--out-dir`.

The comparison is then stated by **realised length, not by nominal budget**,
and that pairing is named wherever the numbers appear. This adds a comparison;
it does not revise the registered budgets, and the original arms stand as
reported.

### 2026-10-05, finishing the 32B Supreme Court run

The run is 362 rows short at `status: running`. It is resumed once more on a
fresh pod; the dataset hashes identically, so finished rows are skipped. The
earlier note calling the failure "most likely OOM" is weaker than it was
written: the same run **completed once**, on the second pod, which a
reproducible memory bound would not do. The cause is unknown and intermittent.

If it fails a third time it is reported at n = 1,095 with `running` disclosed,
and no further compute is spent on it.

### 2026-10-06, where does binding actually break? (scope decomposition)

Registered before the run. The study so far shows that compressing a window
costs attribution, but not **what** the compression destroys. A free analysis
of existing rows makes the gap concrete: splitting probes into target-length
quartiles *within* each corpus shows the target's own length explains very
little of the loss.

| Run | Q1 shortest | Q4 longest |
| --- | ---: | ---: |
| Supreme Court, 32B | −35.4 pts (8–20 w) | −39.3 pts (78–628 w) |
| Supreme Court, 14B | −23.7 pts (8–20 w) | −42.0 pts (80–628 w) |
| AMI, 32B | −6.0 pts (8–12 w) | −11.7 pts (34–212 w) |
| ICSI, 32B | −4.3 pts (8–10 w) | −9.3 pts (18–62 w) |

Supreme Court probes whose target is 8–20 words lose **35 pts**; AMI probes of
the same target length lose **6**. Same target length, six times the loss — so
the cross-corpus difference is not the target's length, and the figure caption
"the more speaker evidence a turn carries" must mean the *window*, not the
probed statement.

`run_attribution_frozen.py` already carries `--compress-scope`, unused in this
study. Two further arms on AMI with `qwen2.5:32b`, at the registered budgets,
against the existing `both` baseline:

- **`--compress-scope target`** — compress only the hidden statement; the
  author's other lines stay full length.
- **`--compress-scope context`** — compress only the other lines; the statement
  stays full length.

**The prediction, stated before the runs:** binding needs the author's other
lines, so the `context` arm should carry most of the loss and the `target` arm
much less. If instead `target` dominates, what compression destroys is the
statement's own content, not the speaker binding, and the study's framing needs
rewording. Either outcome is reportable; this is registered so that neither can
be chosen after the fact.

Swap rows are switched off in these arms (`--swap-budgets` empty): the
counterfactual is about labels, and these arms vary text.

### 2026-10-06, a reader from a different family

Registered before the run. **Every reader in this study is `qwen2.5`** — 7b,
14b and 32b. That is one model family, one tokenizer and one training recipe,
and it is the most obvious objection to the whole result.

`gemma2:27b` is run on AMI under the registered design, as a reader reported
separately and never pooled, exactly as the plan already requires. It is
comparable in size to `qwen2.5:32b` and shares no lineage with it.

It may fail the headroom gate, as `qwen2.5:7b` did. That is a result and is
reported as one; no sweep follows a failed gate.

## Results, the follow-up arms (2026-10-06)

### The reader binds statements to their author's other lines, and compression destroys that

The label-swap counterfactual, run on **Supreme Court with `qwen2.5:32b`**,
1,000 eligible probes. Labels A↔B are swapped on the non-target messages;
following the swap means the statement was bound to its author's other lines,
answering the original author means a content prior survived the relabel.

| Budget | Follows swap | Original author | **Binding index** | Chance |
| ---: | ---: | ---: | --- | ---: |
| 1.0 | 48.8% [45.6, 52.1] | 10.6% [8.7, 12.4] | **+38.2 pts [+34.2, +42.4]** | 20.7% |
| 0.25 | 21.3% [19.1, 23.7] | 16.5% [14.2, 19.1] | +4.8 pts [+1.1, +8.5] | 20.7% |
| 0.1 | 19.7% [17.4, 22.1] | 17.6% [15.0, 20.4] | +2.1 pts [−2.0, +6.0] | 20.7% |

**This settles the estimate the study could not read.** On AMI the binding index
was +5.4 pts [−3.2, +14.4] on 278 probes — inconclusive, and the reason the
`--swap-only` option was built. On Supreme Court it is **+38.2 pts**, an
interval nowhere near zero: the reader is overwhelmingly tracking *who else
said things like this*, not a prior about the content.

And compression destroys exactly that: +38.2 → +4.8 → **+2.1 [−2.0, +6.0]**, an
interval containing zero. By a tenth of the words the statement is no longer
bound to its author at all.

### Where binding breaks: the prediction was wrong

Registered prediction: binding needs the author's other lines, so the `context`
arm should carry most of the loss. **It does not.** On AMI with `qwen2.5:32b`:

| Arm | 1.0 → 0.5 | 1.0 → 0.25 | 1.0 → 0.1 |
| --- | --- | --- | --- |
| `both` | −5.6 [−7.8, −3.2] | −8.1 [−10.7, −5.5] | −9.3 [−12.1, −6.5] |
| `context` only | −5.3 [−7.8, −2.9] | −8.9 [−11.3, −6.6] | −8.2 [−11.0, −5.5] |
| `target` only | −4.9 [−7.1, −2.8] | −7.0 [−9.6, −4.5] | −9.1 [−11.4, −6.9] |

Compressing **either side alone costs about as much as compressing both**, at
every budget, with intervals overlapping throughout. The two do not add: 9.1 +
8.2 is not 9.3.

Two readings, and the second is more parsimonious:

1. Attribution is a **matching operation** between the statement and the
   author's other lines, so degrading either operand breaks the match and
   degrading both cannot break it twice. The swap result above supports this:
   the reader really is matching against the other lines.
2. A **floor**. All three arms land at 33–34% at budget 0.1, against a 34.6%
   frequency shortcut. Once any single intervention pushes the reader onto the
   label-only floor, nothing further can be lost, so the arms cannot separate.

The honest statement is that **this design cannot localise the damage**, and
the registered prediction is refuted either way. Separating the two readings
needs budgets that keep the reader above the shortcut — the 0.5 cells, where
all three arms are also indistinguishable, suggest the matching reading, but
not decisively.

### A reader from a different family replicates it, larger

`gemma2:27b` on AMI, registered design, reported separately and never pooled.

| | Uncompressed | 1.0 → 0.1 |
| --- | ---: | --- |
| `gemma2:27b` | **45.8% [42.9, 48.7]** | **−13.8 pts [−16.7, −11.1]**, p = 2 × 10⁻¹⁷ |
| `qwen2.5:32b` | 42.3% | −9.3 pts [−12.1, −6.5] |
| `qwen2.5:14b` | 40.4% | −9.2 pts [−12.3, −6.0] |

It **passes the gate** with a lift of +18.1 pts [+15.3, +21.0] — the best
uncompressed reader on AMI — and loses *more* to compression than either qwen.
At budget 0.1 it reaches 31.9%, below the 34.6% frequency shortcut, the same
crossing both qwen readers show.

**The result is not an artefact of one model family.** This was the most
obvious objection to the study and it does not survive.

### The compressors are indistinguishable at matched length

Same reader (`qwen2.5:14b`), AMI, comparing by **realised** words rather than
nominal budget:

| Realised words | Word-drop | LLM summary |
| ---: | --- | --- |
| ~9 | −7.8 pts [−11.1, −4.7] | −5.2 pts [−8.3, −2.2] |
| ~5.7 | −8.3 pts [−11.5, −5.2] | −8.5 pts [−11.5, −5.4] |
| 2.9 / 2.7 | −9.2 pts [−12.3, −6.0] | −7.9 pts [−11.3, −4.5] |

Intervals overlap heavily at all three lengths. **The budget-matching
limitation is closed**: a realistic LLM summarizer destroys who-said-what about
as much as naive word-dropping, and that now rests on three matched lengths
rather than one.

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

## Results, the three new corpora (2026-10-05)

All seven runs used the registered design unchanged. **Four of the seven gates
passed**, against the expectation recorded in `docs/PC_HANDOFF.md` that the
stronger label-only shortcuts would mostly block them. They raised the bar; the
readers cleared it on the long-turn corpora.

| Corpus | Reader | Uncompressed | Best shortcut | Lead (lower bound) | Gate |
| --- | --- | ---: | ---: | ---: | --- |
| Supreme Court | 32B | 62.5% | 42.6% | +19.8 (+16.6) | **pass** |
| Supreme Court | 14B | 58.4% | 42.6% | +15.8 (+12.3) | **pass** |
| ICSI | 32B | 61.1% | 55.2% | +5.9 (+3.0) | **pass** |
| ICSI | 14B | 58.4% | 55.2% | +3.2 (−0.3) | fail |
| ELITR | 32B | 52.8% | 54.9% | −2.2 (−6.0) | fail |
| ELITR | 14B | 47.2% | 54.9% | −7.8 (−11.9) | fail |

### Supreme Court: the largest effect in the study

| Reader | Paired n | 1.0 → 0.1 | McNemar p | At 0.1, lift over chance |
| --- | ---: | --- | ---: | --- |
| 32B | 1,095 | **−36.9 pts [−40.4, −33.3]** | 5 × 10⁻⁷⁸ | **+1.4 pts [−1.3, +4.1]** |
| 14B | 1,200 | **−28.2 pts [−31.5, −25.1]** | 1 × 10⁻⁵³ | +6.5 pts [+3.9, +9.2] |

Three to four times the AMI effect, on the corpus chosen for long, distinctive
turns (62.7 target words against AMI's 28.4). **At a tenth of the words the 32B
reader's lift over chance has a 95% interval that includes zero** — it has gone
from +38.8 pts to statistically indistinguishable from guessing. Both readers
end far below the 42.6% frequency shortcut, at 30.2% and 25.0%.

This is the cleanest statement the study can make: where there is the most
speaker evidence to destroy, compression destroys the most.

### ICSI: passes with the 32B, small effect

61.1% → 54.2%, a change of **−6.9 pts [−9.4, −4.5]**, McNemar p = 4 × 10⁻⁷.
Targets are short here (15.2 words), which plausibly caps how much there is to
lose. At 0.1 the reader sits at 54.2%, **below its own 55.2% frequency
shortcut** — the same crossing AMI shows.

The 14B missed by a hair: a +3.2 pt lead over the frequency shortcut with a
lower bound of −0.003. It failed, and it is reported as a failure.

### ELITR: fails with both readers

47.2% and 52.8% against a turn-taking shortcut of 54.9%. Neither reader beats
it, so no sweep ran. The cause was recorded before the run: the converter makes
one utterance per speaker marker, so adjacent turns always have different
speakers and "not the neighbours" becomes genuinely informative. **ELITR as
converted cannot support a speaker-attribution claim**, and that is the result.

### The bigger label-swap arm also failed its gate

`--swap-only` reached 1,000 eligible probes against the 278 the ride-along arm
manages, as designed. On that subpopulation the 14B scored 36.1% against a
turn-taking shortcut of 35.3% — a lead of +0.8 pts, lower bound −3.4 — so the
gate failed and no swap sweep ran.

This is the decision recorded above being honoured: the swap-eligible probes
are a different population and the gate is re-read on them. The structure is
worth noting — selecting probes whose author has an equal-count partner
collapses the frequency shortcut from 34.6% to 18.1% by construction, while
turn-taking rises to 35.3%, so the arm is gated on a harder heuristic than the
main design. **The binding index remains unsettled**, and a bigger arm alone
will not settle it.

### The 32B Supreme run dies mid-sweep, reproducibly

`qwen2.5:14b` on Supreme Court is **complete**: 5,562 rows, paired n = 1,200.

`qwen2.5:32b` is **not**. Its manifest still reads `running` at 5,200 rows,
paired n = 1,095. It was resumed twice onto fresh pods — the dataset hashes
identically (`2e3d0f5318af…`), so finished rows are skipped correctly — and it
died mid-sweep each time, at 1,047 and then 1,097 probes.

The failure has no error trail: 2 reader errors in 5,200 rows, both
`TimeoutError` at exactly the client's 180 s cap, both at budget 1.0, and
latencies in the final rows are ordinary (1.93, 0.90, 1.21 s) right up to the
last one written. An abrupt stop with no exception and no slow-down is
consistent with the process being **killed from outside — most likely OOM** —
rather than crashing. `plan()` materialises every rendered job up front, and
Supreme Court's 20-turn windows of 62.7-word turns are by far the largest text
this instrument has held. That is a hypothesis, not a diagnosis: the pod was
terminated before it could be confirmed, and confirming it needs a run with
memory instrumentation.

**The estimate is still valid at its stated n.** Probe order is a deterministic
shuffle, so an interrupted run leaves a random, fully paired subsample rather
than a biased prefix — a designed property of the runner. Reporting it needs
the n stated and the `running` status disclosed, which is what this section
does. The conclusion does not turn on the missing 105 probes: −36.9 pts
[−40.4, −33.3] is not a result that 9% more data overturns.

**For the next session:** before re-running 32B on Supreme Court, either stream
the job list instead of materialising it, or run with a memory limit and a
`dmesg` check so the kill is confirmed rather than inferred.

## Results, LLM-summary compressor (2026-10-05)

`qwen2.5:7b` wrote the summaries, `qwen2.5:14b` read them, on the same 1,200
frozen probes and the same budgets. Registered under *Deviations* above.
36,501 summaries generated, **17,704 of them (48.5%) clipped** to their word
budget.

- **Headroom gate: PASS.** 40.5% [37.2, 43.8], lift +12.9 pts [+9.7, +16.2].
  At budget 1.0 this compressor is the identity, so this is the same text the
  word-drop run showed the same reader, and **40.5% against that run's 40.4%
  is an internal consistency check** — the 0.1 pt gap is Ollama's
  non-determinism at temperature 0.
- **Primary outcome** (paired 1.0 → 0.1): **−7.9 pts [−11.3, −4.5]**,
  245 lost / 150 gained, McNemar p = 2.0 × 10⁻⁶. Reading: **effect**.
- **Secondary outcomes.** −5.2 pts [−8.3, −2.2] at 0.5 and −8.5 pts
  [−11.5, −5.4] at 0.25; both effects. Accuracy is flat from 0.25 to 0.1
  (32.0%, 32.6%), both at or below the 34.6% frequency shortcut.
- **Label swap**, 278 probes: +6.5 pts [−2.6, +15.9] uncompressed, decaying to
  +0.4 pts [−8.1, +8.2] at 0.1. Inconclusive, as in both word-drop arms.

### The budgets are only matched at 1.0 and 0.1

The two compressors were designed to share one word rule, but the summarizer
undershoots it: `cap_words` clips a summary that runs long and nothing pads one
that comes in short, and a 7B model asked for "at most k words" often returns
fewer.

| Budget | Word-drop, realised | Summary, realised |
| ---: | ---: | ---: |
| 1.0 | 28.4 | 28.4 |
| 0.5 | 14.2 | **9.0** |
| 0.25 | 7.1 | **5.8** |
| 0.1 | 2.9 | **2.7** |

So the two arms are **not** comparable at 0.5 and 0.25 — the summary arm
compressed 37% and 18% harder than nominal there, and its larger loss at those
budgets is partly just less text.

**The comparison that holds is at budget 0.1**, where realised length is 2.7
words against 2.9. There, the same reader loses **−9.2 pts [−12.3, −6.0]** to
word-dropping and **−7.9 pts [−11.3, −4.5]** to LLM summarisation. The
intervals overlap heavily, so this design detects no difference between the two
compressors at matched realised length: **a realistic LLM summarizer destroys
who-said-what about as much as naive word-dropping**, which is the practically
important version of the claim.

Reporting this as "matched word budgets" at 0.5 and 0.25 would overstate the
design. Fixing it properly needs a length-targeted summarizer (resample until
the summary lands within a tolerance of k), which is a change to the
instrument, not an analysis choice.

- **Errors and exclusions:** no reader errors, no invalid answers, 100% valid
  across 5,634 rows.
- **Provenance:** git `86f2200`; `qwen2.5:14b` digest `7cdf5a0187d5`;
  summarizer `qwen2.5:7b`; AMI sha256 `f15cc2fa6db2…`; Python 3.13.12,
  `PYTHONHASHSEED=0`.

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
