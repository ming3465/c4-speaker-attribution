# Table 3: Failure-Mode Decomposition (pilot)

- Memory budget: 25% of full-context words (matched across systems).
- Retrieval: BM25, top-5; formation threshold tau=0.65.
- Memory unit: 1 message(s); compressor: salient.
- Graded questions: 98 of 185 evidence-linked (questions whose answer is not recoverable from gold evidence even at full fidelity are excluded, so the table measures the memory system rather than the evidence labels).

Buckets are mutually exclusive and assigned in order. Splitting `answer visible` into `correct` and `retrieved but misinterpreted` requires a reader model; see docs/FAILURE_DECOMPOSITION.md.

## ALL (n=98)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 60.2 | 27.6 | 12.2 |
| recency_window | 67.3 | 19.4 | 13.3 |
| speaker_partitioned_memory | 66.3 | 21.4 | 12.2 |
| amac_global_utility | 64.3 | 24.5 | 11.2 |
| oracle_future_consumer | 0.0 | 43.9 | 56.1 |

## knowledge_update (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 100.0 | 0.0 | 0.0 |
| recency_window | 81.0 | 14.3 | 4.8 |
| speaker_partitioned_memory | 81.0 | 14.3 | 4.8 |
| amac_global_utility | 81.0 | 9.5 | 9.5 |
| oracle_future_consumer | 0.0 | 52.4 | 47.6 |

## multi_hop (n=37)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 40.5 | 37.8 | 21.6 |
| recency_window | 54.1 | 24.3 | 21.6 |
| speaker_partitioned_memory | 51.4 | 29.7 | 18.9 |
| amac_global_utility | 54.1 | 29.7 | 16.2 |
| oracle_future_consumer | 0.0 | 32.4 | 67.6 |

## temporal (n=6)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 0.0 | 83.3 | 16.7 |
| recency_window | 50.0 | 33.3 | 16.7 |
| speaker_partitioned_memory | 50.0 | 33.3 | 16.7 |
| amac_global_utility | 50.0 | 33.3 | 16.7 |
| oracle_future_consumer | 0.0 | 83.3 | 16.7 |

## term_ambiguity (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 47.6 | 38.1 | 14.3 |
| recency_window | 71.4 | 23.8 | 4.8 |
| speaker_partitioned_memory | 71.4 | 23.8 | 4.8 |
| amac_global_utility | 47.6 | 42.9 | 9.5 |
| oracle_future_consumer | 0.0 | 66.7 | 33.3 |

## user_implicit (n=13)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 100.0 | 0.0 | 0.0 |
| recency_window | 84.6 | 0.0 | 15.4 |
| speaker_partitioned_memory | 84.6 | 0.0 | 15.4 |
| amac_global_utility | 100.0 | 0.0 | 0.0 |
| oracle_future_consumer | 0.0 | 7.7 | 92.3 |
