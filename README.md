# JAX cross-vendor checkpoint-portability test (port of `dagster-test-flow`)

Same question as the PyTorch repo — *can LoRA fine-tuning be checkpointed on one GPU vendor and resumed on another?* —
rebuilt on JAX (pure-JAX model, Optax, Orbax) with the experiment redesigned so the answer is checkable.

## What I found in the original repo (and why the design changed)

Read from the uploaded files; none of this was re-executed.

1. **The "AMD" leg never used an AMD GPU.** `repo_config.json` sets `amd_use_gpu: false` (trains with `CUDA_VISIBLE_DEVICES=''`), and
   `checkpoint_meta.json` records `"device": "cpu"`. In the Story-3 log, `odyn-radeon2` reports `torch 2.13.0+cu130`, `hip_version: null`,
   `cuda_available: false` (a CUDA wheel on an AMD box cannot use the GPU). The passing result is CPU→GB10 evidence, not ROCm→CUDA.
2. **Story 3 recorded 0/3 trials passed**, all infrastructure failures (SSH timeouts / connection resets). One died at step 32/45 running
   on CPU at 10–23 s/step over a foreground SSH session.
3. **The LR schedule appears to change at every hand-off.** Legs are launched with `--max-steps = leg end` (e.g. 100 then 30; 30/45/60), and
   the linear schedule is rebuilt from that horizon. The Story-3 log even shows Trainer warning `save_steps: 45 != 30` on resume. Cross and control
   runs share this quirk (so their comparison is internally consistent), but neither equals an uninterrupted run.
4. **The loss checks cannot fail.** Losses at batch size 1 span 1.15–2.76 (std 0.42; largest step-to-step jump 1.43). `max_loss_delta = 2.0`
   exceeds every observed jump, and the checked pair (step 10 vs step 30) differs by 0.23.
5. **"Continuity" is satisfied by restored history.** The resumed summary's `first_logged_step` is 1 because Trainer restores `log_history`.
6. **Optimizer check compares one norm.** Equal `exp_avg_sq` norms do not imply equal state (see `test_norm_check_is_blind_...`).
7. **Credentials in the repo:** `repo_config.json` holds `ssh_password` in plaintext, and the harness passes it via `sshpass -p` (visible in `ps`)
   and pipes it to `sudo`. If that password is used anywhere real, rotate it. This port is key-only (`BatchMode=yes`).

## What "state of the art" means here

Not a new algorithm: the practices that make a resume *verifiable*.

| Concern | PyTorch/HF version | This version |
|---|---|---|
| Training state | optimizer.pt, scheduler.pt, RNG pickles, log history | one pytree `{lora, opt_state, step}`; Orbax array store (no pickle) |
| Randomness | framework RNG state (device-specific) | counter-based keys `fold_in(seed, step)`; data order = pure function of `(seed, step)` |
| LR schedule | object rebuilt per leg | pure function of `count` in `opt_state`; `total_steps` fixed in config; resume with a different identity is **refused** |
| Transfer evidence | file exists, non-zero | sha256 per file **and** canonical digest per array; restore is compared bitwise |
| Vendor claim | hostname label | runtime introspection; `--require-vendor` makes CPU fallback a hard error; verdict names only the vendors actually seen |
| Numerical claim | RMSE < 0.5 vs batch-noise | **paired** comparison on identical batches; same platform must be bitwise equal; cross-platform judged against a *measured* noise floor (ulp-scale init perturbation) |
| Long legs over SSH | foreground ssh (dropped -> failure) | remote leg detached (`nohup`) and polled; transient ssh errors retried |
| Loss | prompt + response tokens (pad id = EOS, so real EOS is also masked) | response-only by default (`--loss-on all` scores prompt too); padding is never a target, real EOS is; examples with no target token after truncation are dropped and counted (kept in, they yield a fake 0.0 loss) |

Three claims are kept separate in the report: **state transfer** (bitwise), **resume semantics** (steps/config/history), **numerical drift** (tolerance).
Data transfer in JAX runtime paths is explicit: `jax.device_put()` moves host batches/trees to accelerator memory, and `jax.device_get()` moves computed values back to host for checkpoint hashing and reporting.
Transfer validation also records throughput metrics for `device_put`, `device_get`, and a Mooncake floor benchmark (with TCP fallback when Mooncake is unavailable) so runtime transfer checks include both correctness and transport speed evidence.
Expect *not* to get bitwise equality across vendors: different GEMM/attention kernels round differently, and training amplifies that.
That is why the tolerance is measured rather than guessed.

## Verified in this sandbox (CPU only, 1 core) vs not verified

Verified (16 tests, `pytest tests`; plus a full Dagster materialization):
* `train 0->12` equals `train 0->6, checkpoint, restore, train 6->12` **bitwise** (params, optimizer state, every loss).
* Checkpoint round-trip, manifest/corruption detection, identity guard (changed `total_steps`, `seed`, `lr` refused), silent-CPU-fallback refusal,
  scoped verdicts, HF-safetensors loader round-trip, causality and LoRA-identity properties of the model.
* Relay harness + Dagster graph (reference, noise floor, 2 relays, report, 2 asset checks) with local transport. Verdict there:
  `MECHANICS_OK_NO_CROSS_VENDOR_CLAIM` — correct, because every leg was CPU.

**Not verified — you must run these:**
* Anything on a real GPU. NVIDIA (GB10/A100) and AMD (ROCm) behavior is untested, including `--xla_gpu_deterministic_ops` on ROCm and
  whether `vendor` classification strings match your hosts (raw strings are recorded in every report for audit).
* `SshTransport` (written, never executed).
* Numerical parity with Hugging Face Qwen2.5 weights: run `python parity_check.py --model-dir ... --dtype float32`. Until it passes, the
  architecture is verified against its own invariants only. Model hyper-parameters are read from `config.json`, not hard-coded.
* Python/JAX availability: JAX needs Python >= 3.12; the AMD host in your logs ran Python 3.14.4, for which I did not check wheel availability.
  Use the same Python minor and the same `jax`/`jaxlib` on both hosts (the report flags mismatches).

## Python policy

Use Python 3.12 by default for this repository. Only use a different Python minor version when it is explicitly called out for a specific task.

## Run

```bash
# once, on one machine (tokenizer -> identical token ids everywhere)
python prepare_data.py --jsonl data/story3_dataset.jsonl --out data/story3_qwen_tokens.npz --tokenizer ~/models/Qwen2.5-1.5B --max-len 128
python parity_check.py --model-dir ~/models/Qwen2.5-1.5B --dtype float32           # on a host with torch+HF
# copy code + data + model to both hosts, install requirements-{nvidia,amd}.txt in ~/jax-venv, then:
python harness.py --plan experiments/story3_jax_preregistration.json --run-dir runs/story3 --transport ssh
# or as Dagster:
JAXFT_PLAN=experiments/story3_jax_preregistration.json JAXFT_TRANSPORT=ssh dagster dev -f dagster_jax_portability.py
# CPU dry run (what was tested here):
python harness.py --plan experiments/local_dryrun_plan.json --run-dir /tmp/run --transport local
```
Commit the pre-registration file before running. Read `report.json`: `verdict.status` is one of `FAILED`,
`MECHANICS_OK_NO_CROSS_VENDOR_CLAIM`, `CROSS_VENDOR_DEMONSTRATED[_TOLERANCE_UNCALIBRATED]`.

## Ray resilient launch (coordinator + actors)

Based on NVIDIA JAX Toolbox's resilient Ray pattern, this repo now includes:

- `scripts/ray/resilient_coordinator.py` (coordinator + actor lifecycle, restart, heartbeat timeout)
- `scripts/ray/launch_ray_job.py` (Ray Jobs submission client)
- `scripts/ray/slurm_start_and_submit.sh` (SLURM cluster bring-up + Ray job submit)
- `configs/ray_resilient_local.json` (local runtime config)

Local cluster example:

```bash
python3 -m pip install "ray[default]" redis
ray start --head --port=6379 --dashboard-port=8265
export REDIS_ADDR=127.0.0.1:6380
redis-server --bind 127.0.0.1 --port 6380 --protected-mode no --daemonize yes
python3 scripts/ray/launch_ray_job.py --runtime-config configs/ray_resilient_local.json
```

SLURM cluster example:

```bash
sbatch scripts/ray/slurm_start_and_submit.sh
```

`scripts/ray/slurm_start_and_submit.sh` is now pinned to run the remote eval harness gate first
(`michael@odyn-dgx3`, `/home/michael/merlin-eval-harness`, checkpoint root `/tmp/opencode/bench`).
Override via `JAX_ZAPIER_EVAL_SSH`, `JAX_ZAPIER_EVAL_ROOT`, `JAX_ZAPIER_CHECKPOINT_ROOT`, or disable with `ZAPIER_EVAL_ENABLED=0`.

Story3 SSH preregistration via Ray job on SLURM:

```bash
sbatch --account <SLURM_ACCOUNT> --partition <SLURM_PARTITION> \
  --export=ALL,RAY_RUNTIME_CONFIG=configs/ray_resilient_story3_ssh.json \
  scripts/ray/slurm_start_and_submit.sh
```

Distributed JAX runtime check on DGX Spark + Ray (multi-process bootstrap):

```bash
sbatch --nodes=2 --account <SLURM_ACCOUNT> --partition <SLURM_PARTITION> \
  --export=ALL,RAY_ENTRYPOINT_SCRIPT=scripts/ray/distributed_jax_coordinator.py,RAY_RUNTIME_CONFIG=configs/ray_distributed_jax_dgxspark.json \
  scripts/ray/slurm_start_and_submit.sh
```

This validates `jax.distributed.initialize(...)` and cross-process collectives under Ray. It is not a full distributed training loop for `jaxft/train.py`.

Dagster flow for the same distributed bootstrap:

```bash
JAX_RAY_LAUNCH_MODE=slurm \
JAX_RAY_SLURM_FLAGS="--nodes=2 --account <SLURM_ACCOUNT> --partition <SLURM_PARTITION>" \
JAX_RAY_ENTRYPOINT_SCRIPT=scripts/ray/distributed_jax_coordinator.py \
JAX_RAY_RUNTIME_CONFIG=configs/ray_distributed_jax_dgxspark.json \
dagster dev -f dagster_jax_distributed.py
```

That Dagster flow now also runs the remote eval harness checks on `michael@odyn-dgx3` before the Ray distributed bootstrap:

- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`
- baseline benchmark at step 6, then resume to step 10

Override remote settings with `JAX_ZAPIER_EVAL_SSH`, `JAX_ZAPIER_EVAL_ROOT`, and `JAX_ZAPIER_CHECKPOINT_ROOT`.

## Scope and next steps
Single device, short horizon, one model. Not evidence for multi-GPU, tensor parallelism, larger models, or long runs.
Natural extensions: Grain for multi-host data loading, `Mesh`/`NamedSharding` with Orbax resharding on restore, all-linear LoRA / rsLoRA
(already switchable in `LoraConfig`), fp32 "golden" reference leg, and Tunix/MaxText if you want their trainers rather than this minimal one.
