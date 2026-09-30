# Table 3: Failure-Mode Decomposition (pilot)

- Memory budget: 10% of full-context words (matched across systems).
- Retrieval: BM25, top-5; formation threshold tau=0.65.
- Memory unit: 1 message(s); compressor: salient.
- Graded questions: 98 of 185 evidence-linked (questions whose answer is not recoverable from gold evidence even at full fidelity are excluded, so the table measures the memory system rather than the evidence labels).

Buckets are mutually exclusive and assigned in order. Splitting `answer visible` into `correct` and `retrieved but misinterpreted` requires a reader model; see docs/FAILURE_DECOMPOSITION.md.

## ALL (n=98)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 80.6 | 16.3 | 3.1 |
| recency_window | 87.8 | 7.1 | 5.1 |
| speaker_partitioned_memory | 88.8 | 7.1 | 4.1 |
| amac_global_utility | 85.7 | 9.2 | 5.1 |
| oracle_future_consumer | 31.6 | 27.6 | 40.8 |

## knowledge_update (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 100.0 | 0.0 | 0.0 |
| recency_window | 95.2 | 0.0 | 4.8 |
| speaker_partitioned_memory | 100.0 | 0.0 | 0.0 |
| amac_global_utility | 95.2 | 0.0 | 4.8 |
| oracle_future_consumer | 28.6 | 23.8 | 47.6 |

## multi_hop (n=37)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 67.6 | 27.0 | 5.4 |
| recency_window | 81.1 | 8.1 | 10.8 |
| speaker_partitioned_memory | 81.1 | 8.1 | 10.8 |
| amac_global_utility | 83.8 | 10.8 | 5.4 |
| oracle_future_consumer | 18.9 | 21.6 | 59.5 |

## temporal (n=6)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 50.0 | 33.3 | 16.7 |
| recency_window | 100.0 | 0.0 | 0.0 |
| speaker_partitioned_memory | 100.0 | 0.0 | 0.0 |
| amac_global_utility | 100.0 | 0.0 | 0.0 |
| oracle_future_consumer | 16.7 | 66.7 | 16.7 |

## term_ambiguity (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 81.0 | 19.0 | 0.0 |
| recency_window | 81.0 | 19.0 | 0.0 |
| speaker_partitioned_memory | 81.0 | 19.0 | 0.0 |
| amac_global_utility | 66.7 | 23.8 | 9.5 |
| oracle_future_consumer | 23.8 | 47.6 | 28.6 |

## user_implicit (n=13)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 100.0 | 0.0 | 0.0 |
| recency_window | 100.0 | 0.0 | 0.0 |
| speaker_partitioned_memory | 100.0 | 0.0 | 0.0 |
| amac_global_utility | 100.0 | 0.0 | 0.0 |
| oracle_future_consumer | 92.3 | 0.0 | 7.7 |
