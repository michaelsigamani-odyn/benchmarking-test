"""Pure-JAX decoder-only transformer with LoRA: dense (Qwen2/Qwen3/Llama-style) and MoE.

MoE families handled (see `ModelConfig.from_hf_config`): qwen2_moe, qwen3_moe, mixtral, olmoe.
NOT handled (the loader raises rather than silently mis-loading): dense-first/mixed layer stacks
(`mlp_only_layers`, `decoder_sparse_step != 1`), sliding-window attention, `clip_qkv`, MLA (DeepSeek).

Design, aimed at making training state a plain pytree and routing auditable:
  * frozen base weights: pytree of per-layer arrays stacked on a leading layer axis (bf16)
  * trainable LoRA weights: separate fp32 pytree; the router is ALWAYS frozen (fine-tuning it changes
    routing itself, which is a different experiment)
  * layers run under `jax.lax.scan`; all randomness comes from explicit keys
  * router math is done in fp32 (deliberate: fewer numerically-induced expert flips than a bf16 router;
    this differs slightly from HF's bf16 gate for bf16 models)
  * expert dispatch is DROPLESS (no capacity factor, no token dropping): tokens are sorted by expert and
    fed to a grouped GEMM (`jax.lax.ragged_dot`); results are un-sorted with a gather and combined with a
    fixed-order weighted sum, so there is no scatter-add over duplicate indices in the forward pass
  * `moe_impl="dense"` computes every expert for every token (O(E) cost): a slow oracle used by the tests
"""
from __future__ import annotations

import dataclasses
import json
import math
from typing import Any, Dict, Optional, Tuple

import jax
import jax.numpy as jnp

Array = jax.Array

ATTN_TARGETS = ("q", "k", "v", "o")
DENSE_MLP_TARGETS = ("gate", "up", "down")
EXPERT_TARGETS = ("e_gate", "e_up", "e_down")     # every routed expert gets its own rank-r adapter
SHARED_TARGETS = ("s_gate", "s_up", "s_down")     # the always-on shared expert (Qwen2-MoE)
LORA_TARGETS = ATTN_TARGETS + DENSE_MLP_TARGETS + EXPERT_TARGETS + SHARED_TARGETS

SUPPORTED_MOE = ("qwen2_moe", "qwen3_moe", "mixtral", "olmoe")


@dataclasses.dataclass(frozen=True)
class ModelConfig:
    vocab_size: int
    hidden: int
    intermediate: int                # dense MLP width (unused by MoE layers)
    layers: int
    heads: int
    kv_heads: int
    head_dim: int
    rms_eps: float = 1e-6
    rope_theta: float = 1e6
    tie_embeddings: bool = True
    qkv_bias: bool = True
    qk_norm: str = "none"            # "none" | "head" (Qwen3: RMSNorm over head_dim) | "full" (OLMoE: over the whole projection)
    dtype: str = "bfloat16"
    # ---- MoE (num_experts == 0 => dense model)
    num_experts: int = 0
    top_k: int = 0
    moe_intermediate: int = 0        # width of ONE routed expert
    shared_intermediate: int = 0     # >0 => shared expert with a sigmoid gate (Qwen2-MoE)
    norm_topk_prob: bool = True      # renormalise the selected top-k weights to sum to 1

    @property
    def jdtype(self):
        return jnp.dtype(self.dtype)

    @property
    def is_moe(self) -> bool:
        return self.num_experts > 0

    @classmethod
    def from_hf_config(cls, path_or_dict, dtype: str = "bfloat16") -> "ModelConfig":
        """Read a Hugging Face config.json instead of trusting hard-coded presets.

        Field names follow my recollection of the HF configs for these families; anything unexpected raises
        (KeyError / NotImplementedError) instead of guessing. `parity_check.py` is the real test.
        """
        c = path_or_dict
        if not isinstance(c, dict):
            with open(path_or_dict) as f:
                c = json.load(f)
        mt = c.get("model_type", "")
        heads = c["num_attention_heads"]
        if c.get("use_sliding_window") or (mt == "mixtral" and c.get("sliding_window")):
            raise NotImplementedError("sliding-window attention is not implemented")
        if c.get("clip_qkv"):
            raise NotImplementedError("clip_qkv is not implemented")
        common = dict(
            vocab_size=c["vocab_size"], hidden=c["hidden_size"], layers=c["num_hidden_layers"], heads=heads,
            kv_heads=c.get("num_key_value_heads", heads), head_dim=c.get("head_dim") or c["hidden_size"] // heads,
            rms_eps=c.get("rms_norm_eps", 1e-6), rope_theta=float(c.get("rope_theta", 1e4)),
            tie_embeddings=bool(c.get("tie_word_embeddings", False)), dtype=dtype)
        if mt in SUPPORTED_MOE:
            if c.get("mlp_only_layers") or c.get("decoder_sparse_step", 1) != 1:
                raise NotImplementedError("mixed dense/MoE layer stacks (mlp_only_layers / decoder_sparse_step) are not supported")
            k = c["num_experts_per_tok"]
            if mt == "qwen2_moe":
                return cls(**common, intermediate=c["intermediate_size"], qkv_bias=True, qk_norm="none",
                           num_experts=c["num_experts"], top_k=k, moe_intermediate=c["moe_intermediate_size"],
                           shared_intermediate=c["shared_expert_intermediate_size"], norm_topk_prob=bool(c.get("norm_topk_prob", False)))
            if mt == "qwen3_moe":
                return cls(**common, intermediate=c["intermediate_size"], qkv_bias=bool(c.get("attention_bias", False)), qk_norm="head",
                           num_experts=c["num_experts"], top_k=k, moe_intermediate=c["moe_intermediate_size"],
                           norm_topk_prob=bool(c.get("norm_topk_prob", False)))
            if mt == "mixtral":  # softmax over the top-k logits == renormalised top-k of the full softmax
                return cls(**common, intermediate=c["intermediate_size"], qkv_bias=False, qk_norm="none",
                           num_experts=c["num_local_experts"], top_k=k, moe_intermediate=c["intermediate_size"], norm_topk_prob=True)
            return cls(**common, intermediate=c["intermediate_size"], qkv_bias=bool(c.get("attention_bias", False)), qk_norm="full",  # olmoe
                       num_experts=c["num_experts"], top_k=k, moe_intermediate=c["intermediate_size"],
                       norm_topk_prob=bool(c.get("norm_topk_prob", False)))
        return cls(**common, intermediate=c["intermediate_size"], qkv_bias=(mt == "qwen2") or bool(c.get("attention_bias", False)),
                   qk_norm="head" if mt == "qwen3" else "none")


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
TINY_MOE = ModelConfig(vocab_size=272, hidden=64, intermediate=128, layers=2, heads=4, kv_heads=2, head_dim=16,
                       rope_theta=10000.0, tie_embeddings=True, qkv_bias=False, qk_norm="head",
                       num_experts=8, top_k=2, moe_intermediate=32, shared_intermediate=48, norm_topk_prob=True)


def target_shapes(cfg: ModelConfig) -> Dict[str, Tuple[int, ...]]:
    """(din, dout) per LoRA target; expert targets are per-expert matrices."""
    H, D = cfg.hidden, cfg.head_dim
    s = {"q": (H, cfg.heads * D), "k": (H, cfg.kv_heads * D), "v": (H, cfg.kv_heads * D), "o": (cfg.heads * D, H)}
    if cfg.is_moe:
        M, S = cfg.moe_intermediate, cfg.shared_intermediate
        s.update({"e_gate": (H, M), "e_up": (H, M), "e_down": (M, H)})
        if S:
            s.update({"s_gate": (H, S), "s_up": (H, S), "s_down": (S, H)})
    else:
        s.update({"gate": (H, cfg.intermediate), "up": (H, cfg.intermediate), "down": (cfg.intermediate, H)})
    return s


def count_params(cfg: ModelConfig) -> Dict[str, int]:
    """Analytic parameter counts: 'total', and 'active' per token (top_k routed experts + everything shared)."""
    L, H, D, V = cfg.layers, cfg.hidden, cfg.head_dim, cfg.vocab_size
    attn = L * (H * cfg.heads * D + 2 * H * cfg.kv_heads * D + cfg.heads * D * H)
    if cfg.qkv_bias:
        attn += L * (cfg.heads * D + 2 * cfg.kv_heads * D)
    norms = L * 2 * H + H + (L * 2 * D if cfg.qk_norm == "head" else L * (cfg.heads * D + cfg.kv_heads * D) if cfg.qk_norm == "full" else 0)
    emb = V * H * (1 if cfg.tie_embeddings else 2)
    if not cfg.is_moe:
        t = attn + norms + emb + L * 3 * H * cfg.intermediate
        return {"total": t, "active": t}
    E, M, S = cfg.num_experts, cfg.moe_intermediate, cfg.shared_intermediate
    shared = L * (3 * H * S + H) if S else 0
    common = attn + norms + emb + shared + L * H * E
    return {"total": common + L * E * 3 * H * M, "active": common + L * cfg.top_k * 3 * H * M}


def validate_targets(cfg: ModelConfig, lcfg: LoraConfig) -> None:
    valid = set(target_shapes(cfg))
    bad = [t for t in lcfg.targets if t not in valid]
    if bad:
        hint = ""
        if cfg.is_moe and any(t in DENSE_MLP_TARGETS for t in bad):
            hint = " (this is a MoE model: use e_gate/e_up/e_down for routed experts, s_* for the shared expert)"
        if not cfg.is_moe and any(t in EXPERT_TARGETS + SHARED_TARGETS for t in bad):
            hint = " (this is a dense model: use gate/up/down)"
        raise ValueError(f"LoRA targets {bad} not valid for this model; valid: {sorted(valid)}{hint}")


# ----------------------------------------------------------------------------- init


def init_base_random(key: Array, cfg: ModelConfig) -> Dict[str, Any]:
    """Random base weights (tests / smoke runs). Real runs load HF weights via hf_io."""
    L, H, D = cfg.layers, cfg.hidden, cfg.head_dim
    sh = target_shapes(cfg)
    ks = iter(jax.random.split(key, 64))

    def w(shape, std=0.02):
        return (std * jax.random.normal(next(ks), shape, jnp.float32)).astype(cfg.jdtype)

    layers = {"ln1": jnp.ones((L, H), cfg.jdtype), "ln2": jnp.ones((L, H), cfg.jdtype)}
    for n in ATTN_TARGETS:
        layers[f"{n}_w"] = w((L, *sh[n]))
    if cfg.qkv_bias:
        for n in ("q", "k", "v"):
            layers[f"{n}_b"] = w((L, sh[n][1]))
    if cfg.qk_norm == "head":
        layers["q_norm"] = jnp.ones((L, D), cfg.jdtype); layers["k_norm"] = jnp.ones((L, D), cfg.jdtype)
    elif cfg.qk_norm == "full":
        layers["q_norm"] = jnp.ones((L, sh["q"][1]), cfg.jdtype); layers["k_norm"] = jnp.ones((L, sh["k"][1]), cfg.jdtype)
    if cfg.is_moe:
        E = cfg.num_experts
        layers["router_w"] = w((L, H, E), std=0.5)  # large-ish so routing is decisive rather than near-uniform
        for n in EXPERT_TARGETS:
            layers[f"{n}_w"] = w((L, E, *sh[n]))
        if cfg.shared_intermediate:
            for n in SHARED_TARGETS:
                layers[f"{n}_w"] = w((L, *sh[n]))
            layers["s_router_w"] = w((L, H, 1))
    else:
        for n in DENSE_MLP_TARGETS:
            layers[f"{n}_w"] = w((L, *sh[n]))
    base = {"embed": w((cfg.vocab_size, H)), "layers": layers, "final_ln": jnp.ones((H,), cfg.jdtype)}
    if not cfg.tie_embeddings:
        base["lm_head"] = w((H, cfg.vocab_size))
    return base


def init_lora(key: Array, cfg: ModelConfig, lcfg: LoraConfig) -> Dict[str, Any]:
    """PEFT-style init: A ~ U(-1/sqrt(in), 1/sqrt(in)), B = 0 (adapter starts as identity). Expert targets: per-expert A/B."""
    validate_targets(cfg, lcfg)
    sh = target_shapes(cfg)
    out = {}
    for name, k in zip(sorted(lcfg.targets), jax.random.split(key, max(len(lcfg.targets), 1))):
        din, dout = sh[name]
        lead = (cfg.layers, cfg.num_experts) if name in EXPERT_TARGETS else (cfg.layers,)
        bound = 1.0 / math.sqrt(din)
        out[name] = {"a": jax.random.uniform(k, (*lead, din, lcfg.r), jnp.float32, -bound, bound),
                     "b": jnp.zeros((*lead, lcfg.r, dout), jnp.float32)}
    return out


# ----------------------------------------------------------------------------- building blocks


def rmsnorm(x: Array, w: Array, eps: float) -> Array:
    xf = x.astype(jnp.float32)
    xf = xf * jax.lax.rsqrt(jnp.mean(xf * xf, axis=-1, keepdims=True) + eps)
    return w * xf.astype(x.dtype)  # matches HF RMSNorm


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


def _dropout(x: Array, key, rate: float, train: bool) -> Array:
    if not train or rate <= 0.0:
        return x
    keep = jax.random.bernoulli(key, 1.0 - rate, x.shape)
    return jnp.where(keep, x / (1.0 - rate), 0).astype(x.dtype)


def _linear(x, w, b, lt, lcfg: LoraConfig, dkey, train: bool):
    y = x @ w
    if b is not None:
        y = y + b
    if lt is not None:
        xl = _dropout(x, dkey, lcfg.dropout, train)
        delta = (xl.astype(jnp.float32) @ lt["a"]) @ lt["b"]  # LoRA math in fp32
        y = y + (lcfg.scale * delta).astype(y.dtype)
    return y


# ----------------------------------------------------------------------------- MoE


def route(xf: Array, router_w: Array, cfg: ModelConfig):
    """fp32 router. xf [N,H] -> logits [N,E], probs [N,E], idx [N,K] (top-k on logits), weights [N,K] fp32."""
    logits = xf.astype(jnp.float32) @ router_w.astype(jnp.float32)
    probs = jax.nn.softmax(logits, axis=-1)
    _, idx = jax.lax.top_k(logits, cfg.top_k)              # ties -> lowest index first (verified on CPU)
    vals = jnp.take_along_axis(probs, idx, axis=-1)
    w = vals / jnp.sum(vals, axis=-1, keepdims=True) if cfg.norm_topk_prob else vals
    return logits, probs, idx, w


def balance_loss(probs: Array, idx: Array, valid: Array, cfg: ModelConfig):
    """Switch/HF load-balancing loss for one layer: E * sum_e f_e * P_e, over non-padding tokens.

    f_e = fraction of tokens routed to expert e (a token counts once per selected expert, so sum_e f_e = top_k),
    P_e = mean router probability. Equals HF `load_balancing_loss_func` averaged over layers. Perfect balance -> top_k.
    Gradient flows through P only (the routing decision is not differentiable).
    """
    m = valid.reshape(-1).astype(jnp.float32)
    denom = jnp.maximum(jnp.sum(m), 1.0)
    counts = jnp.sum(jax.nn.one_hot(idx, cfg.num_experts, dtype=jnp.float32), axis=1)  # [N,E] in {0,1}
    f = jnp.sum(counts * m[:, None], axis=0) / denom
    p = jnp.sum(probs * m[:, None], axis=0) / denom
    return cfg.num_experts * jnp.sum(f * p), f


def _expert_ragged(xs, gs, w, lt, lcfg, dkey, train):
    y = jax.lax.ragged_dot(xs, w, gs)
    if lt is not None:
        xl = _dropout(xs, dkey, lcfg.dropout, train).astype(jnp.float32)
        d = jax.lax.ragged_dot(jax.lax.ragged_dot(xl, lt["a"], gs), lt["b"], gs)
        y = y + (lcfg.scale * d).astype(y.dtype)
    return y


def moe_experts_ragged(xf, idx, w, lp, lo, lcfg, dkeys, train, cfg):
    """Dropless grouped-GEMM dispatch. xf [N,H], idx/w [N,K] -> [N,H] (fp32 combine)."""
    N, K, E = xf.shape[0], cfg.top_k, cfg.num_experts
    flat = idx.reshape(-1)                                          # assignment a = n*K + j
    order = jnp.argsort(flat, stable=True)                          # group assignments by expert, deterministic
    gs = jnp.bincount(flat, length=E).astype(jnp.int32)             # tokens per expert (sums to N*K: nothing dropped)
    xs = xf[order // K]
    lt = lambda n: (lo or {}).get(n)
    g = _expert_ragged(xs, gs, lp["e_gate_w"], lt("e_gate"), lcfg, dkeys["e_gate"], train)
    u = _expert_ragged(xs, gs, lp["e_up_w"], lt("e_up"), lcfg, dkeys["e_up"], train)
    y = _expert_ragged(jax.nn.silu(g) * u, gs, lp["e_down_w"], lt("e_down"), lcfg, dkeys["e_down"], train)
    y = y[jnp.argsort(order)].reshape(N, K, -1)                     # back to (token, slot) order: a gather, not a scatter-add
    return jnp.einsum("nkh,nk->nh", y.astype(jnp.float32), w).astype(xf.dtype)


def _expert_dense(x, w, lt, lcfg, spec_w, spec_a):
    y = jnp.einsum(spec_w, x, w)
    if lt is not None:
        d = jnp.einsum(spec_a[1], jnp.einsum(spec_a[0], x.astype(jnp.float32), lt["a"]), lt["b"])
        y = y + (lcfg.scale * d).astype(y.dtype)
    return y


def moe_experts_dense(xf, idx, w, lp, lo, lcfg, dkeys, train, cfg):
    """Oracle: every expert on every token, masked by the routing weights. Eval-only (no dropout)."""
    assert not (train and lcfg.dropout > 0), "moe_impl='dense' is an eval oracle; it does not implement LoRA dropout"
    N, E = xf.shape[0], cfg.num_experts
    lt = lambda n: (lo or {}).get(n)
    g = _expert_dense(xf, lp["e_gate_w"], lt("e_gate"), lcfg, "nh,ehi->nei", ("nh,ehr->ner", "ner,eri->nei"))
    u = _expert_dense(xf, lp["e_up_w"], lt("e_up"), lcfg, "nh,ehi->nei", ("nh,ehr->ner", "ner,eri->nei"))
    y = _expert_dense(jax.nn.silu(g) * u, lp["e_down_w"], lt("e_down"), lcfg, "nei,eih->neh", ("nei,eir->ner", "ner,erh->neh"))
    full = jnp.sum(jax.nn.one_hot(idx, E, dtype=jnp.float32) * w[..., None], axis=1)   # [N,E]
    return jnp.einsum("neh,ne->nh", y.astype(jnp.float32), full).astype(xf.dtype)


def moe_block(h, lp, lo, lcfg, cfg, dkeys, train, impl, valid, want_logits):
    """h [B,T,H] (post-LN) -> (out [B,T,H], per-layer stats)."""
    B, T, H = h.shape
    xf = h.reshape(B * T, H)
    logits, probs, idx, w = route(xf, lp["router_w"], cfg)
    fn = moe_experts_ragged if impl == "ragged" else moe_experts_dense
    out = fn(xf, idx, w, lp, lo, lcfg, dkeys, train, cfg)
    if cfg.shared_intermediate:
        lt = lambda n: (lo or {}).get(n)
        sg = _linear(xf, lp["s_gate_w"], None, lt("s_gate"), lcfg, dkeys["s_gate"], train)
        su = _linear(xf, lp["s_up_w"], None, lt("s_up"), lcfg, dkeys["s_up"], train)
        sh = _linear(jax.nn.silu(sg) * su, lp["s_down_w"], None, lt("s_down"), lcfg, dkeys["s_down"], train)
        gate = jax.nn.sigmoid(xf.astype(jnp.float32) @ lp["s_router_w"].astype(jnp.float32))
        out = out + (gate * sh.astype(jnp.float32)).astype(out.dtype)
    aux, f = balance_loss(probs, idx, valid, cfg)
    vf = valid.reshape(-1).astype(jnp.float32)
    z = jnp.sum(jnp.square(jax.nn.logsumexp(logits, axis=-1)) * vf) / jnp.maximum(jnp.sum(vf), 1.0)
    stats = {"aux": aux, "z": z, "load": f / cfg.top_k}          # load: share of routed assignments per expert
    if want_logits:
        stats["router_logits"] = logits.reshape(B, T, -1)
    return out.reshape(B, T, H), stats


# ----------------------------------------------------------------------------- forward


def forward_with_aux(base, lora, tokens: Array, cfg: ModelConfig, lcfg: LoraConfig, *,
                     dropout_key: Optional[Array] = None, train: bool = False, attn_impl: Optional[str] = "xla",
                     remat: bool = False, moe_impl: str = "ragged", valid: Optional[Array] = None,
                     return_router: bool = False):
    """tokens [B,T] int32 -> (hidden [B,T,H], aux) where aux holds per-layer [L,...] MoE stats ({} for dense)."""
    B, T = tokens.shape
    N, K, D = cfg.heads, cfg.kv_heads, cfg.head_dim
    x = base["embed"][tokens]
    cos, sin = rope_tables(T, D, cfg.rope_theta)
    if valid is None:
        valid = jnp.ones((B, T), jnp.bool_)
    if dropout_key is None:
        dropout_key = jax.random.key(0)
    all_names = sorted(target_shapes(cfg))                      # one key per possible target: keys are stable across LoRA configs
    layer_keys = jax.random.split(dropout_key, cfg.layers * len(all_names)).reshape(cfg.layers, len(all_names))
    kidx = {n: i for i, n in enumerate(all_names)}

    def layer(x, xs):
        lp, lo, keys = xs
        dk = {n: keys[kidx[n]] for n in all_names}

        def lin(name, hh, wname, bname=None):
            return _linear(hh, lp[wname], lp.get(bname) if bname else None, (lo or {}).get(name), lcfg, dk[name], train)

        h = rmsnorm(x, lp["ln1"], cfg.rms_eps)
        q, k, v = lin("q", h, "q_w", "q_b"), lin("k", h, "k_w", "k_b"), lin("v", h, "v_w", "v_b")
        if cfg.qk_norm == "full":                                # OLMoE: normalise the whole projection before splitting heads
            q, k = rmsnorm(q, lp["q_norm"], cfg.rms_eps), rmsnorm(k, lp["k_norm"], cfg.rms_eps)
        q, k, v = q.reshape(B, T, N, D), k.reshape(B, T, K, D), v.reshape(B, T, K, D)
        if cfg.qk_norm == "head":                                # Qwen3: per-head RMSNorm before RoPE
            q, k = rmsnorm(q, lp["q_norm"], cfg.rms_eps), rmsnorm(k, lp["k_norm"], cfg.rms_eps)
        q, k = apply_rope(q, cos, sin), apply_rope(k, cos, sin)
        a = jax.nn.dot_product_attention(q, k, v, is_causal=True, implementation=attn_impl)
        x = x + lin("o", a.reshape(B, T, N * D), "o_w")
        h = rmsnorm(x, lp["ln2"], cfg.rms_eps)
        if cfg.is_moe:
            m, stats = moe_block(h, lp, lo, lcfg, cfg, dk, train, moe_impl, valid, return_router)
        else:
            g, u = lin("gate", h, "gate_w"), lin("up", h, "up_w")
            m, stats = lin("down", jax.nn.silu(g) * u, "down_w"), {}
        return x + m, stats

    fn = jax.checkpoint(layer) if remat else layer
    x, aux = jax.lax.scan(fn, x, (base["layers"], lora, layer_keys))
    return rmsnorm(x, base["final_ln"], cfg.rms_eps), aux


def forward(base, lora, tokens: Array, cfg: ModelConfig, lcfg: LoraConfig, **kw) -> Array:
    return forward_with_aux(base, lora, tokens, cfg, lcfg, **kw)[0]


def logits_fn(base, h: Array, cfg: ModelConfig) -> Array:
    head = base["embed"].T if cfg.tie_embeddings else base["lm_head"]
    return (h @ head).astype(jnp.float32)


def loss_and_aux(base, lora, tokens, loss_mask, cfg, lcfg, *, valid=None, dropout_key=None, train=False,
                 attn_impl="xla", remat=False, moe_impl="ragged", aux_coef=0.0, z_coef=0.0):
    """Returns (objective, info). objective = CE + aux_coef*balance + z_coef*z-loss. info['ce'] is the task loss alone."""
    h, aux = forward_with_aux(base, lora, tokens, cfg, lcfg, dropout_key=dropout_key, train=train, attn_impl=attn_impl,
                              remat=remat, moe_impl=moe_impl, valid=valid)
    logits = logits_fn(base, h[:, :-1], cfg)
    labels, m = tokens[:, 1:], loss_mask[:, 1:].astype(jnp.float32)
    logp = jax.nn.log_softmax(logits, axis=-1)
    nll = -jnp.take_along_axis(logp, labels[..., None], axis=-1)[..., 0]
    ce = jnp.sum(nll * m) / jnp.maximum(jnp.sum(m), 1.0)
    info = {"ce": ce}
    total = ce
    if cfg.is_moe:
        bal, z = jnp.mean(aux["aux"]), jnp.mean(aux["z"])
        load = aux["load"]                                       # [L,E]
        info.update({"aux": bal, "z": z, "load_max": jnp.mean(jnp.max(load, axis=-1)),
                     "unused_experts": jnp.mean(jnp.sum(load == 0, axis=-1).astype(jnp.float32))})
        total = ce + aux_coef * bal + z_coef * z
    return total, info


def masked_ce_loss(base, lora, tokens, loss_mask, cfg, lcfg, **kw):
    """Task loss only (kept for callers that do not care about MoE terms)."""
    return loss_and_aux(base, lora, tokens, loss_mask, cfg, lcfg, **kw)[1]["ce"]


def routing_probe(base, lora, tokens, valid, cfg: ModelConfig, lcfg: LoraConfig, moe_impl: str = "ragged", attn_impl="xla"):
    """Expert choices on a fixed batch. Returns idx [L,B,T,K] (sorted expert ids) and margin [L,B,T] (logit gap between
    the K-th chosen and the (K+1)-th expert: how close the routing decision was to flipping)."""
    _, aux = forward_with_aux(base, lora, tokens, cfg, lcfg, train=False, moe_impl=moe_impl, valid=valid,
                              return_router=True, attn_impl=attn_impl)
    top, idx = jax.lax.top_k(aux["router_logits"], cfg.top_k + 1)
    return jnp.sort(idx[..., : cfg.top_k], axis=-1).astype(jnp.int16), (top[..., cfg.top_k - 1] - top[..., cfg.top_k])
