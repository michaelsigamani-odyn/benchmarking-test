from __future__ import annotations

import argparse
from concurrent import futures

import grpc

from cross_oem_migration.inference.gateway_stubs import (
    GenerateRequest,
    GenerateResponse,
    InferenceGatewayServicer,
    add_InferenceGatewayServicer_to_server,
)
from cross_oem_migration.inference.vllm_client import VllmClient


class GatewayService(InferenceGatewayServicer):
    def __init__(self, vllm_endpoint: str):
        self._client = VllmClient(vllm_endpoint)

    def Generate(self, request: GenerateRequest, context: grpc.ServicerContext) -> GenerateResponse:
        payload = self._client.generate(
            model=request.model,
            prompts=list(request.prompts),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        outputs = [str(choice.get("text", "")) for choice in payload.get("choices", [])]
        usage = {k: int(v) for k, v in dict(payload.get("usage", {})).items()}
        return GenerateResponse(outputs=outputs, model=request.model, usage=usage)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="0.0.0.0:50051")
    parser.add_argument("--vllm-endpoint", required=True)
    parser.add_argument("--max-workers", type=int, default=16)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=args.max_workers))
    add_InferenceGatewayServicer_to_server(GatewayService(args.vllm_endpoint), server)
    server.add_insecure_port(args.listen)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    main()
