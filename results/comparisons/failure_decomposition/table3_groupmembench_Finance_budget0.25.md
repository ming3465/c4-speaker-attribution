# Table 3: Failure-Mode Decomposition (groupmembench / Finance)

- Memory budget: 25% of full-context words (matched across systems).
- Retrieval: BM25, top-5; formation threshold tau=0.65.
- Memory unit: 1 message(s); compressor: salient.
- Graded questions: 98 of 185 evidence-linked (questions whose answer is not recoverable from gold evidence even at full fidelity are excluded, so the table measures the memory system rather than the evidence labels).

Buckets are mutually exclusive and assigned in order. Splitting `answer visible` into `correct` and `retrieved but misinterpreted` requires a reader model; see docs/FAILURE_DECOMPOSITION.md.

## ALL (n=98)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 60.2 | 33.7 | 6.1 |
| recency_window | 65.3 | 26.5 | 8.2 |
| speaker_partitioned_memory | 64.3 | 26.5 | 9.2 |
| amac_global_utility | 60.2 | 33.7 | 6.1 |
| oracle_future_consumer | 0.0 | 68.4 | 31.6 |

## knowledge_update (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 100.0 | 0.0 | 0.0 |
| recency_window | 81.0 | 14.3 | 4.8 |
| speaker_partitioned_memory | 81.0 | 14.3 | 4.8 |
| amac_global_utility | 76.2 | 23.8 | 0.0 |
| oracle_future_consumer | 0.0 | 90.5 | 9.5 |

## multi_hop (n=37)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 40.5 | 45.9 | 13.5 |
| recency_window | 48.6 | 35.1 | 16.2 |
| speaker_partitioned_memory | 45.9 | 37.8 | 16.2 |
| amac_global_utility | 48.6 | 37.8 | 13.5 |
| oracle_future_consumer | 0.0 | 54.1 | 45.9 |

## temporal (n=6)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 0.0 | 100.0 | 0.0 |
| recency_window | 50.0 | 50.0 | 0.0 |
| speaker_partitioned_memory | 50.0 | 33.3 | 16.7 |
| amac_global_utility | 50.0 | 50.0 | 0.0 |
| oracle_future_consumer | 0.0 | 100.0 | 0.0 |

## term_ambiguity (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 47.6 | 47.6 | 4.8 |
| recency_window | 71.4 | 28.6 | 0.0 |
| speaker_partitioned_memory | 71.4 | 28.6 | 0.0 |
| amac_global_utility | 42.9 | 52.4 | 4.8 |
| oracle_future_consumer | 0.0 | 81.0 | 19.0 |

## user_implicit (n=13)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 100.0 | 0.0 | 0.0 |
| recency_window | 84.6 | 7.7 | 7.7 |
| speaker_partitioned_memory | 84.6 | 7.7 | 7.7 |
| amac_global_utility | 100.0 | 0.0 | 0.0 |
| oracle_future_consumer | 0.0 | 38.5 | 61.5 |
