# Table 3: Failure-Mode Decomposition (pilot)

- Memory budget: 75% of full-context words (matched across systems).
- Retrieval: BM25, top-5; formation threshold tau=0.65.
- Memory unit: 1 message(s); compressor: salient.
- Graded questions: 98 of 185 evidence-linked (questions whose answer is not recoverable from gold evidence even at full fidelity are excluded, so the table measures the memory system rather than the evidence labels).

Buckets are mutually exclusive and assigned in order. Splitting `answer visible` into `correct` and `retrieved but misinterpreted` requires a reader model; see docs/FAILURE_DECOMPOSITION.md.

## ALL (n=98)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 20.4 | 33.7 | 45.9 |
| recency_window | 22.4 | 37.8 | 39.8 |
| speaker_partitioned_memory | 24.5 | 36.7 | 38.8 |
| amac_global_utility | 11.2 | 45.9 | 42.9 |
| oracle_future_consumer | 0.0 | 42.9 | 57.1 |

## knowledge_update (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 76.2 | 9.5 | 14.3 |
| recency_window | 47.6 | 23.8 | 28.6 |
| speaker_partitioned_memory | 47.6 | 23.8 | 28.6 |
| amac_global_utility | 0.0 | 42.9 | 57.1 |
| oracle_future_consumer | 0.0 | 42.9 | 57.1 |

## multi_hop (n=37)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 2.7 | 27.0 | 70.3 |
| recency_window | 18.9 | 32.4 | 48.6 |
| speaker_partitioned_memory | 18.9 | 32.4 | 48.6 |
| amac_global_utility | 8.1 | 37.8 | 54.1 |
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
| uniform_compression | 0.0 | 71.4 | 28.6 |
| recency_window | 14.3 | 57.1 | 28.6 |
| speaker_partitioned_memory | 23.8 | 52.4 | 23.8 |
| amac_global_utility | 0.0 | 71.4 | 28.6 |
| oracle_future_consumer | 0.0 | 66.7 | 33.3 |

## user_implicit (n=13)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 23.1 | 7.7 | 69.2 |
| recency_window | 15.4 | 23.1 | 61.5 |
| speaker_partitioned_memory | 15.4 | 23.1 | 61.5 |
| amac_global_utility | 61.5 | 15.4 | 23.1 |
| oracle_future_consumer | 0.0 | 15.4 | 84.6 |
