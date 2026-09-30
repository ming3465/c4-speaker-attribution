#!/usr/bin/env python3
"""Export a self-contained Contribution 4 pilot bundle.

The raw GroupMemBench domain files are 48 MB each and gitignored, and the
labels are spread across three repositories. This collapses everything the
failure decomposition needs into `data/pilot/c4/`, small enough to commit:

    questions.jsonl          185 evidence-linked Finance questions, merged
    evidence_messages.jsonl  every gold evidence message, full metadata
    corpus_<pct>.jsonl       sampled corpus that keeps ALL evidence messages
    manifest.json            counts, provenance, and the sampling caveat
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.datasets.memory_tasks import QUESTION_TYPES, read_jsonl  # noqa: E402
from src.evaluation.failure_decomposition import answer_support, answer_tokens  # noqa: E402

KEEP_FIELDS = (
    "msg_node", "content", "author", "role", "timestamp", "reply_to",
    "topic", "phase_name", "is_noise", "is_decision_point",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="Finance")
    parser.add_argument("--sample-pct", type=float, default=10.0,
                        help="Percent of non-evidence messages to keep.")
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument("--tau", type=float, default=0.65)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data" / "pilot" / "c4")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw = ROOT / "data" / "raw"
    conversations = json.loads(
        (raw / "groupmembench" / f"synthetic_domain_channels_rolevariants_{args.domain}.json")
        .read_text(encoding="utf-8")
    )
    questions_dir = raw / "groupmembench" / "questions" / args.domain
    evidence_rows = read_jsonl(
        raw / "gmb_agent_sessions" / args.domain.lower() / "questions_enhanced.jsonl"
    )
    recovered = {str(row["id"]): row for row in evidence_rows}

    messages: dict[str, dict] = {}
    channel_of: dict[str, str] = {}
    for channel, entries in conversations.items():
        for message in entries:
            uid = str(message["msg_node"])
            messages[uid] = {"channel": channel} | {
                field: message.get(field) for field in KEEP_FIELDS
            }
            channel_of[uid] = channel

    questions: list[dict] = []
    for question_type in QUESTION_TYPES:
        path = questions_dir / f"{question_type}.jsonl"
        if not path.exists():
            continue
        for row in read_jsonl(path):
            extra = recovered.get(str(row["id"]), {})
            uids = [str(u) for u in extra.get("evidence_msg_ids") or []]
            if not uids:
                continue
            gold = answer_tokens(str(row["answer"]))
            best = max(answer_support(gold, messages[u]["content"]) for u in uids if u in messages)
            questions.append({
                "qid": str(row["id"]),
                "category": question_type,
                "question": str(row["question"]),
                "answer": str(row["answer"]),
                "asking_user_id": str(row.get("asking_user_id", "")),
                "evidence_msg_ids": uids,
                "evidence_channels": sorted({channel_of[u] for u in uids if u in channel_of}),
                "evidence_authors": sorted({messages[u]["author"] for u in uids if u in messages}),
                "label_confidence": extra.get("confidence"),
                "answer_support_full_fidelity": round(best, 4),
                "eligible": bool(best >= args.tau),
                "cross_consumer": bool(
                    {messages[u]["author"] for u in uids if u in messages}
                    - {str(row.get("asking_user_id", ""))}
                ),
            })

    evidence_uids = {u for q in questions for u in q["evidence_msg_ids"]}
    rng = random.Random(args.seed)
    keep = set(evidence_uids)
    per_channel: dict[str, list[str]] = defaultdict(list)
    for uid, channel in channel_of.items():
        if uid not in evidence_uids:
            per_channel[channel].append(uid)
    for channel, uids in per_channel.items():
        uids.sort()
        take = round(len(uids) * args.sample_pct / 100)
        keep.update(rng.sample(uids, take))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{args.sample_pct:g}pct"

    def dump(name: str, rows: list[dict]) -> Path:
        path = args.out_dir / name
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return path

    ordered = [uid for uid in messages if uid in keep]
    paths = [
        dump("questions.jsonl", questions),
        dump("evidence_messages.jsonl", [messages[u] | {"msg_node": u} for u in messages if u in evidence_uids]),
        dump(f"corpus_{tag}.jsonl", [messages[u] | {"msg_node": u} for u in ordered]),
    ]

    eligible = [q for q in questions if q["eligible"]]
    manifest = {
        "bundle": "contribution_4_failure_decomposition_pilot",
        "domain": args.domain,
        "generated_by": "scripts/data/export_pilot_bundle.py",
        "sources": {
            "conversations": "huggingface://datasets/kimperyang/GroupMemBench",
            "questions": "github://UCSB-NLP-Chang/GroupMemBench/questions",
            "evidence": "huggingface://datasets/toddzheng024/groupmembench-agent-sessions",
        },
        "counts": {
            "questions_with_evidence": len(questions),
            "questions_eligible": len(eligible),
            "eligible_by_category": dict(Counter(q["category"] for q in eligible)),
            "cross_consumer_questions": sum(1 for q in questions if q["cross_consumer"]),
            "distinct_evidence_messages": len(evidence_uids),
            "corpus_messages_full": len(messages),
            "corpus_messages_sampled": len(ordered),
            "channels": len(conversations),
        },
        "sampling": {
            "percent_of_non_evidence_kept": args.sample_pct,
            "seed": args.seed,
            "all_evidence_retained": True,
        },
        "eligibility": {
            "rule": "gold answer tokens recoverable from gold evidence at full fidelity",
            "threshold_tau": args.tau,
        },
        "caveat": (
            "The sampled corpus removes distractors, so retrieval is easier on it "
            "than on the full 30,000-message domain. Use it to validate pipeline "
            "logic; report numbers from the full corpus."
        ),
        "files": {path.name: path.stat().st_size for path in paths},
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    for path in paths:
        print(f"wrote {path.relative_to(ROOT)}  {path.stat().st_size / 1e6:.2f} MB")
    print(f"wrote {(args.out_dir / 'manifest.json').relative_to(ROOT)}")
    print(json.dumps(manifest["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
