"""Load Hugging Face safetensors checkpoints into the stacked-layer pytree used by `model.py`.

A tiny safetensors parser is used on purpose: `safetensors.numpy` cannot represent bfloat16, and this avoids a
torch dependency on the training hosts. Format: 8-byte little-endian header length, JSON header, raw tensor bytes.

Tensors are read LAZILY (one at a time, straight from disk) and written into preallocated stacked arrays. That
matters for MoE: a 30B-class checkpoint would otherwise need ~2x its size in host RAM (all tensors + stacked copy).

Tensor-name layouts are those of the HF hub checkpoints for each family as I recall them; a missing key raises
KeyError naming the exact tensor, and `parity_check.py` compares logits against transformers on real weights.
"""
from __future__ import annotations

import glob
import json
import os
import struct
from typing import Any, Dict, Iterator, List, Tuple

import ml_dtypes
import numpy as np

from .model import ModelConfig

_DT = {"F32": np.float32, "F16": np.float16, "BF16": ml_dtypes.bfloat16, "I64": np.int64, "I32": np.int32}
_DT_REV = {np.dtype(v): k for k, v in _DT.items()}


class LazyTensors:
    """Mapping name -> np.ndarray that reads from disk on access (nothing cached)."""

    def __init__(self, files: List[str]):
        self._loc: Dict[str, Tuple[str, int, int, str, tuple]] = {}
        for path in files:
            with open(path, "rb") as f:
                n = struct.unpack("<Q", f.read(8))[0]
                header = json.loads(f.read(n))
            for name, meta in header.items():
                if name != "__metadata__":
                    s, e = meta["data_offsets"]
                    self._loc[name] = (path, 8 + n + s, e - s, meta["dtype"], tuple(meta["shape"]))

    def __contains__(self, name): return name in self._loc
    def keys(self): return self._loc.keys()

    def __getitem__(self, name: str) -> np.ndarray:
        if name not in self._loc:
            raise KeyError(f"tensor {name!r} not found in checkpoint (family layout mismatch?)")
        path, off, nbytes, dt, shape = self._loc[name]
        with open(path, "rb") as f:
            f.seek(off)
            return np.frombuffer(f.read(nbytes), dtype=_DT[dt]).reshape(shape)


def read_safetensors(path: str) -> Dict[str, np.ndarray]:
    lt = LazyTensors([path])
    return {k: lt[k] for k in lt.keys()}


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


def read_hf_dir(d: str) -> LazyTensors:
    files = sorted(glob.glob(os.path.join(d, "*.safetensors")))
    assert files, f"no .safetensors files in {d}"
    return LazyTensors(files)


# ----------------------------------------------------------------------------- per-family naming
_ATTN = {"q": "self_attn.q_proj", "k": "self_attn.k_proj", "v": "self_attn.v_proj", "o": "self_attn.o_proj"}
_DENSE = {"gate": "mlp.gate_proj", "up": "mlp.up_proj", "down": "mlp.down_proj"}


class Names:
    """Where a family keeps its MoE tensors. family is inferred from the config (see `family_of`)."""
    def __init__(self, family: str):
        self.family = family
        if family == "mixtral":
            self.router = "block_sparse_moe.gate.weight"
            self.expert = lambda j, w: f"block_sparse_moe.experts.{j}.{ {'gate': 'w1', 'up': 'w3', 'down': 'w2'}[w] }.weight"
        else:  # qwen2_moe, qwen3_moe, olmoe
            self.router = "mlp.gate.weight"
            self.expert = lambda j, w: f"mlp.experts.{j}.{w}_proj.weight"


def family_of(cfg: ModelConfig) -> str:
    """Infer the MoE family from the architecture flags (the pytree layout is the same; only names differ)."""
    if not cfg.is_moe:
        return "dense"
    if cfg.shared_intermediate:
        return "qwen2_moe"
    return {"head": "qwen3_moe", "full": "olmoe", "none": "mixtral"}[cfg.qk_norm]


def _cast(a, dt): return np.asarray(a).astype(dt)


def hf_to_params(t, cfg: ModelConfig) -> Dict[str, Any]:
    dt, L = cfg.jdtype, cfg.layers
    stack = lambda fn, tr=False: np.stack([_cast(t[fn(i)].T if tr else t[fn(i)], dt) for i in range(L)])
    layers = {"ln1": stack(lambda i: f"model.layers.{i}.input_layernorm.weight"),
              "ln2": stack(lambda i: f"model.layers.{i}.post_attention_layernorm.weight")}
    for n, p in _ATTN.items():
        layers[f"{n}_w"] = stack(lambda i, p=p: f"model.layers.{i}.{p}.weight", tr=True)   # HF is [out,in]; we use [in,out]
    if cfg.qkv_bias:
        for n in ("q", "k", "v"):
            layers[f"{n}_b"] = stack(lambda i, n=n: f"model.layers.{i}.{_ATTN[n]}.bias")
    if cfg.qk_norm != "none":
        layers["q_norm"] = stack(lambda i: f"model.layers.{i}.self_attn.q_norm.weight")
        layers["k_norm"] = stack(lambda i: f"model.layers.{i}.self_attn.k_norm.weight")
    if cfg.is_moe:
        nm, E = Names(family_of(cfg)), cfg.num_experts
        layers["router_w"] = stack(lambda i: f"model.layers.{i}.{nm.router}", tr=True)
        for w, key in (("gate", "e_gate_w"), ("up", "e_up_w"), ("down", "e_down_w")):
            first = t[f"model.layers.0.{nm.expert(0, w)}"]
            out = np.empty((L, E, first.shape[1], first.shape[0]), dtype=dt)              # [L,E,in,out]
            for i in range(L):
                for j in range(E):
                    out[i, j] = _cast(t[f"model.layers.{i}.{nm.expert(j, w)}"].T, dt)
            layers[key] = out
        if cfg.shared_intermediate:
            for w, key in (("gate", "s_gate_w"), ("up", "s_up_w"), ("down", "s_down_w")):
                layers[key] = stack(lambda i, w=w: f"model.layers.{i}.mlp.shared_expert.{w}_proj.weight", tr=True)
            layers["s_router_w"] = stack(lambda i: f"model.layers.{i}.mlp.shared_expert_gate.weight", tr=True)   # [1,H] -> [H,1]
    else:
        for n, p in _DENSE.items():
            layers[f"{n}_w"] = stack(lambda i, p=p: f"model.layers.{i}.{p}.weight", tr=True)
    base = {"embed": _cast(t["model.embed_tokens.weight"], dt), "layers": layers, "final_ln": _cast(t["model.norm.weight"], dt)}
    if not cfg.tie_embeddings:
        base["lm_head"] = _cast(t["lm_head.weight"], dt).T
    return base


def params_to_hf(base: Dict[str, Any], cfg: ModelConfig) -> Dict[str, np.ndarray]:
    """Inverse mapping (used by tests to prove the loader round-trips for every family)."""
    a = lambda x: np.asarray(x)
    T = lambda x: np.ascontiguousarray(a(x).T)
    lay = base["layers"]
    t = {"model.embed_tokens.weight": a(base["embed"]), "model.norm.weight": a(base["final_ln"])}
    for i in range(cfg.layers):
        p = f"model.layers.{i}."
        t[p + "input_layernorm.weight"], t[p + "post_attention_layernorm.weight"] = a(lay["ln1"][i]), a(lay["ln2"][i])
        for n, name in _ATTN.items():
            t[p + name + ".weight"] = T(lay[f"{n}_w"][i])
        if cfg.qkv_bias:
            for n in ("q", "k", "v"):
                t[p + _ATTN[n] + ".bias"] = a(lay[f"{n}_b"][i])
        if cfg.qk_norm != "none":
            t[p + "self_attn.q_norm.weight"], t[p + "self_attn.k_norm.weight"] = a(lay["q_norm"][i]), a(lay["k_norm"][i])
        if cfg.is_moe:
            nm = Names(family_of(cfg))
            t[p + nm.router] = T(lay["router_w"][i])
            for j in range(cfg.num_experts):
                for w, key in (("gate", "e_gate_w"), ("up", "e_up_w"), ("down", "e_down_w")):
                    t[p + nm.expert(j, w)] = T(lay[key][i, j])
            if cfg.shared_intermediate:
                for w, key in (("gate", "s_gate_w"), ("up", "s_up_w"), ("down", "s_down_w")):
                    t[p + f"mlp.shared_expert.{w}_proj.weight"] = T(lay[key][i])
                t[p + "mlp.shared_expert_gate.weight"] = T(lay["s_router_w"][i])
        else:
            for n, name in _DENSE.items():
                t[p + name + ".weight"] = T(lay[f"{n}_w"][i])
    if not cfg.tie_embeddings:
        t["lm_head.weight"] = T(base["lm_head"])
    return t


def load_hf_model(d: str, dtype: str = "bfloat16"):
    cfg = ModelConfig.from_hf_config(os.path.join(d, "config.json"), dtype=dtype)
    return cfg, hf_to_params(read_hf_dir(d), cfg)
