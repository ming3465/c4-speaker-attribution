# Table 3: Failure-Mode Decomposition (pilot)

- Memory budget: 100% of full-context words (matched across systems).
- Retrieval: BM25, top-5; formation threshold tau=0.65.
- Memory unit: 1 message(s); compressor: salient.
- Graded questions: 98 of 185 evidence-linked (questions whose answer is not recoverable from gold evidence even at full fidelity are excluded, so the table measures the memory system rather than the evidence labels).

Buckets are mutually exclusive and assigned in order. Splitting `answer visible` into `correct` and `retrieved but misinterpreted` requires a reader model; see docs/FAILURE_DECOMPOSITION.md.

## ALL (n=98)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 0.0 | 43.9 | 56.1 |
| recency_window | 0.0 | 43.9 | 56.1 |
| speaker_partitioned_memory | 0.0 | 43.9 | 56.1 |
| amac_global_utility | 0.0 | 43.9 | 56.1 |
| oracle_future_consumer | 0.0 | 43.9 | 56.1 |

## knowledge_update (n=21)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 0.0 | 38.1 | 61.9 |
| recency_window | 0.0 | 38.1 | 61.9 |
| speaker_partitioned_memory | 0.0 | 38.1 | 61.9 |
| amac_global_utility | 0.0 | 38.1 | 61.9 |
| oracle_future_consumer | 0.0 | 38.1 | 61.9 |

## multi_hop (n=37)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 0.0 | 32.4 | 67.6 |
| recency_window | 0.0 | 32.4 | 67.6 |
| speaker_partitioned_memory | 0.0 | 32.4 | 67.6 |
| amac_global_utility | 0.0 | 32.4 | 67.6 |
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
| uniform_compression | 0.0 | 76.2 | 23.8 |
| recency_window | 0.0 | 76.2 | 23.8 |
| speaker_partitioned_memory | 0.0 | 76.2 | 23.8 |
| amac_global_utility | 0.0 | 76.2 | 23.8 |
| oracle_future_consumer | 0.0 | 76.2 | 23.8 |

## user_implicit (n=13)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 0.0 | 15.4 | 84.6 |
| recency_window | 0.0 | 15.4 | 84.6 |
| speaker_partitioned_memory | 0.0 | 15.4 | 84.6 |
| amac_global_utility | 0.0 | 15.4 | 84.6 |
| oracle_future_consumer | 0.0 | 15.4 | 84.6 |
