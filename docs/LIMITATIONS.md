# Limitations

## Computational Cost

Reinforcement learning over long conversations may be expensive even with a frozen base model.

Mitigation:

- Train controllers with supervised learning first.
- Use task-level RL or refinement only after supervised components work.
- If RL is infeasible, evaluate the supervised dynamic router as a valid version of the method.

## Synthetic Training Data Realism

The training dataset may be difficult to generate realistically.

Specific risks:

- Speaker roles and vocabulary ambiguity may not behave like real interactions.
- Patterns of who queries a fact later may be unrealistic.
- Simulating plausible future conversational behavior is harder than generating plausible present dialogue.

Mitigation:

- Treat synthetic data as controller-training data, not proof that the method works.
- Use held-out real benchmarks for scientific evidence.

## Novelty Boundary

Adaptive memory routing and dynamic activation steering are active research areas.

The proposal should not claim to be the first method to:

- Perform adaptive compression.
- Perform adaptive KV-cache management.
- Use dynamic memory operation routing.
- Use speaker-indexed memory.
- Use private/shared group memory.
- Use role vectors or activation steering.

The novelty should remain focused on:

- Predicting future consumer roles or participants.
- Using that prediction to guide compression fidelity.
- Combining the write-time prediction with provenance-conditioned interpretation at read time.

## Activation Steering Reliability

Steering vectors can cause unintended behavior changes.

Risks:

- Reduced answer reliability on ordinary questions.
- Safety regressions.
- Unrelated task degradation.
- Over-application of provenance-sensitive interpretation.

Mitigation:

- Bound steering magnitude.
- Use a router gate so steering is optional.
- Regression-test ordinary QA, safety-related prompts, and unrelated tasks.
- Include negative examples where provenance should not affect interpretation.

## Ambiguous Or Changing Roles

Speaker roles are not always fixed.

Risks:

- A participant may have multiple roles.
- A participant may change roles during a conversation.
- Future-consumer predictions for older information may become inaccurate after a role change.

Mitigation:

- Start with explicit roles to establish the core effect.
- Add ambiguous or changing-role experiments if time permits.

## Wrong Future-Consumer Predictions

Incorrect prediction can cause permanent fidelity loss.

Why this matters:

- If residual detail is discarded because the predicted consumer did not seem likely to need it, the system may not recover that detail later.
- This is a genuine tradeoff introduced by the proposed method.
- Speaker-partitioned storage may preserve more detail per speaker even if it is less efficient.

Required measurement:

- Compare failure rates when future-consumer prediction was right versus wrong.

## Joint Reasoning Across Many Speakers

The architecture may fail when information is useful only after combining facts across many participants.

Risk:

- If no single role is predicted to need a fact, role-specific residual detail may be under-preserved.

Mitigation:

- Keep a shared semantic core accessible to all readers.
- Directly evaluate cross-speaker reasoning instead of assuming the shared core solves it.

## Benchmark Overfitting

The controller may learn the structure of one benchmark instead of a general memory-management policy.

Mitigation:

- Keep public evaluation datasets held out.
- Use multiple benchmarks.
- Include qualitative checks of whether controller decisions track meaningful conversational events.

## Practical Memory Accounting

The system adds metadata and residual details that must count toward total memory cost.

Risk:

- The method may appear efficient if shared cores are counted but provenance metadata or residuals are ignored.

Mitigation:

- Count shared semantic cores, residuals, provenance metadata, and predicted-consumer metadata in memory cost.
