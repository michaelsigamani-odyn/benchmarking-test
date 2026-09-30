# DGX Spark Qwen Benchmark Points (1-4)

Scope: CUDA-only framework comparison on two DGX Spark hosts (`michael@odyn-dgx1`, `michael@odyn-dgx3`).

This plan does not answer mixed-vendor synchronous training. CUDA+ROCm in one all-reduce step is not a supported production path. Use relay/checkpoint-transfer for cross-vendor studies.

## Preflight gates (must pass before the sweep)

1. JAX runtime works on DGX Spark (GB10, aarch64): single-step compile and execute on both hosts.
2. Identical precision policy across frameworks (`bf16` or `fp16`) and identical LoRA config.
3. Equivalent attention path across frameworks (no FlashAttention vs naive mismatch).
4. Data order and seeds pinned; deterministic flags recorded.
5. Memory-fit probe per point and mode (1-node LoRA, 2-node LoRA, 2-node sharded):
   - load model + optimizer + one forward/backward microstep,
   - record framework peak allocation and host unified-memory pressure,
   - mark each mode as `fits` or `does_not_fit` before benchmarking.
6. Fabric validation and ceiling measurement:
   - run `nccl-tests` (`all_reduce_perf`) on the 2-node pair and record achieved bandwidth/latency,
   - record NCCL transport details and confirm no socket fallback,
   - collect NCCL debug logs (`NCCL_DEBUG=INFO`) for benchmark runs.

## Benchmark points

| Point | Model | Train mode | Parallelism strategy | Node mode to test | Intent | Per-device batch | Seq len | Steps (warmup+measure) |
|---|---|---|---|---|---|---:|---:|---:|
| 1 | `Qwen/Qwen2.5-1.5B` | LoRA | data parallel | 1-node then 2-node | framework baseline and runtime sanity | 2 | 1024 | 20 + 80 |
| 2 | `Qwen/Qwen2.5-7B` | LoRA | data parallel | 1-node then 2-node | scaling floor with light gradient traffic | 1 | 2048 | 20 + 80 |
| 3 | `Qwen/Qwen2.5-14B` | LoRA | sharded (FSDP/tensor-parallel equivalent) | 1-node then 2-node if fit | interconnect pressure under model-state exchange | 1 | 2048 | 20 + 60 |
| 4 | `Qwen/Qwen2.5-32B` | LoRA first, full-tune optional | sharded (required) | decided by preflight fit matrix | largest practical stage stress | 1 | 2048 | 20 + 40 |

Notes:
- `Qwen/Qwen2.5-7B` has prior single-node evidence in-repo: `artifacts/single-dgx3-qwen7b-20260907-062333/run_summary_dgx3.json`.
- Point 4 is not assumed 2-node by default. If 32B LoRA fits on 1 node per preflight, run both 1-node and 2-node baselines.
- If 32B does not fit on 1 node, point 4 becomes a two-node-only framework comparison and must be reported with that limitation.
- If 32B is unavailable or unstable, fallback is `Qwen/Qwen2.5-14B` at `seq_len=4096` with sharded parallelism.
- For sharded points, match equivalent sharding policy across frameworks (full parameter sharding / ZeRO-3 class behavior) and log per-step collective bytes + collective count to confirm comparable communication work.

## Measurement outputs (required per run)

1. Steady-state step time: p50, p95, standard deviation.
2. Throughput: tokens/s measured only on post-warmup window.
3. Startup cost: first-step latency and compile time reported separately.
4. Memory: framework-level peak allocation (not only `nvidia-smi`).
5. Power/thermal: board power and clocks sampled during measured window.

## Numerical validity controls

1. Create LoRA adapter initialization once, persist it, and load identical adapter weights in both frameworks.
2. Materialize one fixed token-batch order for the run and feed exactly the same batch sequence to both frameworks.
3. Match optimizer and schedule details: AdamW epsilon, weight decay, gradient clipping, LR schedule, and master-weight precision policy.
4. Compare first N-step loss traces between frameworks per point using the fixed initialization and fixed data order.
5. Record max/median absolute loss delta over the first N measured steps.
6. Pre-register tolerance before runs:
   - compute PyTorch-only run-to-run baseline at each point,
   - accept JAX-vs-PyTorch if loss-gap metric is within that baseline envelope,
   - reject speed claims when gap exceeds envelope.
7. Record attention-kernel mapping per run and reject parity comparisons with mismatched attention classes.

## Throughput decision rule

1. Primary claim: JAX is faster at a benchmark point only if JAX worst-repeat tokens/s > PyTorch best-repeat tokens/s.
2. Secondary claim: if primary rule is not met, require JAX median speedup >= max(5%, observed spread threshold) for a qualified win.
3. Baseline variants: run PyTorch eager and PyTorch `torch.compile`; compare JAX against the stronger PyTorch result.

## Run protocol

1. For points 1-3, run 1-node and 2-node for both PyTorch and JAX (only modes marked `fits` in preflight).
2. For point 4, run all modes marked `fits`; if only 2-node fits, report as two-node-only.
3. Interleave framework order (ABBA or randomized blocks) to reduce thermal/load bias.
4. Execute at least 3 repeats each; use 5 repeats for points where medians are within the observed 3-run spread.
5. Report median, p95, min-max range, and spread; do not claim wins smaller than observed spread.
6. Save all raw JSON/CSV outputs under `artifacts/benchmarks/dgxspark_qwen/point_{1..4}/`.
7. Report Spark-specific conclusions only; do not generalize to A100 racks.
8. Log ambient temperature, GPU clocks, and board power for every repeat.

## Fit definition on unified memory

A mode is marked `fits` only if it completes the full warmup + measured steps at target sequence length and batch size with no swap-thrash symptoms and with >=10% memory headroom retained through steady state.

## Pre-registration process

Before the first measured run:

1. Commit this spec and the JSON run matrix.
2. Record the commit hash in the benchmark output root metadata.
3. Treat any subsequent protocol change as an explicit dated amendment.

## Command entrypoints in this repo

- PyTorch reference microbenchmark: `scripts/lora_reference.py`
- Distributed JAX Dagster flow: `dagster_jax_distributed.py`
- Ray distributed runtime config: `configs/ray_distributed_jax_dgxspark.json`

Use the same benchmark tuple per point across both frameworks: `(model_id, batch_size, seq_len, steps, warmup_steps, dtype, lora config)`.
