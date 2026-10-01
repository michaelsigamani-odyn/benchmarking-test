"""Resumable LoRA training "leg".

A leg trains steps (start, end] and writes a checkpoint. Legs are designed so that

    leg(0->k) then leg(k->n)   ==   leg(0->n)

exactly (bitwise, on the same platform). That identity is what the validator tests, and it is
why `total_steps` (the LR-schedule horizon) is part of the config and NOT tied to a leg's end.
(In the PyTorch version each leg was launched with `--max-steps = leg end`, which I believe
changes the linear LR schedule at every hand-off; see README.)
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import time
from typing import Any, Callable, Dict, Optional

import jax
import jax.numpy as jnp
import numpy as np
import optax

from . import ckpt as ck
from .data import batch_for_step, load_arrays
from .device_transfer import arrays_to_device, scalar_to_host, tree_to_device
from .env import describe_env, require_vendor
from .export import export_lora_adapter
from .model import LoraConfig, ModelConfig, init_base_random, init_lora, masked_ce_loss


@dataclasses.dataclass
class TrainConfig:
    base: Dict[str, Any]                      # {"kind":"random","model":{...},"seed":0} | {"kind":"hf","path":...}
    data_path: str                            # .npz produced by prepare_data.py
    seed: int = 17
    total_steps: int = 60                     # LR-schedule horizon, constant across all legs
    batch_size: int = 1
    lr: float = 2e-4
    warmup_ratio: float = 0.03
    weight_decay: float = 0.0
    max_grad_norm: float = 1.0
    adam_b1: float = 0.9
    adam_b2: float = 0.999
    adam_eps: float = 1e-8
    lora: Dict[str, Any] = dataclasses.field(default_factory=lambda: {"r": 8, "alpha": 16, "dropout": 0.05, "targets": ["q", "v"], "rslora": False})
    attn_impl: Optional[str] = "xla"          # "xla" is portable; None lets JAX pick cuDNN flash on NVIDIA
    remat: bool = False
    init_perturb: float = 0.0                 # relative noise on LoRA-A init; used only to measure the noise floor
    init_perturb_seed: int = 0

    @classmethod
    def from_json(cls, path: str) -> "TrainConfig":
        with open(path) as f:
            return cls(**json.load(f))

    def lora_cfg(self) -> LoraConfig:
        d = dict(self.lora); d["targets"] = tuple(d.get("targets", ("q", "v")))
        return LoraConfig(**d)


def sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def identity_of(cfg: TrainConfig, data_digest: str, base_digest: str) -> Dict[str, Any]:
    """Everything that determines the training trajectory. Resuming with a different identity is refused."""
    d = dataclasses.asdict(cfg)
    d.pop("data_path"); d["base"] = {k: v for k, v in d["base"].items() if k != "path"}  # path is location, not identity
    return {"config": d, "data_digest": data_digest, "base_digest": base_digest}


def make_schedule(cfg: TrainConfig):
    warm = math.ceil(cfg.total_steps * cfg.warmup_ratio)
    return optax.join_schedules(
        [optax.linear_schedule(0.0, cfg.lr, warm), optax.linear_schedule(cfg.lr, 0.0, cfg.total_steps - warm)], [warm])


def make_optimizer(cfg: TrainConfig):
    return optax.chain(
        optax.clip_by_global_norm(cfg.max_grad_norm),
        optax.adamw(make_schedule(cfg), b1=cfg.adam_b1, b2=cfg.adam_b2, eps=cfg.adam_eps, weight_decay=cfg.weight_decay))


def load_base(cfg: TrainConfig):
    b = cfg.base
    if b["kind"] == "random":
        mcfg = ModelConfig(**b["model"])
        return mcfg, init_base_random(jax.random.key(b.get("seed", 0)), mcfg)
    if b["kind"] == "hf":
        from .hf_io import load_hf_model
        mcfg, params = load_hf_model(os.path.expanduser(b["path"]), dtype=b.get("dtype", "bfloat16"))
        return mcfg, tree_to_device(params)
    raise ValueError(f"unknown base kind {b['kind']!r}")


def tree_norm(tree) -> jax.Array:
    return jnp.sqrt(sum(jnp.sum(jnp.square(x.astype(jnp.float32))) for x in jax.tree.leaves(tree)))


def make_step_fn(cfg: TrainConfig, mcfg: ModelConfig, lcfg: LoraConfig, opt):
    schedule = make_schedule(cfg)
    root = jax.random.key(cfg.seed)

    def loss_fn(lora, base, tokens, mask, key):
        return masked_ce_loss(base, lora, tokens, mask, mcfg, lcfg, dropout_key=key, train=True,
                              attn_impl=cfg.attn_impl, remat=cfg.remat)

    @jax.jit
    def step(base, state, tokens, mask):
        n = state["step"] + 1
        key = jax.random.fold_in(root, n)  # stateless: dropout key is a function of (seed, step) only
        loss, grads = jax.value_and_grad(loss_fn)(state["lora"], base, tokens, mask, key)
        updates, opt_state = opt.update(grads, state["opt_state"], state["lora"])
        lora = optax.apply_updates(state["lora"], updates)
        new = {"lora": lora, "opt_state": opt_state, "step": n}
        return new, {"loss": loss, "grad_norm": tree_norm(grads), "lr": schedule(state["step"])}

    return step


def fresh_state(cfg: TrainConfig, mcfg: ModelConfig, lcfg: LoraConfig, opt):
    key = jax.random.fold_in(jax.random.key(cfg.seed), 0)
    lora = init_lora(key, mcfg, lcfg)
    if cfg.init_perturb:
        nk = jax.random.fold_in(jax.random.key(cfg.seed), 10**6 + cfg.init_perturb_seed)
        for i, name in enumerate(sorted(lora)):
            lora[name]["a"] = lora[name]["a"] * (1.0 + cfg.init_perturb * jax.random.normal(jax.random.fold_in(nk, i), lora[name]["a"].shape))
    return {"lora": lora, "opt_state": opt.init(lora), "step": jnp.asarray(0, jnp.int32)}


class IdentityMismatch(RuntimeError):
    pass


def run_leg(cfg: TrainConfig, out_dir: str, end_step: int, resume_from: Optional[str] = None,
            require_vendor_: Optional[str] = None, hash_base: bool = True,
            log: Callable[[str], None] = print) -> Dict[str, Any]:
    t0 = time.time()
    env = describe_env()
    require_vendor(env, require_vendor_)
    assert 0 < end_step <= cfg.total_steps, "end_step must be within the LR-schedule horizon (total_steps)"
    os.makedirs(out_dir, exist_ok=True)

    mcfg, base = load_base(cfg)
    lcfg = cfg.lora_cfg()
    arrays, data_digest = load_arrays(os.path.expanduser(cfg.data_path))
    base_digest = ck.state_digest(base)["overall"] if hash_base else "unhashed"
    identity = identity_of(cfg, data_digest, base_digest)
    identity_hash = sha(identity)
    opt = make_optimizer(cfg)
    step_fn = make_step_fn(cfg, mcfg, lcfg, opt)
    state = fresh_state(cfg, mcfg, lcfg, opt)

    restore_info: Dict[str, Any] = {"resumed": False}
    carried: list = []
    if resume_from:
        manifest = ck.verify_manifest(resume_from)
        meta = ck.read_meta(resume_from)
        if meta["identity_hash"] != identity_hash:
            raise IdentityMismatch(
                f"checkpoint identity {meta['identity_hash'][:12]} != current {identity_hash[:12]}; "
                f"refusing to resume with a different config/data/base (e.g. changed total_steps or seed).")
        state = ck.restore_checkpoint(resume_from, state)
        got = ck.state_digest(state)
        with open(os.path.join(resume_from, "digest.json")) as f:
            saved = json.load(f)
        restore_info = {
            "resumed": True, "resume_from": resume_from, "manifest_ok": manifest["ok"], "manifest": manifest,
            "restored_step": int(state["step"]), "meta_step": int(meta["step"]),
            "restored_digest": got["overall"], "saved_digest": saved["overall"],
            "roundtrip_exact": got["overall"] == saved["overall"], "leaf_diff": ck.diff_digests(saved, got),
        }
        carried = [dict(r, source="restored") for r in meta["trace"]]
    start_step = int(state["step"])
    assert start_step < end_step, f"start_step {start_step} >= end_step {end_step}"
    log(f"[leg] {env['vendor']}/{env['device_kind']} steps {start_step + 1}..{end_step} of {cfg.total_steps}")

    new_trace = []
    for s in range(start_step + 1, end_step + 1):
        tokens, mask = batch_for_step(arrays, cfg.batch_size, cfg.seed, s)
        device_tokens, device_mask = arrays_to_device(tokens, mask)
        state, m = step_fn(base, state, device_tokens, device_mask)
        new_trace.append({"step": s, "loss": scalar_to_host(m["loss"]), "grad_norm": scalar_to_host(m["grad_norm"]),
                          "lr": scalar_to_host(m["lr"]), "source": "computed"})
        log(f"[leg] step {s} loss {new_trace[-1]['loss']:.6f}")
    assert int(state["step"]) == end_step

    ckpt_dir = os.path.join(out_dir, f"ckpt-{end_step}")
    trace = [{k: r[k] for k in ("step", "loss", "grad_norm", "lr")} for r in carried + new_trace]
    digest = ck.save_checkpoint(ckpt_dir, state, {"step": end_step, "identity_hash": identity_hash,
                                                  "identity": identity, "trace": trace, "env": env})
    exported = export_lora_adapter(ckpt_dir, state["lora"], alpha=int(lcfg.alpha), rank=int(lcfg.r))
    summary = {
        "schema": "jaxft.leg/1", "env": env, "identity_hash": identity_hash, "identity": identity,
        "start_step": start_step, "end_step": end_step, "restore": restore_info,
        "trace": carried + new_trace, "ckpt_dir": ckpt_dir, "final_digest": digest["overall"],
        "adapter_export": exported,
        "seconds": round(time.time() - t0, 3),
    }
    with open(os.path.join(out_dir, "leg_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    return summary
