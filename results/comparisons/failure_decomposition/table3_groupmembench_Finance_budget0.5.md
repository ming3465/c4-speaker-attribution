# Table 3: Failure-Mode Decomposition (groupmembench / Finance)

- Memory budget: 50% of full-context words (matched across systems).
- Retrieval: BM25, top-5; formation threshold tau=0.65.
- Memory unit: 1 message(s); compressor: salient.
- Graded questions: 98 of 185 evidence-linked (questions whose answer is not recoverable from gold evidence even at full fidelity are excluded, so the table measures the memory system rather than the evidence labels).

Buckets are mutually exclusive and assigned in order. Splitting `answer visible` into `correct` and `retrieved but misinterpreted` requires a reader model; see docs/FAILURE_DECOMPOSITION.md.

## ALL (n=98)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 40.8 | 43.9 | 15.3 |
| recency_window | 43.9 | 42.9 | 13.3 |
| speaker_partitioned_memory | 44.9 | 40.8 | 14.3 |
| amac_global_utility | 38.8 | 50.0 | 11.2 |
| oracle_future_consumer | 0.0 | 66.3 | 33.7 |

## knowledge_update (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 100.0 | 0.0 | 0.0 |
| recency_window | 71.4 | 23.8 | 4.8 |
| speaker_partitioned_memory | 76.2 | 19.0 | 4.8 |
| amac_global_utility | 57.1 | 38.1 | 4.8 |
| oracle_future_consumer | 0.0 | 81.0 | 19.0 |

## multi_hop (n=37)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 21.6 | 54.1 | 24.3 |
| recency_window | 32.4 | 40.5 | 27.0 |
| speaker_partitioned_memory | 32.4 | 40.5 | 27.0 |
| amac_global_utility | 29.7 | 48.6 | 21.6 |
| oracle_future_consumer | 0.0 | 54.1 | 45.9 |

## temporal (n=6)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 0.0 | 83.3 | 16.7 |
| recency_window | 0.0 | 100.0 | 0.0 |
| speaker_partitioned_memory | 0.0 | 100.0 | 0.0 |
| amac_global_utility | 0.0 | 100.0 | 0.0 |
| oracle_future_consumer | 0.0 | 100.0 | 0.0 |

## term_ambiguity (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 14.3 | 71.4 | 14.3 |
| recency_window | 38.1 | 61.9 | 0.0 |
| speaker_partitioned_memory | 38.1 | 57.1 | 4.8 |
| amac_global_utility | 14.3 | 76.2 | 9.5 |
| oracle_future_consumer | 0.0 | 81.0 | 19.0 |

## user_implicit (n=13)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 61.5 | 23.1 | 15.4 |
| recency_window | 61.5 | 23.1 | 15.4 |
| speaker_partitioned_memory | 61.5 | 23.1 | 15.4 |
| amac_global_utility | 92.3 | 7.7 | 0.0 |
| oracle_future_consumer | 0.0 | 38.5 | 61.5 |
