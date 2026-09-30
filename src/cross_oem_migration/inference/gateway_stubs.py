from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Sequence

import grpc


@dataclass
class GenerateRequest:
    model: str
    prompts: Sequence[str]
    max_tokens: int
    temperature: float


@dataclass
class GenerateResponse:
    outputs: List[str]
    model: str
    usage: Dict[str, int]


def _serialize_request(message: GenerateRequest) -> bytes:
    return json.dumps(asdict(message)).encode("utf-8")


def _deserialize_request(payload: bytes) -> GenerateRequest:
    body = json.loads(payload.decode("utf-8"))
    return GenerateRequest(
        model=str(body["model"]),
        prompts=list(body["prompts"]),
        max_tokens=int(body["max_tokens"]),
        temperature=float(body.get("temperature", 0.0)),
    )


def _serialize_response(message: GenerateResponse) -> bytes:
    return json.dumps(asdict(message)).encode("utf-8")


def _deserialize_response(payload: bytes) -> GenerateResponse:
    body = json.loads(payload.decode("utf-8"))
    return GenerateResponse(
        outputs=list(body["outputs"]),
        model=str(body["model"]),
        usage={k: int(v) for k, v in dict(body.get("usage", {})).items()},
    )


class InferenceGatewayStub:
    def __init__(self, channel: grpc.Channel):
        self.Generate = channel.unary_unary(
            "/cross_oem_migration.inference.InferenceGateway/Generate",
            request_serializer=_serialize_request,
            response_deserializer=_deserialize_response,
        )


class InferenceGatewayServicer:
    def Generate(self, request: GenerateRequest, context: grpc.ServicerContext) -> GenerateResponse:
        raise NotImplementedError()


def add_InferenceGatewayServicer_to_server(servicer: InferenceGatewayServicer, server: grpc.Server) -> None:
    rpc_method_handlers = {
        "Generate": grpc.unary_unary_rpc_method_handler(
            servicer.Generate,
            request_deserializer=_deserialize_request,
            response_serializer=_serialize_response,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "cross_oem_migration.inference.InferenceGateway",
        rpc_method_handlers,
    )
    server.add_generic_rpc_handlers((generic_handler,))
