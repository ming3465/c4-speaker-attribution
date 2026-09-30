# Method

## System Overview

The system starts with a normal Transformer-based LLM and an exact recent-context KV cache. Information inside the recent-context window remains uncompressed and fully attended to. When information leaves that window, it does not enter a single fixed compressed representation by default.

Instead, a lightweight write controller examines:

- Current hidden representation.
- Speaker identity.
- Speaker role.
- Conversation state.
- Uncertainty.
- Available memory budget.

It then predicts which future participants are likely to require the information and how much fidelity should be preserved for them under the budget.

## Memory Structure

The memory has two main components:

1. Exact recent-memory window.
2. Compressed long-term memory.

Each compressed long-term memory unit contains:

- Shared semantic core: compact role-agnostic summary accessible to any future reader.
- Role-conditioned residual detail: optional extra fidelity retained for participant roles predicted to need the information later.
- Source provenance metadata: original speaker identity and role.
- Predicted-consumer distribution: estimated likelihood that each participant will need the memory later.

This design intentionally avoids isolated per-speaker stores as the central mechanism. Group-relevant information receives broad low-residual retention across roles rather than being copied into a separate shared store.

## Future-Consumer Prediction

Before compression, the write controller predicts the probability that each current participant will require the candidate memory in a later interaction.

For candidate memory `m_t`, conversation history `H_t`, and participant `u_i`, the predictor estimates:

```text
p_{t,i} = P(u_i requires m_t in the future | m_t, H_t, u_i)
```

The participant's role is an input feature, not the prediction target. This lets the system distinguish between multiple participants with the same role while still generalizing across role patterns.

The prediction is multi-label, not single-choice. The same memory may be useful to multiple participants, so implementation should use independent sigmoid outputs for each memory-participant pair rather than a softmax over participants.

Prediction inputs include:

- Message or memory content.
- Speaker role.
- Conversation context.
- Whether the statement is a decision, commitment, technical detail, casual remark, update, conflict, or distractor.
- Patterns learned from synthetic data where future querying roles are known.

## Simple Predictor Implementation

The initial implementation can use a small pairwise MLP. The frozen base LLM provides representations of the candidate memory, recent conversation context, and candidate participant.

```python
class FutureConsumerPredictor(nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        self.scorer = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, memory_h, context_h, participant_h):
        interaction = memory_h * participant_h
        x = torch.cat(
            [
                memory_h,
                context_h,
                participant_h,
                interaction,
            ],
            dim=-1,
        )
        return self.scorer(x).squeeze(-1)
```

This version reduces each information source to a fixed-size representation, concatenates them, and predicts the probability that the participant will require the memory later.

## Attention-Based Predictor Alternative

The MLP may lose token-level distinctions. An alternative keeps memory, context, and participant information as token-level hidden-state matrices from the frozen base LLM.

Implementation sketch:

- Concatenate memory, context, and participant hidden states along the sequence dimension.
- Add type embeddings to mark which tokens belong to which source.
- Process the combined sequence with a shallow Transformer or other small attention network.
- Pool the resulting representation.
- Pass it through a sigmoid classification head.

The output remains the same: the probability that the candidate participant will need the memory in a future interaction.

## Write Controller

When a message or chunk leaves the exact context, the write controller uses the future-consumer prediction plus speaker role, conversation state, uncertainty, and memory budget to decide:

- Compression level of the shared semantic core.
- Which role-conditioned residual layers to retain.
- Which residual layers to expand.
- Which residual layers to drop.

The controller should be small, such as an MLP or shallow Transformer, so most computation remains with the frozen base LLM.

## Read Controller

When a new query arrives, the read controller retrieves relevant compressed memory units using:

- Semantic similarity.
- Speaker identity.
- Speaker role.
- Temporal information.

This allows the system to prefer memories associated with a particular speaker when a question explicitly or implicitly refers to that person.

After retrieval, the controller checks whether the current querying participant matches a role anticipated by the write-time predictor:

- If yes, decode the corresponding role-conditioned residual detail along with the shared semantic core.
- If no, expose only the shared core and fall back to coarser information.

## Provenance-Conditioned Interpretation

After retrieval and fidelity decoding, the system separately decides whether the retrieved information requires provenance-conditioned interpretation. This is different from fidelity allocation:

- Fidelity allocation decides how much detail survives compression.
- Provenance-conditioned interpretation decides how the surviving content should be understood.

If provenance-sensitive interpretation is needed, the system applies a lightweight steering vector at selected intermediate layers of the frozen LLM. The router is conditioned on:

- Retrieved memory.
- Source provenance.
- Current query.

The objective is not to make the model adopt the role of the original speaker. The objective is to use that role and source context as evidence for correct interpretation.

## Provenance Router Implementation

```python
class ProvenanceRouter(nn.Module):
    def __init__(self, hidden_dim, num_vectors):
        super().__init__()
        self.router = nn.Sequential(
            nn.Linear(hidden_dim * 3, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.gate_head = nn.Linear(hidden_dim, 1)
        self.vector_head = nn.Linear(hidden_dim, num_vectors)

    def forward(self, query_h, memory_h, provenance_h):
        x = torch.cat(
            [
                query_h,
                memory_h,
                provenance_h,
            ],
            dim=-1,
        )
        z = self.router(x)
        gate = torch.sigmoid(self.gate_head(z))
        weights = torch.softmax(self.vector_head(z), dim=-1)
        return gate, weights
```

Inputs:

- `query_h`: representation of the current question.
- `memory_h`: representation of retrieved evidence.
- `provenance_h`: representation of original speaker, role, and conversational context.

Outputs:

- `gate`: whether provenance-sensitive interpretation is required.
- `weights`: distribution over available interpretation vectors.

## Interpretation Vector Application

If the interpretation-vector library contains `v_1, ..., v_K` and the router outputs weights `alpha_1, ..., alpha_K`, the selected intervention is:

```text
v* = sum_k alpha_k v_k
```

The selected vector is applied to an intermediate hidden state:

```text
h' = h + g * lambda * v*
```

where:

- `g` is the routing gate.
- `lambda` is a bounded steering-strength parameter.
- `v*` is the weighted interpretation vector.

For the initial implementation, `lambda` can remain fixed so the router only learns whether steering is required and which interpretation direction to select.

## Constructing Interpretation Vectors

Interpretation vectors are initially constructed from matched provenance-sensitive contrasts:

- Pair the same or highly similar memory content with different source roles or contexts.
- Ensure each source role or context implies a different correct semantic interpretation.
- Capture activations at a selected transformer layer.
- Contrast activations for the correct provenance-conditioned interpretation against source-agnostic or incorrect interpretations.
- Average the activation differences to produce an initial candidate steering direction.

## End-to-End Pipeline

```text
multi-party conversation
-> exact recent-context window
-> future-consumer prediction at write time
-> audience-predictive compression
-> shared semantic core plus role-conditioned residual detail
-> query-dependent retrieval and fidelity decoding
-> optional provenance-conditioned interpretation
-> LLM answer
```
