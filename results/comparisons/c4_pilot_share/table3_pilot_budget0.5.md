# Table 3: Failure-Mode Decomposition (pilot)

- Memory budget: 50% of full-context words (matched across systems).
- Retrieval: BM25, top-5; formation threshold tau=0.65.
- Memory unit: 1 message(s); compressor: salient.
- Graded questions: 98 of 185 evidence-linked (questions whose answer is not recoverable from gold evidence even at full fidelity are excluded, so the table measures the memory system rather than the evidence labels).

Buckets are mutually exclusive and assigned in order. Splitting `answer visible` into `correct` and `retrieved but misinterpreted` requires a reader model; see docs/FAILURE_DECOMPOSITION.md.

## ALL (n=98)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 40.8 | 32.7 | 26.5 |
| recency_window | 44.9 | 29.6 | 25.5 |
| speaker_partitioned_memory | 46.9 | 29.6 | 23.5 |
| amac_global_utility | 39.8 | 35.7 | 24.5 |
| oracle_future_consumer | 0.0 | 41.8 | 58.2 |

## knowledge_update (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 100.0 | 0.0 | 0.0 |
| recency_window | 66.7 | 14.3 | 19.0 |
| speaker_partitioned_memory | 76.2 | 14.3 | 9.5 |
| amac_global_utility | 57.1 | 28.6 | 14.3 |
| oracle_future_consumer | 0.0 | 42.9 | 57.1 |

## multi_hop (n=37)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 21.6 | 29.7 | 48.6 |
| recency_window | 32.4 | 32.4 | 35.1 |
| speaker_partitioned_memory | 32.4 | 32.4 | 35.1 |
| amac_global_utility | 29.7 | 35.1 | 35.1 |
| oracle_future_consumer | 0.0 | 32.4 | 67.6 |

## temporal (n=6)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 0.0 | 83.3 | 16.7 |
| recency_window | 0.0 | 83.3 | 16.7 |
| speaker_partitioned_memory | 0.0 | 83.3 | 16.7 |
| amac_global_utility | 0.0 | 83.3 | 16.7 |
| oracle_future_consumer | 0.0 | 83.3 | 16.7 |

## term_ambiguity (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 14.3 | 66.7 | 19.0 |
| recency_window | 42.9 | 38.1 | 19.0 |
| speaker_partitioned_memory | 42.9 | 38.1 | 19.0 |
| amac_global_utility | 19.0 | 52.4 | 28.6 |
| oracle_future_consumer | 0.0 | 66.7 | 33.3 |

## user_implicit (n=13)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 61.5 | 15.4 | 23.1 |
| recency_window | 69.2 | 7.7 | 23.1 |
| speaker_partitioned_memory | 69.2 | 7.7 | 23.1 |
| amac_global_utility | 92.3 | 0.0 | 7.7 |
| oracle_future_consumer | 0.0 | 7.7 | 92.3 |
