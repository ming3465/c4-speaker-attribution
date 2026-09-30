"""Compressors for the C4 attribution probe: (units, budgets) -> {budget: {uid: text}}.

Two families, compared at matched word budgets:

  WordDropCompressor  keep the most salient words (or a prefix) of each message.
                      This is what the GroupMemBench pilot used. It keeps
                      high-IDF topic words, which is exactly what lexical
                      speaker binding relies on, so it is a mild threat.
  SummaryCompressor   an LLM rewrites each message as a neutral summary of at
                      most k words. Summaries change voice and wording -- the
                      realistic way memory systems compress, and the likelier
                      way to destroy who-said-what.

Summaries are per message, not merged across messages, so every snippet keeps
its own speaker label and the probe structure holds. Merged (multi-speaker)
summarization is a separate, stronger manipulation left for later.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from src.evaluation.attribution_frozen import build_stores
from src.evaluation.failure_decomposition import (
    MemoryQuestion,
    MemoryUnit,
    compress,
    corpus_idf,
    salience_order,
)
from src.evaluation.ollama_client import OllamaClient

ALLOCATIONS = ("pooled", "per-message")

SUMMARY_PROMPT = """Summarise the following chat message in at most {k} words.
Write a neutral summary of what it says. Keep the facts; do not add anything.
Output only the summary.

Message:
{text}
"""


def target_words(n_words: int, budget: float) -> int:
    """Word budget for one message: the same rule for every compressor."""
    return max(1, round(budget * n_words))


def cap_words(text: str, k: int) -> str:
    return " ".join(text.split()[:k])


def cache_key(model: str, k: int, text: str) -> str:
    return hashlib.sha256(f"{model}|{k}|{text}".encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WordDropCompressor:
    """Keep the most salient words (or a prefix) of each message.

    allocation "pooled" (the pilot): one word budget per conversation, shared as
    equal per-message cores, so every message gets about the same number of
    words whatever its length. Fine for similar-length chat messages; on
    meetings, where one-word backchannels sit next to long turns, it cuts long
    statements far below the nominal budget.
    allocation "per-message": keep target_words(n, budget) words of every
    message -- the same rule as SummaryCompressor, so budgets match exactly.
    """

    mode: str = "salient"            # "salient" | "prefix"
    policy: str = "uniform_compression"
    allocation: str = "pooled"       # "pooled" | "per-message"

    def compress(self, units: list[MemoryUnit], budgets: Iterable[float], *,
                 questions: Iterable[MemoryQuestion] = (),
                 only_uids: set[str] | None = None) -> dict[float, dict[str, str]]:  # noqa: ARG002
        if self.allocation == "pooled":
            return build_stores(units, list(questions), policy=self.policy,
                                budgets=list(budgets), compressor=self.mode)
        if self.allocation == "per-message":
            return _per_message_stores(units, list(budgets), self.mode)
        raise ValueError(f"allocation must be one of {ALLOCATIONS}, got {self.allocation!r}")


def _per_message_stores(units: list[MemoryUnit], budgets: list[float], mode: str) -> dict[float, dict[str, str]]:
    idf = corpus_idf(units)
    order = {u.uid: salience_order(u.text, idf) for u in units}
    return {budget: {u.uid: u.text if budget >= 1.0
                     else compress(u.text, target_words(len(u.text.split()), budget), order[u.uid], mode)
                     for u in units}
            for budget in budgets}


@dataclass
class SummaryCompressor:
    """LLM per-message summaries with a hard word cap and a content-hash cache.

    The cap keeps budgets matched across compressors: a summary longer than k
    words is clipped, and the number of clipped summaries is reported so a
    summarizer that ignores the limit is visible rather than silently favoured.
    """

    client: OllamaClient
    model: str
    cache_path: Path
    clipped: int = field(default=0, init=False)
    generated: int = field(default=0, init=False)

    def compress(self, units: list[MemoryUnit], budgets: Iterable[float], *,
                 questions: Iterable[MemoryQuestion] = (),  # noqa: ARG002
                 only_uids: set[str] | None = None) -> dict[float, dict[str, str]]:
        cache = self._load_cache()
        wanted = [u for u in units if only_uids is None or u.uid in only_uids]
        return {budget: {u.uid: self._compress_one(u.text, budget, cache) for u in wanted}
                for budget in budgets}

    def _compress_one(self, text: str, budget: float, cache: dict[str, str]) -> str:
        words = text.split()
        k = target_words(len(words), budget)
        if budget >= 1.0 or len(words) <= k:
            return text  # already within budget: identity, no model call
        key = cache_key(self.model, k, text)
        if key not in cache:
            summary = self.client.generate(
                self.model, SUMMARY_PROMPT.format(k=k, text=text),
                options={"temperature": 0, "seed": 0, "num_predict": min(512, 2 * k + 32)},
            )
            cache[key] = summary
            self._append_cache(key, k, summary)
            self.generated += 1
        summary = cache[key]
        if len(summary.split()) > k:
            self.clipped += 1
        return cap_words(summary, k)

    def _load_cache(self) -> dict[str, str]:
        if not self.cache_path.exists():
            return {}
        cache: dict[str, str] = {}
        with self.cache_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    entry = json.loads(line)
                    cache[entry["key"]] = entry["summary"]
        return cache

    def _append_cache(self, key: str, k: int, summary: str) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"key": key, "model": self.model, "k": k, "summary": summary}) + "\n")
