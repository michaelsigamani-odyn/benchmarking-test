from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

import numpy as np

from .hf_io import write_safetensors

_TARGET_TO_MODULE = {
    "q": "self_attn.q_proj",
    "k": "self_attn.k_proj",
    "v": "self_attn.v_proj",
    "o": "self_attn.o_proj",
    "gate": "mlp.gate_proj",
    "up": "mlp.up_proj",
    "down": "mlp.down_proj",
}


def _adapter_name(layer: int, module: str, side: str) -> str:
    return f"base_model.model.model.layers.{layer}.{module}.lora_{side}.weight"


def _tensor_pair(a: Any, b: Any) -> Tuple[np.ndarray, np.ndarray]:
    return np.asarray(a, np.float32).T.copy(), np.asarray(b, np.float32).T.copy()


def export_lora_adapter(ckpt_dir: str, lora: Dict[str, Any], alpha: int, rank: int) -> Dict[str, Any]:
    adapter_dir = os.path.join(ckpt_dir, "vllm_adapter")
    os.makedirs(adapter_dir, exist_ok=True)
    tensors: Dict[str, np.ndarray] = {}
    mapping: Dict[str, str] = {}
    for target, blocks in lora.items():
        module = _TARGET_TO_MODULE.get(target)
        if not module:
            continue
        for layer in range(int(blocks["a"].shape[0])):
            name_a = _adapter_name(layer, module, "A")
            name_b = _adapter_name(layer, module, "B")
            tensor_a, tensor_b = _tensor_pair(blocks["a"][layer], blocks["b"][layer])
            tensors[name_a], tensors[name_b] = tensor_a, tensor_b
            mapping[f"{target}.{layer}.a"], mapping[f"{target}.{layer}.b"] = name_a, name_b
    write_safetensors(os.path.join(adapter_dir, "adapter_model.safetensors"), tensors)
    with open(os.path.join(adapter_dir, "adapter_config.json"), "w") as f:
        json.dump({"peft_type": "LORA", "r": rank, "lora_alpha": alpha, "bias": "none"}, f, indent=2)
    with open(os.path.join(adapter_dir, "tensor_name_map.json"), "w") as f:
        json.dump(mapping, f, indent=2, sort_keys=True)
    return {"adapter_dir": adapter_dir, "tensor_count": len(tensors), "map_path": os.path.join(adapter_dir, "tensor_name_map.json")}
