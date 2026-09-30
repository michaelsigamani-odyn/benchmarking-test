from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List
from urllib import request


@dataclass(frozen=True)
class VllmClient:
    endpoint: str
    timeout_s: float = 60.0

    def generate(self, *, model: str, prompts: List[str], max_tokens: int, temperature: float) -> Dict[str, object]:
        body = {
            "model": model,
            "prompt": prompts,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        payload = json.dumps(body).encode("utf-8")
        req = request.Request(self._url("/v1/completions"), data=payload, headers={"Content-Type": "application/json"})
        with request.urlopen(req, timeout=self.timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _url(self, path: str) -> str:
        return self.endpoint.rstrip("/") + path
