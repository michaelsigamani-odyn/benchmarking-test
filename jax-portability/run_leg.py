"""Run one training leg on THIS machine. Invoked locally or over ssh by harness.py."""
import argparse, os, sys

# Must be set before jax initialises its backends. Opt-out with --no-deterministic.
if "--no-deterministic" not in sys.argv:
    os.environ.setdefault("XLA_FLAGS", "--xla_gpu_deterministic_ops=true")

import jax
from jaxft.train import TrainConfig, run_leg

p = argparse.ArgumentParser()
p.add_argument("--config", required=True)
p.add_argument("--out-dir", required=True)
p.add_argument("--end-step", type=int, required=True)
p.add_argument("--resume-from", default=None)
p.add_argument("--require-vendor", choices=["nvidia", "amd", "cpu"], default=None,
               help="fail hard unless the runtime really is this vendor (no silent CPU fallback)")
p.add_argument("--data-path", default=None, help="override data path on this host")
p.add_argument("--base-path", default=None, help="override HF model dir on this host")
p.add_argument("--probe-steps", default="", help="comma-separated steps at which to save a routing probe (MoE only)")
p.add_argument("--probe-n", type=int, default=8, help="number of fixed examples in the routing probe")
p.add_argument("--no-deterministic", action="store_true")
p.add_argument("--no-hash-base", action="store_true")
a = p.parse_args()

jax.config.update("jax_default_matmul_precision", "highest")
cfg = TrainConfig.from_json(a.config)
if a.data_path: cfg.data_path = a.data_path
if a.base_path: cfg.base = dict(cfg.base, path=a.base_path)
run_leg(cfg, a.out_dir, a.end_step, a.resume_from, a.require_vendor, hash_base=not a.no_hash_base,
        probe_steps=[int(x) for x in a.probe_steps.split(',') if x], probe_n=a.probe_n)
