#!/usr/bin/env python3
"""Can a reader tell who said what, on UNCOMPRESSED text?

Screens a corpus BEFORE investing in a speaker-attribution study.

This is the ceiling condition for C4. If a dataset has no ceiling, no amount of
compression can produce a dose-response curve on it -- the hypothesis is
untestable there. Same probe shape for every dataset: a window of consecutive
turns with one speaker blinded, plus a candidate roster.
"""
from __future__ import annotations

import json, random, statistics, sys, time, urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed" / "attribution_ceiling"
API = "http://127.0.0.1:11434/api/generate"
WINDOW, ROSTER, CHARS = 5, 6, 320


def call(model, prompt, timeout=180):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0, "num_predict": 14}}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    t = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r).get("response", "").strip(), time.monotonic() - t


def build(turns, n_probes, seed=11):
    rng = random.Random(seed)
    pool = sorted({t["speaker"] for t in turns})
    groups = {}
    for t in turns:
        groups.setdefault(t["group"], []).append(t)
    probes = []
    for members in groups.values():
        for start in range(0, len(members) - WINDOW, WINDOW):
            win = members[start:start + WINDOW]
            hidden = WINDOW // 2
            gold = win[hidden]["speaker"]
            others = [s for s in pool if s != gold]
            size = min(ROSTER, len(pool)) - 1
            if size < 2:
                continue
            roster = sorted(rng.sample(others, size) + [gold])
            ctx = "\n".join(
                f'[{i}] {"?" if i == hidden else t["speaker"]}: {t["text"][:CHARS]}'
                for i, t in enumerate(win))
            leak = gold.lower() in " ".join(
                t["text"] for i, t in enumerate(win) if i != hidden).lower()
            probes.append({"gold": gold, "leak": leak, "n_cand": len(roster), "prompt":
                "Below are consecutive turns from a conversation. One speaker is hidden as '?'.\n\n"
                f"{ctx}\n\nCandidates: {', '.join(roster)}\n\n"
                "Who spoke the turn marked '?' Answer with the name only."})
            if len(probes) >= n_probes:
                return probes, pool
    return probes, pool


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:7b"
    data = json.loads((DATA / "candidate_turns.json").read_text())
    print(f"reader: {model}   window={WINDOW}  roster={ROSTER}\n")
    print(f"{'dataset':<20}{'probes':>7}{'cands':>7}{'floor':>8}{'majority':>10}{'Hit@1':>8}{'lift':>8}")
    for name, turns in data.items():
        probes, pool = build(turns, 200)
        probes = [p for p in probes if not p["leak"]][:70]   # drop name-leak probes entirely
        if len(probes) < 15:
            print(f"{name:<20}{len(probes):>7}  too few leak-free probes"); continue
        floor = 1 / probes[0]["n_cand"]
        majority = max(Counter(p["gold"] for p in probes).values()) / len(probes)
        hits, n = 0, 0
        for p in probes:
            try:
                ans, _ = call(model, p["prompt"])
            except Exception as exc:
                print(f"  {name}: call failed {type(exc).__name__}"); break
            n += 1
            hits += p["gold"].lower() in ans.lower()
        acc = hits / max(n, 1)
        print(f"{name:<20}{n:>7}{probes[0][chr(34)+chr(34)] if False else probes[0]['n_cand']:>7}{floor:>8.3f}{majority:>10.3f}{acc:>8.3f}{acc-floor:>+8.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
