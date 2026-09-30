from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List

from cross_oem_migration.inference.gateway_client import GrpcGatewayClient
from cross_oem_migration.inference.vllm_client import VllmClient


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--checkpoint-path", required=True)
    parser.add_argument("--prompts-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--gateway-endpoint", default="")
    parser.add_argument("--vllm-endpoint", default="")
    return parser.parse_args()


def _read_prompts(path: str) -> List[str]:
    with open(path) as f:
        rows = [line.strip() for line in f if line.strip()]
    return rows


def _run_via_gateway(args: argparse.Namespace, prompts: List[str]) -> Dict[str, Any]:
    client = GrpcGatewayClient(args.gateway_endpoint)
    return client.generate(
        model=args.model_id,
        prompts=prompts,
        max_tokens=args.max_new_tokens,
        temperature=args.temperature,
    )


def _run_via_vllm(args: argparse.Namespace, prompts: List[str]) -> Dict[str, Any]:
    client = VllmClient(args.vllm_endpoint)
    return client.generate(
        model=args.model_id,
        prompts=prompts,
        max_tokens=args.max_new_tokens,
        temperature=args.temperature,
    )


def _extract_texts(payload: Dict[str, Any]) -> List[str]:
    choices = payload.get("choices", [])
    return [str(choice.get("text", "")) for choice in choices]


def main() -> None:
    args = _parse_args()
    prompts = _read_prompts(args.prompts_path)
    payload = _run_via_gateway(args, prompts) if args.gateway_endpoint else _run_via_vllm(args, prompts)
    texts = _extract_texts(payload)
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, "w") as f:
        json.dump({"prompts": prompts, "outputs": texts}, f, indent=2)
    summary = {
        "status": "ok",
        "model_id": args.model_id,
        "checkpoint_path": args.checkpoint_path,
        "request_count": len(prompts),
        "engine": "grpc_gateway" if args.gateway_endpoint else "vllm_http",
        "output_path": args.output_path,
        "usage": payload.get("usage", {}),
    }
    with open(os.path.join(os.path.dirname(args.output_path), "run_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
