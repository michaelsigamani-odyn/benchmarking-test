# METHODOLOGY

Generated: 2026-10-10T04:47:22Z

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
- Retrieval timestamp: 2026-10-10T04:47:22Z

## Fine-tune formulas
- Together effective $/M tokens = `billed_usd / (tokens / 1e6)`
- Queue minutes = `started_at - created_at`
- Training minutes = `finished_at - started_at`
- Wall minutes = `finished_at - created_at`
- Expected steps reference = `ceil(tokens / (batch_size * 4096))`

## Serving formula (reference)
- `$/M = (gpu_hourly_usd / (tokens_per_second * 3600)) * 1e6`
- Utilization-adjusted: `$/M / U`

## Assumptions / unavailable
- Endpoint precision is marked `UNAVAILABLE` unless returned by endpoint metadata.
- H100 on-demand dedicated rate extracted from pricing table: 5.49

## Fine-tune pricing rows extracted
- Count: 29
