# Data

Not all data is in this repository.

- **AMI Meeting Corpus** (CC BY 4.0): download and convert as described in
  `docs/C4_RUNBOOK.md` (`scripts/data/convert_ami.py`).
- **GroupMemBench** ([UCSB-NLP-Chang/GroupMemBench](https://github.com/UCSB-NLP-Chang/GroupMemBench))
  and **SocialMemBench** samples: these have no redistribution licence, so the
  pilot bundle (`data/pilot/c4/`) and the processed samples are kept out of
  git. Rebuild them from the original repositories with the scripts in
  `scripts/data/`. The tests that need the pilot bundle skip when it is absent.
