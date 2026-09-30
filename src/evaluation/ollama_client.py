"""Minimal stdlib client for a local or remote Ollama server.

Shared by the attribution reader and the summary compressor so both hit the
same server with the same settings. Point `base_url` at another machine (e.g.
the GPU box) to use a larger model without code changes.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:11434"


@dataclass(frozen=True)
class OllamaClient:
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: int = 180

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        options: dict[str, Any] | None = None,
        format: dict[str, Any] | None = None,
    ) -> str:
        """Non-streaming completion. Raises on HTTP or JSON errors -- callers
        record the error per row rather than silently scoring it."""
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False,
                                   "options": options or {}}
        if format is not None:
            payload["format"] = format
        return str(self._request("/api/generate", payload).get("response", "")).strip()

    def model_digest(self, model: str) -> str:
        """Digest of an installed model, for the run manifest. Empty if absent."""
        wanted = model if ":" in model else f"{model}:latest"
        for entry in self._request("/api/tags").get("models", []):
            if entry.get("name") in (model, wanted):
                return str(entry.get("digest", ""))
        return ""
