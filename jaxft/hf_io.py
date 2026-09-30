"""Load Hugging Face safetensors checkpoints into the stacked-layer pytree used by `model.py`.

A tiny safetensors parser is used on purpose: `safetensors.numpy` cannot represent bfloat16,
and this avoids a torch dependency on the training hosts. Format: 8-byte little-endian header
length, JSON header, raw tensor bytes.
"""
from __future__ import annotations

import glob
import json
import os
import struct
from typing import Any, Dict

import ml_dtypes
import numpy as np

from .model import ModelConfig

_DT = {"F32": np.float32, "F16": np.float16, "BF16": ml_dtypes.bfloat16, "I64": np.int64, "I32": np.int32}
_DT_REV = {np.dtype(v): k for k, v in _DT.items()}


def read_safetensors(path: str) -> Dict[str, np.ndarray]:
    out = {}
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(n))
        base = 8 + n
        for name, meta in header.items():
            if name == "__metadata__":
                continue
            s, e = meta["data_offsets"]
            f.seek(base + s)
            out[name] = np.frombuffer(f.read(e - s), dtype=_DT[meta["dtype"]]).reshape(meta["shape"])
    return out


def write_safetensors(path: str, tensors: Dict[str, np.ndarray]) -> None:
    header, off = {}, 0
    for k, v in tensors.items():
        nb = v.nbytes
        header[k] = {"dtype": _DT_REV[v.dtype], "shape": list(v.shape), "data_offsets": [off, off + nb]}
        off += nb
    hb = json.dumps(header).encode()
    hb += b" " * ((8 - len(hb) % 8) % 8)
    with open(path, "wb") as f:
        f.write(struct.pack("<Q", len(hb))); f.write(hb)
        for v in tensors.values():
            f.write(np.ascontiguousarray(v).tobytes())


def read_hf_dir(d: str) -> Dict[str, np.ndarray]:
    files = sorted(glob.glob(os.path.join(d, "*.safetensors")))
    assert files, f"no .safetensors files in {d}"
    tensors: Dict[str, np.ndarray] = {}
    for f in files:
        tensors.update(read_safetensors(f))
    return tensors


_PROJ = {"q": "self_attn.q_proj", "k": "self_attn.k_proj", "v": "self_attn.v_proj", "o": "self_attn.o_proj",
         "gate": "mlp.gate_proj", "up": "mlp.up_proj", "down": "mlp.down_proj"}


def hf_to_params(t: Dict[str, np.ndarray], cfg: ModelConfig) -> Dict[str, Any]:
    dt = cfg.jdtype
    cast = lambda a: np.asarray(a).astype(dt)
    L = cfg.layers
    stack = lambda fmt, tr=False: np.stack([cast(t[fmt.format(i)].T if tr else t[fmt.format(i)]) for i in range(L)])
    layers = {"ln1": stack("model.layers.{}.input_layernorm.weight"),
              "ln2": stack("model.layers.{}.post_attention_layernorm.weight")}
    for n, p in _PROJ.items():
        layers[f"{n}_w"] = stack("model.layers.{}." + p + ".weight", tr=True)  # HF is [out,in]; we use [in,out]
    if cfg.qkv_bias:
        for n in ("q", "k", "v"):
            layers[f"{n}_b"] = stack("model.layers.{}." + _PROJ[n] + ".bias")
    base = {"embed": cast(t["model.embed_tokens.weight"]), "layers": layers, "final_ln": cast(t["model.norm.weight"])}
    if not cfg.tie_embeddings:
        base["lm_head"] = cast(t["lm_head.weight"]).T
    return base


def params_to_hf(base: Dict[str, Any], cfg: ModelConfig) -> Dict[str, np.ndarray]:
    """Inverse mapping (used by tests to prove the loader round-trips)."""
    a = lambda x: np.asarray(x)
    t = {"model.embed_tokens.weight": a(base["embed"]), "model.norm.weight": a(base["final_ln"])}
    for i in range(cfg.layers):
        t[f"model.layers.{i}.input_layernorm.weight"] = a(base["layers"]["ln1"][i])
        t[f"model.layers.{i}.post_attention_layernorm.weight"] = a(base["layers"]["ln2"][i])
        for n, p in _PROJ.items():
            t[f"model.layers.{i}.{p}.weight"] = np.ascontiguousarray(a(base["layers"][f"{n}_w"][i]).T)
        if cfg.qkv_bias:
            for n in ("q", "k", "v"):
                t[f"model.layers.{i}.{_PROJ[n]}.bias"] = a(base["layers"][f"{n}_b"][i])
    if not cfg.tie_embeddings:
        t["lm_head.weight"] = np.ascontiguousarray(a(base["lm_head"]).T)
    return t


def load_hf_model(d: str, dtype: str = "bfloat16"):
    cfg = ModelConfig.from_hf_config(os.path.join(d, "config.json"), dtype=dtype)
    return cfg, hf_to_params(read_hf_dir(d), cfg)
