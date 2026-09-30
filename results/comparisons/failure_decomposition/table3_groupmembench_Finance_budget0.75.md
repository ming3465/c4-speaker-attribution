# Table 3: Failure-Mode Decomposition (groupmembench / Finance)

- Memory budget: 75% of full-context words (matched across systems).
- Retrieval: BM25, top-5; formation threshold tau=0.65.
- Memory unit: 1 message(s); compressor: salient.
- Graded questions: 98 of 185 evidence-linked (questions whose answer is not recoverable from gold evidence even at full fidelity are excluded, so the table measures the memory system rather than the evidence labels).

Buckets are mutually exclusive and assigned in order. Splitting `answer visible` into `correct` and `retrieved but misinterpreted` requires a reader model; see docs/FAILURE_DECOMPOSITION.md.

## ALL (n=98)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 20.4 | 54.1 | 25.5 |
| recency_window | 19.4 | 61.2 | 19.4 |
| speaker_partitioned_memory | 19.4 | 62.2 | 18.4 |
| amac_global_utility | 12.2 | 68.4 | 19.4 |
| oracle_future_consumer | 0.0 | 69.4 | 30.6 |

## knowledge_update (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 76.2 | 14.3 | 9.5 |
| recency_window | 47.6 | 47.6 | 4.8 |
| speaker_partitioned_memory | 47.6 | 47.6 | 4.8 |
| amac_global_utility | 0.0 | 85.7 | 14.3 |
| oracle_future_consumer | 0.0 | 81.0 | 19.0 |

## multi_hop (n=37)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 2.7 | 59.5 | 37.8 |
| recency_window | 18.9 | 56.8 | 24.3 |
| speaker_partitioned_memory | 18.9 | 59.5 | 21.6 |
| amac_global_utility | 10.8 | 56.8 | 32.4 |
| oracle_future_consumer | 0.0 | 54.1 | 45.9 |

## temporal (n=6)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 0.0 | 83.3 | 16.7 |
| recency_window | 0.0 | 83.3 | 16.7 |
| speaker_partitioned_memory | 0.0 | 83.3 | 16.7 |
| amac_global_utility | 0.0 | 100.0 | 0.0 |
| oracle_future_consumer | 0.0 | 100.0 | 0.0 |

## term_ambiguity (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 0.0 | 81.0 | 19.0 |
| recency_window | 0.0 | 85.7 | 14.3 |
| speaker_partitioned_memory | 0.0 | 85.7 | 14.3 |
| amac_global_utility | 0.0 | 85.7 | 14.3 |
| oracle_future_consumer | 0.0 | 85.7 | 14.3 |

## user_implicit (n=13)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 23.1 | 46.2 | 30.8 |
| recency_window | 15.4 | 46.2 | 38.5 |
| speaker_partitioned_memory | 15.4 | 46.2 | 38.5 |
| amac_global_utility | 61.5 | 30.8 | 7.7 |
| oracle_future_consumer | 0.0 | 53.8 | 46.2 |
