# Data

Not all data is in this repository. Every corpus below is downloaded and
converted locally by a script in `scripts/data/`; the converted output is
gitignored and never pushed.

## Corpora used by the C4 attribution study

| Corpus | Licence | Redistributable here? |
| --- | --- | --- |
| AMI Meeting Corpus | CC BY 4.0 | no (kept local; 23 MB) |
| ICSI Meeting Corpus | CC BY 4.0 | no (kept local; 19 MB) |
| ELITR Minuting Corpus | CC BY-NC-SA 4.0 | no — **non-commercial**, share-alike |
| Supreme Court Oral Arguments | none stated | no — see the note below |
| GroupMemBench / SocialMemBench | none stated | no |

### AMI Meeting Corpus (CC BY 4.0)

Manual annotations v1.6.2, NXT format.

```bash
curl -LO https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
unzip ami_public_manual_1.6.2.zip -d data/raw/ami
python scripts/data/convert_ami.py        # 171 meetings, 83,868 utterances
```

The converted `data/processed/ami.jsonl` has sha256
`f15cc2fa6db2ca488a159f87e67b0b51228f5ecc20fd2383ac76e61dcc5986f1`, recorded in
`docs/C4_ANALYSIS_PLAN.md`. The main result depends on it, so the converter's
output must not change.

### ICSI Meeting Corpus (CC BY 4.0)

Same NXT tooling as AMI, from the same Edinburgh group. The licence text ships
inside the zip as `ICSI/LICENCE.txt`. 75 meetings with **3–10 speakers each**,
a wider range than AMI's 4.

```bash
curl -LO https://groups.inf.ed.ac.uk/ami/ICSICorpusAnnotations/ICSI_core_NXT.zip
unzip ICSI_core_NXT.zip -d data/raw/icsi
python scripts/data/convert_icsi.py
```

### ELITR Minuting Corpus (CC BY-NC-SA 4.0)

LINDAT/CLARIAH-CZ, handle `11234/1-4692`. English meetings only. Speakers are
already anonymised in the source as `PERSONnn`.

**The handle's old XMLUI bitstream URL is dead** — LINDAT migrated to DSpace 7
and `/repository/xmlui/bitstream/...` now serves an Angular shell. Resolve the
current URL through the REST API:

```bash
curl -s "https://lindat.mff.cuni.cz/repository/server/api/pid/find?id=hdl:11234/1-4692"
# -> item uuid 8594c726-8ea4-476e-8c66-e9afb85b06e0, then walk bundles -> bitstreams
curl -LO https://lindat.mff.cuni.cz/repository/server/api/core/bitstreams/76466f35-1bac-47bf-958b-c235b1fb4966/content
python scripts/data/convert_elitr.py
```

Non-commercial and share-alike. Academic use only, and derived text must not be
redistributed under a more permissive licence.

### Supreme Court Oral Arguments (no stated licence)

Cornell's ConvoKit corpus, transcripts scraped from Oyez, voting data from the
Supreme Court Database. Used here as the high-signal corpus: oral arguments are
long multi-party sessions, so 20-turn windows apply unchanged.

**Licence status, checked 2026-09-30.** ConvoKit's page for this corpus has no
"Data License" section, unlike several of its other corpora. Oyez's own licence
page renders only in JavaScript and could not be read programmatically. The
underlying oral-argument transcripts are US federal court records, but the Oyez
transcription and alignment are a separate work whose terms are not stated.

Treated as research-use-only: downloaded, converted and read locally, never
redistributed, and the processed output is gitignored — the same handling
`GroupMemBench` gets. Do not publish the transcripts or any derivative that
reproduces them.

```bash
python scripts/data/convert_supreme.py --years 2019 2020 2021
```

Per-year zips are ~7 MB each from
`https://zissou.infosci.cornell.edu/convokit/datasets/supreme-corpus/supreme-<year>.zip`.
Speaker names in the source are real (`j__john_g_roberts_jr`); the converter
anonymises them to `Speaker_<letter>` per conversation, because the study's
design never shows the reader a name.

### GroupMemBench and SocialMemBench (no stated licence)

[UCSB-NLP-Chang/GroupMemBench](https://github.com/UCSB-NLP-Chang/GroupMemBench)
and SocialMemBench samples. No redistribution licence, so the pilot bundle
(`data/pilot/c4/`) and the processed samples are kept out of git. Rebuild them
from the original repositories with the scripts in `scripts/data/`. The tests
that need the pilot bundle skip when it is absent.
