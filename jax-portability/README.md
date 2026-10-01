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

## MoE support (Qwen-style and others)

Families: `qwen2_moe` (Qwen1.5-MoE, shared expert + sigmoid gate), `qwen3_moe` (Qwen3-30B-A3B family, per-head QK-norm),
`mixtral`, `olmoe`. Anything else (mixed dense/MoE stacks, sliding-window attention, `clip_qkv`, DeepSeek-style MLA) raises
`NotImplementedError` instead of loading wrongly.

**Sizes** (computed from the real `config.json`s; the totals reproduce the vendor's published counts, which is tested):

| | Qwen1.5-MoE-A2.7B | Qwen3-30B-A3B |
|---|---|---|
| experts / top-k / shared | 60 / 4 / yes (5632) | 128 / 8 / no |
| params total / active | 14.3B / 2.7B | 30.5B / 3.3B |
| bf16 base weights | ~26.7 GiB | ~56.9 GiB |
| LoRA r=8, attention only (q,k,v,o) | 3.1M | 6.7M |
| LoRA r=8, attention + every routed expert | 122.6M (~1.8 GiB fp32 w/ grads+Adam) | 421.9M (~6.3 GiB) |

Each host must hold the **whole bf16 base plus activations on one device** (no expert parallelism / sharding here). Check the
Radeon's VRAM before choosing Qwen3-30B-A3B; `story3_qwen15_moe_preregistration.json` (the smaller model) is the default for that reason.
For a first hardware smoke test drop the `e_*` targets from the config (attention-only) to isolate ragged-GEMM problems.

**Design decisions**
* *Router frozen, computed in fp32.* Fine-tuning the router changes routing itself, a different experiment. fp32 means fewer
  numerically-induced expert flips than a bf16 router, but differs slightly from HF's bf16 gate in bf16 mode.
* *Dropless dispatch.* No capacity factor and no token dropping (that would make results depend on batch composition). Tokens are
  sorted by expert and run through `jax.lax.ragged_dot`; results are un-sorted with a gather and combined in a fixed order.
* *LoRA targets.* `q,k,v,o`; `e_gate,e_up,e_down` (a separate rank-r adapter for every routed expert); `s_gate,s_up,s_down` (shared expert).
  Dense names (`gate/up/down`) on a MoE model are rejected with a hint.
* *Loss.* `loss` in every trace is the **task CE only**; the objective adds `aux_coef * balance + z_coef * z-loss`. Padding is excluded
  from the balance loss. With a frozen router the balance loss acts only through hidden states, so treat it mostly as a monitor.
* *Lazy weight loading.* Tensors are read one at a time into preallocated stacks, so loading does not need 2x the checkpoint in RAM
  (still needs 1x on the host, then the device).

**Why routing gets its own validation.** Top-k selection is discontinuous: a rounding-level difference between platforms can flip which
experts a token uses, changing its output by a finite amount. Every leg therefore saves a *routing probe* (chosen experts + logit margin
of each decision on a fixed batch) at the leg boundaries, and the report adds, per MoE leg:
* same platform: expert choices must be **identical** to the uninterrupted reference (H2);
* cross platform: disagreement must stay within `floor_mult` x the disagreement between the reference and ulp-perturbed same-platform runs (H4);
* for any flips, the report shows where they sit in the margin distribution (near-ties vs genuine divergence).

On the tiny random-weight test model a 1e-7 init perturbation flipped ~0.4% of routing decisions (15/4056) and moved the loss by ~1e-3,
so the routing noise floor is not zero. That model has many near-tied routers; do not extrapolate the number to real Qwen weights.

## Verified in this sandbox (CPU only, 1 core) vs not verified

Verified (`pytest tests`, see the count at the bottom of this section):
* `train 0->12` equals `train 0->6, checkpoint, restore, train 6->12` **bitwise** for dense **and** MoE (params, per-expert LoRA, Adam state,
  every loss/aux value, and every recorded expert choice).
* Dropless grouped-GEMM dispatch equals a slow all-experts oracle (forward ~5e-7, gradients ~2e-8), with LoRA on routed and shared experts.
* Balance loss equals an independent NumPy transcription of the HF formula (written from my memory of that function, not run against HF),
  including padding masked; padded tokens do not change it.
* Real Qwen1.5-MoE-A2.7B and Qwen3-30B-A3B `config.json` values (copied from the HF pages) parse, and the derived parameter counts match the
  published 14.3B/2.7B and 30.5B/3.3B. The Qwen1.5 config carries `sliding_window=32768` with `use_sliding_window=false`; the guard accepts it.
* Loader round-trips all four families' tensor layouts (against this repo's own writer), names the exact missing tensor, refuses unsupported architectures.
* Checkpoint corruption, identity drift (`total_steps`, seed, lr, `aux_coef`, `moe_impl`, `z_coef`), silent-CPU-fallback, mislabelled vendors,
  missing/NaN routing evidence all fail loudly; verdict never claims cross-vendor from CPU legs.
* Relay harness + Dagster graph (reference, noise floor incl. routing floor, relays, report, 3 asset checks) on CPU with local transport.

**Not verified — you must run these:**
* Anything on a real GPU. NVIDIA (GB10/A100) and AMD (ROCm) are untested, including `jax.lax.ragged_dot` speed/behaviour on ROCm,
  `--xla_gpu_deterministic_ops` there, and whether the `vendor` classification strings match your hosts (raw strings are in every report).
* **Tensor names for real checkpoints.** The naming (`mlp.experts.N.gate_proj`, `mlp.shared_expert_gate`, `block_sparse_moe.experts.N.w1`, ...)
  is from my recollection; I could not read the real `model.safetensors.index.json`. A wrong name raises `KeyError` naming the tensor.
* **Numerical parity with Hugging Face.** `python parity_check.py --model-dir ~/models/Qwen1.5-MoE-A2.7B --dtype float32` compares final logits and,
  for MoE, every layer's router logits and top-k sets. Not run here (no torch, no hub access). Until it passes, the architecture is verified
  against its own invariants and published parameter counts only. The Qwen3 excerpt I read did not show `vocab_size` / `tie_word_embeddings`;
  the test fixture uses 151936 / false from memory. The loader reads them from your real `config.json`.
* `SshTransport` (written, never executed).
* Python/JAX: JAX needs Python >= 3.12; the AMD host in your logs ran Python 3.14.4, for which I did not check wheel availability. Use the same
  Python minor and the same `jax`/`jaxlib` on both hosts (the report flags mismatches).
* Base weights are hashed each leg (`--no-hash-base` skips it): sha256 over ~27-57 GiB takes minutes; skipping it means a changed base is no longer detected.

Result of the last full run in this sandbox: **51 passed** (16 dense in `tests/test_jaxft.py`, 35 MoE in `tests/test_moe.py`), 7m37s on one CPU core.

## Run (Qwen MoE)

```bash
# once, on one machine (identical token ids everywhere); needs `transformers` and the tokenizer files
python prepare_data.py --jsonl data/story3_dataset.jsonl --out data/story3_qwen15moe_tokens.npz \
       --tokenizer Qwen/Qwen1.5-MoE-A2.7B --max-len 128
python parity_check.py --model-dir ~/models/Qwen1.5-MoE-A2.7B --dtype float32        # host with torch+HF; downloads/uses the real weights
# put code + data + model on both hosts (requirements-{nvidia,amd}.txt), then commit the prereg file and:
python harness.py --plan experiments/story3_qwen15_moe_preregistration.json --run-dir runs/qwen15moe --transport ssh
# bigger: experiments/story3_qwen3_30b_a3b_preregistration.json (needs ~57 GiB for the bf16 base on EVERY host)
```
`report.json` per relay leg now also contains `*_routing_vs_reference` checks; the dagster graph adds a `routing_checks_pass` asset check.

## Run (dense, unchanged)

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

## Scope and next steps
Single device, short horizon, one model. Not evidence for multi-GPU, tensor parallelism, larger models, or long runs.
Natural extensions: Grain for multi-host data loading, `Mesh`/`NamedSharding` with Orbax resharding on restore, all-linear LoRA / rsLoRA
(already switchable in `LoraConfig`), fp32 "golden" reference leg, and Tunix/MaxText if you want their trainers rather than this minimal one.
