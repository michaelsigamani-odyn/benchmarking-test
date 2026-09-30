from dataclasses import dataclass
from typing import Any, Dict
import shlex

from .base import Workload


@dataclass
class InferenceJobSpec:
    model_id: str
    checkpoint_path: str
    prompts_path: str
    output_path: str
    max_new_tokens: int = 256
    temperature: float = 0.0
    gateway_endpoint: str = ""
    vllm_endpoint: str = ""


class InferenceWorkload(Workload):
    name = "inference"
    script_relpath = "scripts/inference/serve.py"

    def build_command(self, *, python_cmd: str, remote_root: str, spec: InferenceJobSpec, **kwargs: Any) -> str:
        script = f"{remote_root}/{self.script_relpath}"
        args = [
            python_cmd,
            script,
            "--model-id",
            spec.model_id,
            "--checkpoint-path",
            spec.checkpoint_path,
            "--prompts-path",
            spec.prompts_path,
            "--output-path",
            spec.output_path,
            "--max-new-tokens",
            str(spec.max_new_tokens),
            "--temperature",
            str(spec.temperature),
        ]
        if spec.gateway_endpoint:
            args += ["--gateway-endpoint", spec.gateway_endpoint]
        if spec.vllm_endpoint:
            args += ["--vllm-endpoint", spec.vllm_endpoint]
        return " ".join(shlex.quote(part) for part in args)

    def parse_run_summary(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": str(payload.get("status", "unknown")),
            "model_id": payload.get("model_id"),
            "request_count": int(payload.get("request_count", 0)),
            "output_path": payload.get("output_path"),
            "engine": payload.get("engine"),
        }
