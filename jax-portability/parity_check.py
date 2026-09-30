"""Verify the JAX model matches Hugging Face on REAL weights (dense or MoE). Run once where torch+transformers and the weights exist.

    python parity_check.py --model-dir ~/models/Qwen1.5-MoE-A2.7B --dtype float32

Checks final logits, and for MoE also each layer's router logits and top-k expert sets (best effort: some transformers
versions do not return router logits; that is reported, not silently skipped). NOT run in the sandbox this repo was
written in (no torch, no HF hub access): until it passes on your machine, the architecture is verified against its own
invariants and against published parameter counts, not against Hugging Face's implementation.

fp32 is the meaningful mode. In bf16 HF computes the router linear in bf16 while this code uses fp32 (deliberately), so
expert choices can legitimately differ on near-ties; use --dtype bfloat16 only as a smoke test.
"""
import argparse, os
import numpy as np, jax, jax.numpy as jnp
from jaxft.hf_io import load_hf_model
from jaxft.model import LoraConfig, forward_with_aux, logits_fn

p = argparse.ArgumentParser(); p.add_argument("--model-dir", required=True)
p.add_argument("--dtype", default="float32", choices=["float32", "bfloat16"]); p.add_argument("--prompt", default="Instruction: say hi\nResponse:")
p.add_argument("--min-topk-agreement", type=float, default=0.999)
a = p.parse_args(); d = os.path.expanduser(a.model_dir)

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
tok = AutoTokenizer.from_pretrained(d); ids = tok(a.prompt, return_tensors="pt")["input_ids"]
hf = AutoModelForCausalLM.from_pretrained(d, torch_dtype=getattr(torch, a.dtype)).eval()
cfg, base = load_hf_model(d, dtype=a.dtype)
with torch.no_grad():
    out = hf(ids, output_router_logits=True) if cfg.is_moe else hf(ids)
ref = out.logits.float().numpy()

h, aux = forward_with_aux(base, {}, jnp.asarray(ids.numpy(), jnp.int32), cfg, LoraConfig(targets=()), attn_impl="xla", return_router=cfg.is_moe)
got = np.asarray(logits_fn(base, h, cfg)); diff = np.abs(got - ref)
tol = 2e-3 if a.dtype == "float32" else 0.25
ok = diff.max() < tol and (got.argmax(-1) == ref.argmax(-1)).all()
print(f"dtype={a.dtype} final logits: max_abs_diff={diff.max():.3e} mean_abs={diff.mean():.3e} argmax_match={(got.argmax(-1)==ref.argmax(-1)).mean():.3f}")

if cfg.is_moe:
    hr = getattr(out, "router_logits", None)
    if not hr:
        print("router logits: transformers did not return them (version difference?) -> router parity NOT checked")
    else:
        agree = []
        for L, r in enumerate(hr):
            r = r.float().numpy().reshape(ids.shape[0], ids.shape[1], -1); mine = np.asarray(aux["router_logits"][L])
            ta, tb = np.sort(np.argsort(-r, -1)[..., : cfg.top_k], -1), np.sort(np.argsort(-mine, -1)[..., : cfg.top_k], -1)
            agree.append(float((ta == tb).all(-1).mean()))
            print(f"  layer {L:2d}: router logit max_abs_diff={np.abs(r - mine).max():.3e}  top-{cfg.top_k} set agreement={agree[-1]:.3f}")
        ok = ok and min(agree) >= a.min_topk_agreement
print("PARITY", "OK" if ok else "FAILED")
raise SystemExit(0 if ok else 1)
