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
