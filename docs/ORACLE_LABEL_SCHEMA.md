# Oracle Label Schema

This schema defines the minimal label format for Phase 0 oracle validation.

The label answers:

```text
Which later participant needed which earlier memory evidence?
```

## File Format

Use JSONL: one JSON object per question/evidence label.

Recommended path:

```text
data/processed/groupmembench/oracle_labels.jsonl
```

## Required Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `label_id` | string | Unique label row ID. |
| `domain` | string | GroupMemBench domain, such as `Finance` or `Technology`. |
| `channel` | string | Channel or thread name. |
| `question_id` | string | Evaluation question ID. |
| `question_type` | string | Question type, such as `multi_hop`, `knowledge_update`, `temporal`, `user_implicit`, `term_ambiguity`, or `abstention`. |
| `question_asker` | string | Participant who asks the later question. |
| `question_asker_role` | string | Role of the later asker. |
| `answer` | string | Gold answer. |
| `evidence_message_ids` | list[string] | Earlier messages required to answer the question. |
| `future_consumer_ids` | list[string] | Participants who later require the evidence. Usually includes `question_asker`. |
| `future_consumer_roles` | list[string] | Roles of the future consumers. |

## Optional Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `source_speakers` | list[string] | Authors of the evidence messages. |
| `source_roles` | list[string] | Roles of the evidence-message authors. |
| `topic` | string | Topic associated with the question or evidence. |
| `phase_name` | string | Work phase associated with the evidence. |
| `requires_provenance` | boolean | Whether the answer depends on source speaker or role. |
| `requires_update` | boolean | Whether the answer depends on a later correction or decision update. |
| `requires_multi_hop` | boolean | Whether multiple evidence messages are needed. |
| `notes` | string | Human labeler notes. |

## Example Row

```json
{"label_id":"Finance_001","domain":"Finance","channel":"example_channel","question_id":"Q_001","question_type":"term_ambiguity","question_asker":"User_7","question_asker_role":"Risk Manager","answer":"The token refers to an authentication credential in this context.","evidence_message_ids":["Msg_123"],"future_consumer_ids":["User_7"],"future_consumer_roles":["Risk Manager"],"source_speakers":["User_2"],"source_roles":["Security Engineer"],"topic":"auth incident","phase_name":"incident review","requires_provenance":true,"requires_update":false,"requires_multi_hop":false,"notes":"Toy example row; replace with real GroupMemBench IDs."}
```

## Labeling Rule

For non-abstention questions:

- `evidence_message_ids` should contain the earlier messages needed to answer the question.
- `future_consumer_ids` should include the later asker and any other participants known to require that evidence.
- `future_consumer_roles` should match the roles of those future consumers.

For abstention questions:

- `evidence_message_ids` should be empty if the memory genuinely contains no answer.
- Abstention rows are useful for answer evaluation, but they do not create positive future-consumer training labels.

## Validation

Run:

```bash
python scripts/data/validate_oracle_labels.py --input data/processed/groupmembench/oracle_labels.jsonl
```

The validator checks required fields, list fields, duplicate label IDs, and abstention evidence consistency.
