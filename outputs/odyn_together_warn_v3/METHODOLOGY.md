# METHODOLOGY

Generated: 2026-10-10T04:57:56Z

## Regression checks
- Mode: warn
- Failures:
- Missing expected Qwen token_count=287860
- Missing expected Qwen token_count=2854762

## Safety
- Default mode runs only read-only Together CLI commands:
  - `together fine-tuning list --json`
  - `together fine-tuning retrieve <id> --json`
  - `together endpoints list --json`
  - `together endpoints retrieve <id> --json`
  - `together endpoints hardware --json`
- No fine-tune submission, endpoint creation/start, or inference traffic in default mode.

## Together pricing source
- URL: https://www.together.ai/pricing
- Retrieval timestamp: 2026-10-10T04:57:56Z

## Fine-tune formulas
- Together effective $/M tokens = `billed_usd / (tokens / 1e6)`
- Together list cost ($) = `(tokens / 1e6) * list_rate_per_million`
- Queue real minutes = `JOB_START - created_at`
- Setup minutes = `TRAINING_START - JOB_START`
- Training phase minutes = `TRAINING_COMPLETE - TRAINING_START`
- Finalise minutes = `JOB_COMPLETE - TRAINING_COMPLETE`
- Wall minutes = `updated_at - created_at`
- Setup+train minutes = `setup + training`
- Expected steps references:
  - `ceil(tokens / (effective_batch_cli * 4096))`
  - `ceil(tokens / (8 * 4096))`

## Together billing units
- Together job `total_price`/`train_price` appears to be nano-USD units.
- Conversion used: `usd = raw_price / 1_000_000_000`.

## Dataset-size mapping note
- `dataset_size` for CLI rows is inferred from token-count buckets (1k/5k/10k).

## Serving formula (reference)
- `$/M = (gpu_hourly_usd / (tokens_per_second * 3600)) * 1e6`
- Utilization-adjusted: `$/M / U`

## Assumptions / unavailable
- Endpoint precision is marked `UNAVAILABLE` unless returned by endpoint metadata.
- H100 on-demand dedicated rate extracted from pricing table: 5.49

## Fine-tune pricing rows extracted
- Count: 29
