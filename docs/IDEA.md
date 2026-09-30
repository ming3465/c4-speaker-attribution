# Idea

## One-Sentence Proposal

Build a long-term memory mechanism for multi-party LLM agents that predicts who will need each memory later, allocates compression fidelity accordingly, and uses source provenance at read time to interpret retrieved memories correctly.

## Motivation

Long-context LLM agents need to retain earlier information without keeping the entire conversation in the active KV cache. Existing memory approaches often rely on retrieval, summarization, or compressed recurrent memory, but they usually decide what remains available using relatively fixed policies such as recency or global importance.

This is especially weak in multi-party conversations because information has structure beyond text. The same term can mean different things depending on who said it, what role they occupy, and who later needs the information. If the memory system compresses a group conversation into anonymous content, it may retain words while losing the speaker and role evidence needed for correct interpretation.

GroupMemBench motivates the proposal by showing that multi-party memory failures can happen at different stages: a system can lose speaker identity or key information during memory creation, or it can retrieve correct evidence and still interpret it incorrectly.

The proposal also draws an analogy from human memory: predicted future utility can lead to higher-fidelity retention. The project extends this principle from "will this information be needed?" to "who is likely to need this information?"

## Core Thesis

Memory writing should be predictive rather than reactive. At write time, a lightweight controller predicts which future participants are likely to require a piece of information. The system then stores one compressed memory unit with:

- A shared semantic core accessible to any reader.
- Optional role-conditioned residual detail preserved for participant roles predicted to need higher fidelity later.
- Explicit source speaker and role metadata, so provenance is not compressed away.

At read time, the system retrieves relevant memories, decodes the appropriate level of detail for the current querying participant, and optionally applies provenance-conditioned interpretation if the retrieved evidence depends on who originally produced it.

## Research Question

Can an LLM agent achieve more accurate long-term memory in multi-party conversations, at equal or lower memory and inference cost than existing approaches, by:

1. Predicting which future participant roles will need a piece of information and allocating compression fidelity accordingly at write time.
2. Conditioning interpretation of retrieved memories on the role and provenance of the person who produced them at read time.

## Hypotheses

- Future-consumer-aware fidelity allocation should produce a better accuracy-memory tradeoff than compression based only on recency, global future utility, anticipated future questions, or the identity of the original speaker.
- Preserving speaker and role provenance through compression should reduce speaker-attribution failures in multi-party memory.
- Provenance-conditioned interpretation should reduce cases where correct evidence is retrieved but misunderstood because its meaning depends on speaker role or context.
- The full system should improve the accuracy-memory and accuracy-latency Pareto frontier, especially on GroupMemBench categories involving knowledge updates, term ambiguity, and speaker-grounded reasoning.

## Main Contributions

### Predicted-Consumer-Aware Memory Compression

Instead of assigning a single compressed representation based only on source speaker or semantic importance, the system predicts which participants are likely to require the information in future interactions. It then allocates fidelity according to predicted future demand while preserving a shared semantic core.

This is the central novelty. The proposal should avoid claiming novelty for adaptive memory routing alone, speaker-indexed memory alone, or activation steering alone, because related work already covers those pieces.

### Shared Core With Role-Conditioned Residual Detail

Each memory unit keeps one shared, role-agnostic summary for all future readers and extra fine detail only for participant roles likely to need it. This differs from systems that place each person's information in a separate isolated memory store.

### Provenance-Conditioned Memory Interpretation

The read-time system uses retrieved memory, source provenance, and current query context to decide whether meaning depends on who produced the memory. If so, a small library of interpretation vectors can steer the model toward the correct semantic interpretation. The objective is not roleplay; it is evidence-sensitive interpretation.

### Unified Failure-Mode Analysis

The evaluation should distinguish between:

- Memory-formation failure: required information or provenance was lost during write-time allocation, compression, summarization, or storage.
- Retrieval failure: required information still exists but is not retrieved or ranked highly enough.
- Interpretation failure: correct evidence and provenance are retrieved, but the answer is wrong because the evidence is interpreted incorrectly.

This decomposition makes it possible to identify which component is responsible for any improvement.
