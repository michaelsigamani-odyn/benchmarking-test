"""Pure-JAX decoder-only transformer (Qwen2 / Llama family) with LoRA.

Design choices, all aimed at making training state a plain pytree:
  * frozen base weights are a pytree of stacked per-layer arrays (bf16)
  * trainable LoRA weights are a separate fp32 pytree
  * layers run under `jax.lax.scan` (compile time independent of depth)
  * all randomness is derived from explicit keys (no hidden global RNG state)
"""
from __future__ import annotations

import dataclasses
import json
import math
from typing import Any, Dict, Optional, Tuple

import jax
import jax.numpy as jnp

Array = jax.Array
LORA_TARGETS = ("q", "k", "v", "o", "gate", "up", "down")


@dataclasses.dataclass(frozen=True)
class ModelConfig:
    vocab_size: int
    hidden: int
    intermediate: int
    layers: int
    heads: int
    kv_heads: int
    head_dim: int
    rms_eps: float = 1e-6
    rope_theta: float = 1e6
    tie_embeddings: bool = True
    qkv_bias: bool = True
    dtype: str = "bfloat16"

    @property
    def jdtype(self):
        return jnp.dtype(self.dtype)

    @classmethod
    def from_hf_config(cls, path_or_dict, dtype: str = "bfloat16") -> "ModelConfig":
        """Read a Hugging Face config.json instead of trusting hard-coded presets."""
        c = path_or_dict
        if not isinstance(c, dict):
            with open(path_or_dict) as f:
                c = json.load(f)
        heads = c["num_attention_heads"]
        return cls(
            vocab_size=c["vocab_size"], hidden=c["hidden_size"], intermediate=c["intermediate_size"],
            layers=c["num_hidden_layers"], heads=heads, kv_heads=c.get("num_key_value_heads", heads),
            head_dim=c.get("head_dim") or c["hidden_size"] // heads,
            rms_eps=c.get("rms_norm_eps", 1e-6), rope_theta=float(c.get("rope_theta", 1e4)),
            tie_embeddings=bool(c.get("tie_word_embeddings", False)),
            qkv_bias=c.get("model_type", "") == "qwen2" or bool(c.get("attention_bias", False)),
            dtype=dtype,
        )


@dataclasses.dataclass(frozen=True)
class LoraConfig:
    r: int = 8
    alpha: int = 16
    dropout: float = 0.05
    targets: Tuple[str, ...] = ("q", "v")
    rslora: bool = False  # scale alpha/sqrt(r) instead of alpha/r

    @property
    def scale(self) -> float:
        return self.alpha / (math.sqrt(self.r) if self.rslora else self.r)


TINY = ModelConfig(vocab_size=272, hidden=64, intermediate=128, layers=2, heads=4, kv_heads=2, head_dim=16,
                   rope_theta=10000.0, tie_embeddings=True, qkv_bias=True)


def target_shapes(cfg: ModelConfig) -> Dict[str, Tuple[int, int]]:
    H, I, D = cfg.hidden, cfg.intermediate, cfg.head_dim
    return {"q": (H, cfg.heads * D), "k": (H, cfg.kv_heads * D), "v": (H, cfg.kv_heads * D),
            "o": (cfg.heads * D, H), "gate": (H, I), "up": (H, I), "down": (I, H)}


# ----------------------------------------------------------------------------- init


def init_base_random(key: Array, cfg: ModelConfig) -> Dict[str, Any]:
    """Random base weights (tests / smoke runs). Real runs load HF weights via hf_io."""
    L, H, I, D = cfg.layers, cfg.hidden, cfg.intermediate, cfg.head_dim
    sh = target_shapes(cfg)
    ks = iter(jax.random.split(key, 16))

    def w(shape, std=0.02):
        return (std * jax.random.normal(next(ks), shape, jnp.float32)).astype(cfg.jdtype)

    layers = {
        "ln1": jnp.ones((L, H), cfg.jdtype), "ln2": jnp.ones((L, H), cfg.jdtype),
        **{f"{n}_w": w((L, *sh[n])) for n in LORA_TARGETS},
    }
    if cfg.qkv_bias:
        for n in ("q", "k", "v"):
            layers[f"{n}_b"] = w((L, sh[n][1]))
    base = {"embed": w((cfg.vocab_size, H)), "layers": layers, "final_ln": jnp.ones((H,), cfg.jdtype)}
    if not cfg.tie_embeddings:
        base["lm_head"] = w((H, cfg.vocab_size))
    return base


def init_lora(key: Array, cfg: ModelConfig, lcfg: LoraConfig) -> Dict[str, Any]:
    """PEFT-compatible init: A ~ U(-1/sqrt(in), 1/sqrt(in)), B = 0 (so the adapter starts as identity)."""
    sh = target_shapes(cfg)
    out = {}
    for name, k in zip(sorted(lcfg.targets), jax.random.split(key, len(lcfg.targets))):
        din, dout = sh[name]
        bound = 1.0 / math.sqrt(din)
        out[name] = {"a": jax.random.uniform(k, (cfg.layers, din, lcfg.r), jnp.float32, -bound, bound),
                     "b": jnp.zeros((cfg.layers, lcfg.r, dout), jnp.float32)}
    return out


# ----------------------------------------------------------------------------- forward


def rmsnorm(x: Array, w: Array, eps: float) -> Array:
    xf = x.astype(jnp.float32)
    xf = xf * jax.lax.rsqrt(jnp.mean(xf * xf, axis=-1, keepdims=True) + eps)
    return w * xf.astype(x.dtype)  # matches HF Qwen2RMSNorm


def rope_tables(T: int, D: int, theta: float) -> Tuple[Array, Array]:
    inv = 1.0 / (theta ** (jnp.arange(0, D, 2, dtype=jnp.float32) / D))
    freqs = jnp.outer(jnp.arange(T, dtype=jnp.float32), inv)
    emb = jnp.concatenate([freqs, freqs], axis=-1)
    return jnp.cos(emb), jnp.sin(emb)  # [T, D] fp32


def apply_rope(x: Array, cos: Array, sin: Array) -> Array:
    """HF rotate_half convention. x: [B,T,N,D]."""
    d = x.shape[-1] // 2
    rot = jnp.concatenate([-x[..., d:], x[..., :d]], axis=-1)
    xf = x.astype(jnp.float32)
    out = xf * cos[None, :, None, :] + rot.astype(jnp.float32) * sin[None, :, None, :]
    return out.astype(x.dtype)


def _linear(x, w, b, lt, lcfg: LoraConfig, dkey, train: bool):
    y = x @ w
    if b is not None:
        y = y + b
    if lt is not None:
        xl = x
        if train and lcfg.dropout > 0.0:
            keep = jax.random.bernoulli(dkey, 1.0 - lcfg.dropout, x.shape)
            xl = jnp.where(keep, x / (1.0 - lcfg.dropout), 0).astype(x.dtype)
        delta = (xl.astype(jnp.float32) @ lt["a"]) @ lt["b"]  # LoRA math in fp32
        y = y + (lcfg.scale * delta).astype(y.dtype)
    return y


def forward(base, lora, tokens: Array, cfg: ModelConfig, lcfg: LoraConfig, *,
            dropout_key: Optional[Array] = None, train: bool = False,
            attn_impl: Optional[str] = "xla", remat: bool = False) -> Array:
    """tokens [B,T] int32 -> final hidden states [B,T,H] (bf16)."""
    B, T = tokens.shape
    N, K, D = cfg.heads, cfg.kv_heads, cfg.head_dim
    x = base["embed"][tokens]
    cos, sin = rope_tables(T, D, cfg.rope_theta)
    n_t = len(lcfg.targets)
    if dropout_key is None:
        dropout_key = jax.random.key(0)
    layer_keys = jax.random.split(dropout_key, cfg.layers * max(n_t, 1)).reshape(cfg.layers, max(n_t, 1))
    tidx = {n: i for i, n in enumerate(sorted(lcfg.targets))}

    def layer(x, xs):
        lp, lo, keys = xs
        def lin(name, h, wname, bname=None):
            lt = lo.get(name) if lo else None
            dk = keys[tidx[name]] if name in tidx else None
            return _linear(h, lp[wname], lp.get(bname) if bname else None, lt, lcfg, dk, train)

        h = rmsnorm(x, lp["ln1"], cfg.rms_eps)
        q = lin("q", h, "q_w", "q_b").reshape(B, T, N, D)
        k = lin("k", h, "k_w", "k_b").reshape(B, T, K, D)
        v = lin("v", h, "v_w", "v_b").reshape(B, T, K, D)
        q, k = apply_rope(q, cos, sin), apply_rope(k, cos, sin)
        a = jax.nn.dot_product_attention(q, k, v, is_causal=True, implementation=attn_impl)
        x = x + lin("o", a.reshape(B, T, N * D), "o_w")
        h = rmsnorm(x, lp["ln2"], cfg.rms_eps)
        g, u = lin("gate", h, "gate_w"), lin("up", h, "up_w")
        x = x + lin("down", jax.nn.silu(g) * u, "down_w")
        return x, None

    fn = jax.checkpoint(layer) if remat else layer
    x, _ = jax.lax.scan(fn, x, (base["layers"], lora, layer_keys))
    return rmsnorm(x, base["final_ln"], cfg.rms_eps)


def logits_fn(base, h: Array, cfg: ModelConfig) -> Array:
    head = base["embed"].T if cfg.tie_embeddings else base["lm_head"]
    return (h @ head).astype(jnp.float32)


def masked_ce_loss(base, lora, tokens, loss_mask, cfg, lcfg, *, dropout_key=None, train=False,
                   attn_impl="xla", remat=False):
    """Mean next-token cross-entropy over positions where loss_mask (on the *label* token) is set."""
    h = forward(base, lora, tokens, cfg, lcfg, dropout_key=dropout_key, train=train,
                attn_impl=attn_impl, remat=remat)
    logits = logits_fn(base, h[:, :-1], cfg)
    labels = tokens[:, 1:]
    m = loss_mask[:, 1:].astype(jnp.float32)
    logp = jax.nn.log_softmax(logits, axis=-1)
    nll = -jnp.take_along_axis(logp, labels[..., None], axis=-1)[..., 0]
    return jnp.sum(nll * m) / jnp.maximum(jnp.sum(m), 1.0)
