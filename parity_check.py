"""Verify the JAX model matches Hugging Face on REAL weights. Run once where torch+transformers and the weights exist.

    python parity_check.py --model-dir ~/models/Qwen2.5-1.5B --dtype float32

Not run in the sandbox this repo was written in (no network to the HF hub, no torch). Until it passes on your
machine, the JAX architecture is verified only against its own invariants, not against HF's implementation.
"""
import argparse, os
import numpy as np, jax, jax.numpy as jnp
from jaxft.hf_io import load_hf_model
from jaxft.model import LoraConfig, forward, logits_fn

p = argparse.ArgumentParser(); p.add_argument("--model-dir", required=True)
p.add_argument("--dtype", default="float32", choices=["float32", "bfloat16"]); p.add_argument("--prompt", default="Instruction: say hi\nResponse:")
a = p.parse_args(); d = os.path.expanduser(a.model_dir)

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
tok = AutoTokenizer.from_pretrained(d); ids = tok(a.prompt, return_tensors="pt")["input_ids"]
hf = AutoModelForCausalLM.from_pretrained(d, torch_dtype=getattr(torch, a.dtype)).eval()
with torch.no_grad(): ref = hf(ids).logits.float().numpy()

cfg, base = load_hf_model(d, dtype=a.dtype)
h = forward(base, {}, jnp.asarray(ids.numpy(), jnp.int32), cfg, LoraConfig(targets=()), attn_impl="xla")
got = np.asarray(logits_fn(base, h, cfg))
diff = np.abs(got - ref)
print(f"dtype={a.dtype} max_abs_logit_diff={diff.max():.3e} mean_abs={diff.mean():.3e} argmax_match={(got.argmax(-1)==ref.argmax(-1)).mean():.3f}")
tol = 2e-3 if a.dtype == "float32" else 0.25
raise SystemExit(0 if diff.max() < tol and (got.argmax(-1) == ref.argmax(-1)).all() else 1)
