from __future__ import annotations

import json
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.evaluation.retrieval_proxy import (
    build_index,
    raw_domain_file,
    retrieve,
    score_retrieval,
    synthetic_query,
)
from src.evaluation.retrieval_proxy import load_labels as load_jsonl_labels
from src.evaluation.retrieval_proxy import write_json
from src.datasets.groupmembench import iter_messages, load_domain_file


DEFAULT_PILOT_STRATEGIES = (
    "uniform_compression",
    "speaker_partitioned_memory",
    "a_mac_metadata_utility",
    "query_task_conditioned_compression",
    "recency_window",
    "oracle_future_consumer_allocation",
)


def select_stratified_labels(
    labels: list[dict[str, Any]], sample_size: int
) -> list[dict[str, Any]]:
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for label in labels:
        by_domain[str(label.get("domain", ""))].append(label)

    selected: list[dict[str, Any]] = []
    domain_names = sorted(by_domain)
    index = 0
    while len(selected) < sample_size:
        added = False
        for domain in domain_names:
            domain_labels = by_domain[domain]
            if index < len(domain_labels):
                selected.append(domain_labels[index])
                added = True
                if len(selected) >= sample_size:
                    break
        if not added:
            break
        index += 1
    return selected


def retrieved_context_for_strategy(
    *,
    raw_dir: Path,
    label: dict[str, Any],
    strategy: str,
    shared_core_tokens: int,
    residual_tokens: int,
    top_k: int,
) -> dict[str, Any]:
    domain = str(label["domain"])
    data = load_domain_file(raw_domain_file(raw_dir, domain))
    records = iter_messages(data, domain=domain)
    index = build_index(
        records,
        label,
        strategy=strategy,
        shared_core_tokens=shared_core_tokens,
        residual_tokens=residual_tokens,
    )
    query = synthetic_query(label)
    retrieved = retrieve(index, query, top_k=top_k)
    evidence_ids = set(label.get("evidence_message_ids") or [])
    snippets = [
        {
            "rank": rank,
            "score": round(score, 4),
            "msg_node": message.msg_node,
            "author": message.author,
            "role": message.role,
            "text": message.visible_text,
            "is_gold_evidence": message.msg_node in evidence_ids,
        }
        for rank, (score, message) in enumerate(retrieved, 1)
    ]
    return {
        "query": query,
        "snippets": snippets,
        "gold_evidence_retrieved": any(
            snippet["is_gold_evidence"] for snippet in snippets
        ),
    }


def answer_prompt(label: dict[str, Any], context: dict[str, Any]) -> str:
    snippets_json = json.dumps(context["snippets"], ensure_ascii=False, indent=2)
    return f"""You are answering a memory question from retrieved conversation snippets.

Rules:
- Use only the provided snippets.
- If the snippets do not contain enough information to answer, reply exactly: NOT_ENOUGH_INFORMATION.
- Do not mention that you are an AI or discuss the evaluation.
- Return only the answer, with no markdown.

Question:
{context["query"]}

Question asker:
{label["question_asker"]} ({label["question_asker_role"]})

Retrieved snippets:
{snippets_json}
"""


def judge_prompt(rows: list[dict[str, Any]]) -> str:
    compact_rows = [
        {
            "row_id": row["row_id"],
            "question": row["question"],
            "gold_answer": row["gold_answer"],
            "model_answer": row["model_answer"],
        }
        for row in rows
    ]
    return f"""You are judging answers for a research pilot.

For each row, mark correct=true only if the model answer captures the same current updated decision as the gold answer. Do not require exact wording. Mark correct=false if the answer is missing, contradicts the gold answer, or only states old/outdated information.

Return valid JSON only, with this shape:
{{"judgments":[{{"row_id":"...","correct":true,"rationale":"short reason"}}]}}

Rows:
{json.dumps(compact_rows, ensure_ascii=False, indent=2)}
"""


def run_codex_exec(
    *,
    codex_path: Path,
    model: str,
    cwd: Path,
    prompt: str,
    timeout_seconds: int,
) -> str:
    with tempfile.TemporaryDirectory(prefix="phase0_llm_") as tmpdir:
        output_path = Path(tmpdir) / "last_message.txt"
        command = [
            str(codex_path),
            "exec",
            "--ephemeral",
            "-m",
            model,
            "-s",
            "read-only",
            "-C",
            str(cwd),
            "--color",
            "never",
            "-o",
            str(output_path),
            "-",
        ]
        subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            check=True,
            timeout=timeout_seconds,
        )
        return output_path.read_text(encoding="utf-8").strip()


def strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def parse_judgments(text: str) -> dict[str, Any]:
    return json.loads(strip_json_fence(text))


def summarize_judged_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        strategy = row["strategy"]
        bucket = summary[strategy]
        bucket["rows"] += 1
        bucket["correct"] += int(bool(row.get("judge_correct")))
        bucket["gold_evidence_retrieved"] += int(bool(row["gold_evidence_retrieved"]))

    final: dict[str, Any] = {}
    for strategy, values in summary.items():
        count = max(values["rows"], 1)
        final[strategy] = {
            "rows": int(values["rows"]),
            "llm_accuracy": round(values["correct"] / count, 4),
            "gold_evidence_retrieval_rate": round(
                values["gold_evidence_retrieved"] / count, 4
            ),
        }
    return final
