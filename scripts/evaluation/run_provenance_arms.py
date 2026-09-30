#!/usr/bin/env python3
"""C4 reframed as a 2b-style counterfactual, on GroupMemBench.

Instead of asking the reader to INFER the speaker from style (which sits at the
random floor), hold the retrieved evidence fixed and vary only the provenance
label attached to it, then measure downstream answer accuracy:

    A. labelled    - correct speaker + role on every snippet   (ceiling)
    B. stripped    - no provenance at all                      (the loss)
    C. shuffled    - provenance present but WRONG              (worse than none?)

Same questions, same evidence, same reader. Only the labels move.
"""
from __future__ import annotations

import json, random, sys, time, urllib.request
from pathlib import Path

from src.evaluation.failure_decomposition import answer_support, answer_tokens  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BUNDLE = ROOT / "data" / "pilot" / "c4"
API = "http://127.0.0.1:11434/api/generate"
TAU = 0.65


def call(model, prompt, timeout=180):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0, "num_predict": 40}}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r).get("response", "").strip()


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:7b"
    msgs = {m["msg_node"]: m for m in map(json.loads, (BUNDLE / "evidence_messages.jsonl").open())}
    qs = [q for q in map(json.loads, (BUNDLE / "questions.jsonl").open())
          if q["eligible"] and all(u in msgs for u in q["evidence_msg_ids"])]
    rng = random.Random(3)
    roles = sorted({m["role"] for m in msgs.values()})
    authors = sorted({m["author"] for m in msgs.values()})
    print(f"{len(qs)} eligible questions, reader={model}, tau={TAU}\n")

    results, per_q = {}, {}
    for arm in ("labelled", "stripped", "shuffled"):
        hits = 0
        per_q[arm] = {}
        for q in qs:
            lines = []
            for i, u in enumerate(q["evidence_msg_ids"], 1):
                m = msgs[u]
                if arm == "labelled":
                    tag = f'{m["author"]} ({m["role"]}) '
                elif arm == "stripped":
                    tag = ""
                else:
                    wrong_a = rng.choice([a for a in authors if a != m["author"]])
                    wrong_r = rng.choice([r for r in roles if r != m["role"]])
                    tag = f"{wrong_a} ({wrong_r}) "
                lines.append(f'[{i}] {tag}on {m["timestamp"][:10]}: {m["content"][:400]}')
            prompt = ("Answer the question using only these conversation snippets. "
                      "Reply with the answer only, no explanation.\n\n"
                      + "\n".join(lines)
                      + f'\n\nAsked by {q["asking_user_id"]}.\nQuestion: {q["question"]}\nAnswer:')
            try:
                ans = call(model, prompt)
            except Exception as exc:
                print("call failed:", type(exc).__name__, exc); return 1
            ok = answer_support(answer_tokens(q["answer"]), ans) >= TAU
            per_q[arm][q["qid"]] = ok
            hits += ok
        results[arm] = hits / len(qs)
        print(f"  {arm:<10} answer accuracy {results[arm]:>6.1%}  ({hits}/{len(qs)})")

    print(f"\n  provenance effect (labelled - stripped): {results['labelled']-results['stripped']:+.1%}")
    print(f"  wrong-provenance cost (labelled - shuffled): {results['labelled']-results['shuffled']:+.1%}")

    # paired McNemar, labelled vs stripped
    b = sum(1 for q in qs if per_q["labelled"][q["qid"]] and not per_q["stripped"][q["qid"]])
    c = sum(1 for q in qs if not per_q["labelled"][q["qid"]] and per_q["stripped"][q["qid"]])
    from math import comb
    n = b + c
    p_two = min(1.0, 2 * sum(comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n) if n else 1.0
    print(f"  McNemar labelled vs stripped: {b} flips to labelled, {c} to stripped, "
          f"exact two-sided p = {p_two:.3f}")

    by_cat = {}
    for q in qs:
        by_cat.setdefault(q["category"], []).append(q["qid"])
    print(f"\n  {'category':<18}{'n':>4}{'labelled':>10}{'stripped':>10}{'shuffled':>10}{'prov effect':>13}")
    for cat, qids in sorted(by_cat.items()):
        acc = {a: sum(per_q[a][i] for i in qids) / len(qids) for a in results}
        print(f"  {cat:<18}{len(qids):>4}{acc['labelled']:>10.1%}{acc['stripped']:>10.1%}"
              f"{acc['shuffled']:>10.1%}{acc['labelled']-acc['stripped']:>+13.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
