# Table 3: Failure-Mode Decomposition (locomo)

- Memory budget: 25% of full-context words (matched across systems).
- Retrieval: BM25, top-5; formation threshold tau=0.65.
- Memory unit: 1 message(s); compressor: salient.
- Graded questions: 944 of 1977 evidence-linked (questions whose answer is not recoverable from gold evidence even at full fidelity are excluded, so the table measures the memory system rather than the evidence labels).

Buckets are mutually exclusive and assigned in order. Splitting `answer visible` into `correct` and `retrieved but misinterpreted` requires a reader model; see docs/FAILURE_DECOMPOSITION.md.

## ALL (n=944)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 57.3 | 33.6 | 9.1 |
| recency_window | 67.6 | 28.9 | 3.5 |
| speaker_partitioned_memory | 67.6 | 28.9 | 3.5 |
| amac_global_utility | 66.6 | 29.4 | 3.9 |
| oracle_future_consumer | 39.5 | 52.4 | 8.1 |

## adversarial (n=299)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 57.5 | 31.4 | 11.0 |
| recency_window | 67.9 | 27.8 | 4.3 |
| speaker_partitioned_memory | 67.9 | 27.8 | 4.3 |
| amac_global_utility | 67.2 | 28.8 | 4.0 |
| oracle_future_consumer | 39.8 | 50.8 | 9.4 |

## multi_hop (n=50)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 48.0 | 52.0 | 0.0 |
| recency_window | 54.0 | 44.0 | 2.0 |
| speaker_partitioned_memory | 54.0 | 44.0 | 2.0 |
| amac_global_utility | 52.0 | 46.0 | 2.0 |
| oracle_future_consumer | 28.0 | 70.0 | 2.0 |

## open_domain (n=5)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 40.0 | 60.0 | 0.0 |
| recency_window | 100.0 | 0.0 | 0.0 |
| speaker_partitioned_memory | 100.0 | 0.0 | 0.0 |
| amac_global_utility | 60.0 | 40.0 | 0.0 |
| oracle_future_consumer | 20.0 | 80.0 | 0.0 |

## single_hop (n=565)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 59.6 | 31.2 | 9.2 |
| recency_window | 69.2 | 27.6 | 3.2 |
| speaker_partitioned_memory | 69.2 | 27.6 | 3.2 |
| amac_global_utility | 68.7 | 27.3 | 4.1 |
| oracle_future_consumer | 41.1 | 50.8 | 8.1 |

## temporal (n=25)

| System | Lost at write time (%) | Not retrieved (%) | Answer visible to reader (%) |
| --- | ---: | ---: | ---: |
| uniform_compression | 24.0 | 72.0 | 4.0 |
| recency_window | 48.0 | 48.0 | 4.0 |
| speaker_partitioned_memory | 48.0 | 48.0 | 4.0 |
| amac_global_utility | 44.0 | 52.0 | 4.0 |
| oracle_future_consumer | 28.0 | 68.0 | 4.0 |
