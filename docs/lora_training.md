# LoRA Fine-Tuning Step-Time and Memory Predictor

This document defines the additive `vidur.training` workflow for LoRA fine-tuning prediction on single-device unified-memory systems.

## Scope

- Predictor target: per-step latency and peak memory for LoRA fine-tuning.
- Device target: `dgx_spark_gb10` and `radeon_8060s`.
- Runtime target: Hugging Face `transformers` + `peft`, single device, bf16 by default.
- Out of scope: full fine-tuning, multi-GPU, QLoRA, DoRA, and scheduler integration.

## Reference run

Run reference profiling:

```bash
python -m scripts.lora_reference \
  --model-id TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --batch-size 1 \
  --seq-len 1024 \
  --lora-rank 16 \
  --lora-alpha 32 \
  --lora-target-modules q_proj,k_proj,v_proj,o_proj \
  --steps 40 \
  --warmup-steps 5 \
  --dtype bf16 \
  --output artifacts/lora_reference/tinyllama_1b.json
```

Expected metrics in output JSON:

- `step_time_ms` (excluding the first 5 warmup steps)
- `peak_memory_gb`
- `tokens_per_second`
- `attention_impl` (`flash_attention_2` or `sdpa` fallback)

## Reusing existing cross-OEM artifacts

Use existing benchmark artifacts as measured validation seeds:

```bash
PYTHONPATH=src python -m vidur.training.import_artifacts \
  --report artifacts/radeon2-to-dgxspark-qwen25-05b/cross_oem_metrics_report.json \
  --model-config configs/lora_models/tinyllama_1b.json \
  --batch-size 1 \
  --seq-len 128 \
  --rank 16 \
  --alpha 32 \
  --validation-output artifacts/lora_validation/cases_from_cross_oem.json \
  --transfer-output artifacts/lora_validation/transfer_metrics.json
```

This produces:

- validation cases with measured per-step time and peak memory for both vendors.
- transfer-path metrics (`iperf3`, `rsync`, `mooncake`) for wall-clock planning.

If `mooncake` throughput is materially lower than `rsync` and the transfer test records `backend: scp`, treat it as a fallback-path run rather than Mooncake transport evidence.

## Profiling workflow

Generate backward-aware profiles:

```bash
python -m vidur.profiling.training.cli \
  --output-dir artifacts/lora_profiles/dgx_spark \
  --device cuda \
  --dtype bf16
```

Profiler outputs:

- `profiles.csv`: per-point records with `wall_ms`, `compile_ms`, `warmup_ms`, `kernel_ms`, `residual_ms`.
- `unsupported.json`: unsupported kernel points and exception messages.

## Predictor training workflow

```bash
python -m vidur.training.train_predictors \
  --profiles artifacts/lora_profiles/dgx_spark/profiles.csv \
  --output artifacts/lora_predictor/bundle.json \
  --dgx-overhead-ms 0.0 \
  --radeon-overhead-ms 0.0
```

`dgx-overhead-ms` and `radeon-overhead-ms` are fitted constants from measured reference runs.

## Step-time model

Per-step latency is composed as:

- `forward_ms`
- `backward_ms`
- `recompute_ms` (only when gradient checkpointing is enabled)
- `optimizer_ms` (AdamW update on adapter parameters)
- `overhead_ms` (fitted fixed per-step term)

Total:

`total_step_ms = forward_ms + backward_ms + recompute_ms + optimizer_ms + overhead_ms`

For wall-clock planning with checkpoint migration:

`effective_step_ms = total_step_ms + (migration.transfer_seconds * 1000 / remaining_steps)`

Use this only when modeling a split run across hosts; keep kernel predictor training independent from transfer terms.

## Memory model

Peak memory estimate terms:

- `base_weights_gb = base_parameter_count * dtype_bytes / 2^30`
- `adapter_weights_gb = adapter_parameter_count * dtype_bytes / 2^30`
- `optimizer_states_gb = adapter_parameter_count * 8 / 2^30`
- `gradients_gb = adapter_parameter_count * dtype_bytes / 2^30`
- `activations_gb = tokens * hidden_size * num_layers * dtype_bytes * activation_factor / 2^30`
- `miscellaneous_gb = constant`

Activation factors are profiled constants for checkpointing off/on.

## Validation template

Initial measured rows from existing cross-OEM artifact import:

| device | model | batch | seq | rank | predicted step ms | measured step ms | abs err % | predicted peak GB | measured peak GB | abs err % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| radeon_8060s | TinyLlama/TinyLlama-1.1B-Chat-v1.0 | 1 | 128 | 16 | pending | 215.02 | pending | pending | 1.45 | pending |
| dgx_spark_gb10 | TinyLlama/TinyLlama-1.1B-Chat-v1.0 | 1 | 128 | 16 | pending | 130.10 | pending | pending | 1.36 | pending |

Fill predicted columns after training profile bundle creation and calibration.

```bash
PYTHONPATH=src python -m vidur.training.calibrate \
  --predictor-bundle artifacts/lora_predictor/bundle.json \
  --cases artifacts/lora_validation/cases_from_cross_oem.json \
  --output-bundle artifacts/lora_predictor/bundle_calibrated.json \
  --output-calibration artifacts/lora_validation/calibration.json

PYTHONPATH=src python -m vidur.training.validate \
  --predictor-bundle artifacts/lora_predictor/bundle_calibrated.json \
  --cases artifacts/lora_validation/cases_from_cross_oem.json \
  --output artifacts/lora_validation/validation.json

PYTHONPATH=src python -m vidur.training.report_validation \
  --validation artifacts/lora_validation/validation.json \
  --transfer artifacts/lora_validation/transfer_metrics.json \
  --output artifacts/lora_validation/validation.md
```

Targets:

- Step-time MAE <= 15%
- Peak-memory MAE <= 10%

If either target is missed, record largest error sources and keep the held-out test points unchanged.

## Feasibility check

For an intentionally OOM configuration, run predictor first and record:

- predicted `peak_memory_gb`
- device memory budget
- model feasibility flag

Then run reference training and confirm practical OOM.

## Environment capture

Record environment per device in this section after executing runs:

- Container image or venv spec
- `torch`, `transformers`, `peft` versions
- attention backend fallback behavior
- accelerator runtime notes for CUDA and ROCm

Results in this document characterize single-device unified-memory systems in the ~256-273 GB/s bandwidth class.

## Dagster remote flow

The repository exposes a remote-execution job that runs on this control machine and executes profiling/training on remote GPU hosts:

```bash
dagster job execute -f definitions.py -j lora_predictor_remote_job
```

Job stages:

- host prep and environment sync to source/target
- source train, transfer, resume, and cross-OEM metrics report
- remote kernel profiling on both hosts via `vidur.profiling.training.cli`
- local import of measured report into validation cases
- predictor training with calibration and validation markdown export

Outputs are written under:

- `artifacts/lora_profiles/<run_id>/`
- `artifacts/lora_predictor/<run_id>/`
- `artifacts/lora_validation/<run_id>/`
