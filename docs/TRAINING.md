# Training

## Training Principle

The base LLM remains frozen throughout the primary experiments. Training focuses on lightweight components:

- Future-consumer predictor.
- Write controller.
- Read controller.
- Provenance-aware interpretation router.

Supervised training comes first. Reinforcement learning or task-level refinement is reserved for later because long-conversation RL can be expensive.

## Stage 1: Future-Consumer Predictor

Train a lightweight multi-label predictor using supervised future-dependency labels from synthetic data.

Training labels:

- Which participants later required each fact.
- Which participant roles later queried each fact.
- Which earlier memories supported later questions or decisions.

The predictor learns the probability that each participant will require each candidate memory in the future.

## Stage 2: Memory And Interpretation Controllers

Train lightweight write/read controllers and the provenance-aware interpretation router using supervised examples where the correct behavior is known.

Supervised targets include:

- Correct source speaker.
- Correct source role.
- Predicted consumers.
- Memory allocation decision.
- Relevant evidence.
- Whether provenance-conditioned interpretation is required.
- Which interpretation vector or contrast should apply.

This stage avoids needing expensive reinforcement learning from the beginning.

## Stage 3: Joint Refinement

After the components work independently, integrate them and optionally refine the lightweight controllers using task-level rewards.

Reward signals can include:

- Answer correctness.
- Speaker attribution.
- Evidence retrieval.
- Interpretation accuracy.
- Memory usage.
- Latency.

The main purpose is to tune coordination between the write-time predictor, memory allocation, read-time retrieval, and interpretation router.

## Synthetic Training Dataset

The project uses a separate synthetic training dataset instead of training directly on public evaluation benchmarks.

Initial target:

- About 10,000 multi-party conversations.
- Separate development and internal test sets.
- Size is provisional and should be adjusted after measuring generation and training costs.

Conversation properties:

- Three to six participants.
- Roles such as engineer, manager, researcher, customer, student, administrator, and designer.
- Speaker-specific facts.
- Shared facts.
- Conflicting information.
- Knowledge updates.
- Temporal changes.
- Ambiguous terminology.
- Distractor information.

## Structured Dependency Graph

Each synthetic conversation should first be generated from an underlying structured dependency graph.

The graph specifies:

- Facts introduced during the conversation.
- Source participants.
- Source roles.
- Later participants who require each fact.
- Future queries or decisions that depend on each fact.
- Evidence required to answer each question.

Natural-language dialogue is then generated from this structured plan.

## Automatically Available Labels

Because generation starts from structured events, the training process can automatically know:

- Who introduced each fact.
- Whether a fact is shared or private.
- Which information was later updated.
- Which evidence is required to answer each question.
- Which participant roles subsequently queried each fact.

These labels provide direct supervision for future-consumer prediction and provenance-aware routing.

## Provenance-Sensitive Interpretation Subset

A separate subset of synthetic data should target interpretation.

Positive examples:

- Identical or highly similar lexical content.
- Different source speakers, roles, or conversational contexts.
- Correct interpretation changes because provenance changes.

Negative examples:

- Role-independent facts.
- Changing provenance should not affect the correct interpretation.

Use cases:

- Construct interpretation vectors.
- Train the provenance-aware router.
- Test whether steering is needed only when provenance actually matters.

## Held-Out Evaluation Rule

Public evaluation datasets must remain fully held out from controller training.

Reason: the central claim is that the controller learns a general memory-management policy, not the structure of one benchmark.
