# Table 3: Failure-Mode Decomposition (groupmembench / Finance)

- Memory budget: 10% of full-context words (matched across systems).
- Retrieval: BM25, top-5; formation threshold tau=0.65.
- Memory unit: 1 message(s); compressor: salient.
- Graded questions: 98 of 185 evidence-linked (questions whose answer is not recoverable from gold evidence even at full fidelity are excluded, so the table measures the memory system rather than the evidence labels).

Buckets are mutually exclusive and assigned in order. Splitting `answer visible` into `correct` and `retrieved but misinterpreted` requires a reader model; see docs/FAILURE_DECOMPOSITION.md.

## ALL (n=98)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 77.6 | 20.4 | 2.0 |
| recency_window | 85.7 | 12.2 | 2.0 |
| speaker_partitioned_memory | 86.7 | 12.2 | 1.0 |
| amac_global_utility | 82.7 | 15.3 | 2.0 |
| oracle_future_consumer | 0.0 | 82.7 | 17.3 |

## knowledge_update (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 100.0 | 0.0 | 0.0 |
| recency_window | 95.2 | 4.8 | 0.0 |
| speaker_partitioned_memory | 95.2 | 4.8 | 0.0 |
| amac_global_utility | 90.5 | 9.5 | 0.0 |
| oracle_future_consumer | 0.0 | 90.5 | 9.5 |

## multi_hop (n=37)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 59.5 | 35.1 | 5.4 |
| recency_window | 75.7 | 18.9 | 5.4 |
| speaker_partitioned_memory | 78.4 | 18.9 | 2.7 |
| amac_global_utility | 78.4 | 18.9 | 2.7 |
| oracle_future_consumer | 0.0 | 73.0 | 27.0 |

## temporal (n=6)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 50.0 | 50.0 | 0.0 |
| recency_window | 100.0 | 0.0 | 0.0 |
| speaker_partitioned_memory | 100.0 | 0.0 | 0.0 |
| amac_global_utility | 100.0 | 0.0 | 0.0 |
| oracle_future_consumer | 0.0 | 100.0 | 0.0 |

## term_ambiguity (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 81.0 | 19.0 | 0.0 |
| recency_window | 81.0 | 19.0 | 0.0 |
| speaker_partitioned_memory | 81.0 | 19.0 | 0.0 |
| amac_global_utility | 66.7 | 28.6 | 4.8 |
| oracle_future_consumer | 0.0 | 90.5 | 9.5 |

## user_implicit (n=13)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 100.0 | 0.0 | 0.0 |
| recency_window | 100.0 | 0.0 | 0.0 |
| speaker_partitioned_memory | 100.0 | 0.0 | 0.0 |
| amac_global_utility | 100.0 | 0.0 | 0.0 |
| oracle_future_consumer | 0.0 | 76.9 | 23.1 |
