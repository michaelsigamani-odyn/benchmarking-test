# claims_check

## Regression checks
- Mode: warn
- Failed checks:
  - Missing expected Qwen token_count=287860
  - Missing expected Qwen token_count=2854762

| Claim | Status | Reason |
|---|---|---|
| "$4 per job" and "2.3x to 118x cheaper" | NOT SUPPORTED | Minimum charge is not a per-token list-rate comparison. |
| "First token 2 to 6x sooner" | NEEDS RE-RUN | Together TTFT includes network RTT unless corrected with colocated measurement. |
| "Together sooner only on 27B 10k" | NOT SUPPORTED | Current evidence indicates gpt-oss 5k exceptions as well. |


## Claim safety (auto-generated)
- Policy: claims default to downgraded; upgrade requires CLI_VERIFIED support rows and n >= 3.
- Qwen turnaround claim evidence quality: DOWNGRADED_UNVERIFIED_OR_INSUFFICIENT_N
- Excluded jobs from claim ranges:
- ft-13dd5f5f-d688 (openai/gpt-oss-20b 1k): 1k step-floor pattern (steps far above expected-at-batch8)
- ft-800f78cc-228c (openai/gpt-oss-20b 1k): 1k step-floor pattern (steps far above expected-at-batch8)
- ft-d3580354-5bff (openai/gpt-oss-20b 1k): 1k step-floor pattern (steps far above expected-at-batch8)
- ft-1fce124e-17b1 (openai/gpt-oss-20b 1k): 1k step-floor pattern (steps far above expected-at-batch8)
- ft-c8bfe61e-9d76 (openai/gpt-oss-20b 1k): 1k step-floor pattern (steps far above expected-at-batch8)
- ft-bcf4ff51-89fc (Qwen/Qwen3.5-9B 5k): different max_seq_length (65536)
- Note: claims based on WORKBOOK_UNVERIFIED rows remain downgraded.
