from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import grpc

from .gateway_stubs import GenerateRequest, InferenceGatewayStub


@dataclass(frozen=True)
class GrpcGatewayClient:
    endpoint: str
    timeout_s: float = 60.0

    def generate(self, *, model: str, prompts: List[str], max_tokens: int, temperature: float) -> Dict[str, object]:
        with grpc.insecure_channel(self.endpoint) as channel:
            stub = InferenceGatewayStub(channel)
            response = stub.Generate(
                GenerateRequest(model=model, prompts=prompts, max_tokens=max_tokens, temperature=temperature),
                timeout=self.timeout_s,
            )
        return {"model": response.model, "choices": [{"text": text} for text in response.outputs], "usage": response.usage}
