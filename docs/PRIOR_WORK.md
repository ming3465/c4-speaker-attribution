# Prior Work

## RISER

RISER proposes a lightweight router that dynamically selects and combines activation-steering vectors according to task requirements. It supports the routing principle: a small controller can compose internal model behaviors without retraining the whole model.

Relevance:

- Useful precedent for lightweight dynamic routing.
- Useful precedent for selecting and combining steering vectors.
- Not a memory-management system.

Limitation for this proposal:

- RISER routes over reasoning skills, not memory operations.
- It does not decide whether to retain, compress, retrieve, refresh, or discard information.
- It does not address long-context memory or multi-party speaker structure.

## Artificial Hippocampus Network (AHN)

AHN separates short-term and long-term memory. Recent information remains in the normal Transformer KV cache, while information leaving the attention window is compressed into a fixed-size recurrent state.

Relevance:

- Main architectural long-context baseline.
- Practical starting point because AHN demonstrates compressed recurrent memory with Qwen2.5-3B-Instruct.
- Provides evidence that compressed recurrent memory can reduce memory and inference cost while retaining useful long-context information.

Limitation for this proposal:

- AHN largely uses a fixed temporal rule for compression.
- Information enters compressed memory because it leaves the attention window, not because the system predicts who will need it later.
- AHN does not explicitly preserve speaker identity as a separate memory structure.

## GroupMemBench

GroupMemBench evaluates LLM agent memory in multi-party conversations. It covers multi-hop reasoning, knowledge updates, term ambiguity, temporal reasoning, and speaker-grounded understanding.

Relevance:

- Primary benchmark for this project.
- Strong evidence that speaker identity, group structure, and role-dependent interpretation matter.
- Motivates the failure decomposition between ingestion, retrieval, and interpretation.

Limitation for this proposal:

- It diagnoses multi-party memory failures but does not provide a general architectural solution.

## LongMemEval

LongMemEval evaluates long-term conversational memory across extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention.

Relevance:

- Generalization benchmark beyond group conversations.
- Useful precedent for decomposing memory into indexing, retrieval, and reading stages.

Limitation for this proposal:

- It is not specifically designed around multi-party speaker structure or role-dependent meaning.

## LoCoMo

LoCoMo evaluates very long-term conversational memory using long conversations, QA, event summarization, and long-range temporal or causal dependencies.

Relevance:

- General long-term conversational-memory evaluation set.
- Tests whether the system handles distant conversational dependencies.

Limitation for this proposal:

- It does not directly test dynamic memory management or future-consumer-aware compression.

## AgentViSS

AgentViSS evaluates whether multimodal agents can convert observations about people into appropriate sequential interaction behavior.

Relevance:

- Supports the distinction between recognizing or retrieving information and using it correctly.
- Analogous to the proposal's interpretation problem: an LLM may retrieve correct evidence but still fail to interpret it according to speaker role or social context.

Limitation for this proposal:

- It is not directly a memory paper.

## AtomMem

AtomMem treats memory management as a dynamic decision-making problem and decomposes memory into atomic Create, Read, Update, and Delete operations. It trains a policy using supervised fine-tuning followed by reinforcement learning.

Relevance:

- Closest prior art to general dynamic CRUD-style memory routing.
- Important overlap warning: adaptive memory operation routing should be treated as prior work.

Limitation for this proposal:

- AtomMem manages globally useful memory.
- It does not use predicted future consumers as the target for fidelity allocation.

## Adaptive Memory Admission Control (A-MAC)

A-MAC scores candidate memories using predicted future utility, factual confidence, semantic novelty, temporal recency, and content type.

Relevance:

- Major baseline.
- Strong comparison because it already uses future utility as a write-time signal.

Limitation for this proposal:

- A-MAC estimates whether a memory is useful in general.
- It does not predict which specific participant will need the memory or allocate fidelity by future consumer.

## Collaborative Memory

Collaborative Memory proposes private user-specific memory and shared memory while preserving provenance such as contributing user and timestamp. Its access-control mechanism determines who may read or write memories.

Relevance:

- Important prior work for private/shared memory and provenance metadata.
- Should be included as a baseline.

Limitation for this proposal:

- It is mainly concerned with access permission, not predicted future need.
- The proposal's comparison is: "Who may access this memory?" versus "Who is likely to need this memory later, and how much detail should be preserved for them?"

## MuPPET

MuPPET has channels for agent identity or ownership, user-specific persistent memory, and shared group memory in a multi-party group chat setting.

Relevance:

- Close neighbor for multi-party memory structure.
- Reinforces that private/shared memory terminology and two-tier structures are not the novelty.

Limitation for this proposal:

- It does not implement a single shared compressed memory with adjustable future-consumer-specific detail.

## AFA

Adaptive Friend Agent combines speaker identification with per-user isolated memory stores to prevent persona confusion in shared multi-user settings.

Relevance:

- Prior work for routing to the correct speaker's memory store.

Limitation for this proposal:

- It lacks shared memory and compression.
- It does not predict future consumers.

## Other Close Neighbors

- WhenLoss: close because it predicts future questions, but it does not predict the future person who will need the memory.
- Adaptive Memory Structures / FluxMem: close because it selects among memory structures based on interaction-level features.
- SRPS and related role-vector work: show that roles can be represented as activation-space steering directions.
- DSEM and Neural Procedural Memory: show that memory or prior experience can dynamically retrieve or construct activation steering vectors.
- Sparse Latents Steer Retrieval-Augmented Generation: shows that activation interventions can modify how an LLM uses retrieved evidence.
- Continuous Interpretive Steering: shows that activation steering can causally alter linguistic interpretation.

## Novelty Boundary

The proposal should not claim novelty for:

- Adaptive compression in general.
- Dynamic memory operation routing in general.
- Speaker-indexed memory or private/shared memory in general.
- Role vectors or activation steering in general.
- Steering retrieved evidence in general.

The defensible novelty is the combination of:

- Write-time prediction of likely future consumers.
- Allocation of shared-core plus role-conditioned residual fidelity based on that prediction.
- Read-time provenance-conditioned interpretation for long-term conversational memories.
- Failure-mode decomposition that separates formation, retrieval, and interpretation errors.
