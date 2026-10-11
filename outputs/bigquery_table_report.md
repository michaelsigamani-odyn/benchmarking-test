# BigQuery Table Report (inbound-dahlia-507808-g1)

Generated: 2026-10-11T15:09:42.471333+00:00

## Dataset: `biz_ops`

### Row counts

| Table | Type | Row count |
|---|---|---:|

| `gpu_health_latest_v1` | VIEW | 0 |

| `tableau_ceo_commercial_benchmark_v1` | VIEW | 0 |

| `tableau_ceo_compute_diversity_v1` | VIEW | 0 |

| `tableau_ceo_concurrency_v1` | VIEW | 0 |

| `tableau_ceo_data_freshness_v1` | VIEW | 0 |

| `tableau_ceo_digester_evaluations_v1` | VIEW | 0 |

| `tableau_ceo_digester_pricing_accuracy_v1` | VIEW | 0 |

| `tableau_ceo_digester_runtime_accuracy_v1` | VIEW | 0 |

| `tableau_ceo_digester_vram_accuracy_v1` | VIEW | 0 |

| `tableau_ceo_fleet_machine_detail_v1` | VIEW | 0 |

| `tableau_ceo_fleet_machine_overview_v1` | VIEW | 0 |

| `tableau_ceo_fleet_summary_v1` | VIEW | 0 |

| `tableau_ceo_gpu_utilization_v1` | VIEW | 0 |

| `tableau_ceo_job_investigation_v1` | VIEW | 0 |

| `tableau_ceo_scheduler_economics_v1` | VIEW | 0 |

| `tableau_ceo_workload_failures_v1` | VIEW | 0 |

| `workload_benchmark_flat_v1` | VIEW | 0 |


### Top 3 rows per table

#### `biz_ops.gpu_health_latest_v1`

_No rows._

#### `biz_ops.tableau_ceo_commercial_benchmark_v1`

```json
[
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "cost_basis": "UNAVAILABLE_IN_GOVERNED_BIGQUERY_V1",
    "cost_per_million_tokens_usd": null,
    "dataset_ref": null,
    "limitation_reason": "Missing governed token_count + governed buyer/supplier pricing table join in current BigQuery schema.",
    "model_available_at": null,
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "provider": "odyn",
    "source_system": "eks_kuberay",
    "submitted_at": null,
    "token_count": null,
    "trainer_started_at": null,
    "training_ended_at": null,
    "training_time_min": null,
    "wall_time_min": null,
    "workload_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "workload_type": "serving"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "cost_basis": "UNAVAILABLE_IN_GOVERNED_BIGQUERY_V1",
    "cost_per_million_tokens_usd": null,
    "dataset_ref": null,
    "limitation_reason": "Missing governed token_count + governed buyer/supplier pricing table join in current BigQuery schema.",
    "model_available_at": null,
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "provider": "odyn",
    "source_system": "eks_kuberay",
    "submitted_at": null,
    "token_count": null,
    "trainer_started_at": null,
    "training_ended_at": null,
    "training_time_min": null,
    "wall_time_min": null,
    "workload_id": "92fa7793-2c1d-5b15-83e4-de59fc529c14",
    "workload_type": "serving"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "cost_basis": "UNAVAILABLE_IN_GOVERNED_BIGQUERY_V1",
    "cost_per_million_tokens_usd": null,
    "dataset_ref": null,
    "limitation_reason": "Missing governed token_count + governed buyer/supplier pricing table join in current BigQuery schema.",
    "model_available_at": null,
    "model_id": "Qwen/Qwen2.5-7B-Instruct",
    "provider": "odyn",
    "source_system": "eks_kuberay",
    "submitted_at": null,
    "token_count": null,
    "trainer_started_at": null,
    "training_ended_at": null,
    "training_time_min": null,
    "wall_time_min": null,
    "workload_id": "c2104b10-f154-53cb-9f19-4169369251b5",
    "workload_type": "serving"
  }
]
```

#### `biz_ops.tableau_ceo_compute_diversity_v1`

```json
[
  {
    "as_of_date": "2026-10-11",
    "catalog_match_confidence": "not_verified_in_hf_catalog",
    "compatibility_note": "Inventory and observation are separated: registered_hosts vs observed_hosts and expected_gpu_count vs reporting_gpu_count.",
    "compatibility_status": "UNTESTED",
    "cpu_model": "AMD Ryzen AI Max+ 395",
    "expected_gpu_count": "3",
    "gpu_architecture": "RDNA 3.5",
    "gpu_memory_type": "shared",
    "gpu_model": "Radeon 8060S",
    "gpu_model_confidence": "exact",
    "gpu_model_hf_name": null,
    "gpu_model_hf_slug": null,
    "gpu_model_raw_examples": "AMD Radeon Graphics || AMD Radeon(TM) 8060S Graphics",
    "gpu_type": "integrated",
    "observed_hosts": "3",
    "observed_samples": "3",
    "operating_system": null,
    "registered_hosts": "3",
    "reporting_gpu_count": "3",
    "runtime_backend": "UNKNOWN || ssh_powershell_wmi || ssh_rocm_smi",
    "system_model": "GMKtec EVO-X2",
    "telemetry_coverage_pct": "100.0",
    "vendor": "amd"
  },
  {
    "as_of_date": "2026-10-11",
    "catalog_match_confidence": null,
    "compatibility_note": "Inventory and observation are separated: registered_hosts vs observed_hosts and expected_gpu_count vs reporting_gpu_count.",
    "compatibility_status": "UNTESTED",
    "cpu_model": null,
    "expected_gpu_count": "2",
    "gpu_architecture": null,
    "gpu_memory_type": null,
    "gpu_model": "NVIDIA GB10",
    "gpu_model_confidence": null,
    "gpu_model_hf_name": null,
    "gpu_model_hf_slug": null,
    "gpu_model_raw_examples": "NVIDIA GB10",
    "gpu_type": null,
    "observed_hosts": "2",
    "observed_samples": "2",
    "operating_system": null,
    "registered_hosts": "2",
    "reporting_gpu_count": "2",
    "runtime_backend": "UNKNOWN",
    "system_model": null,
    "telemetry_coverage_pct": "100.0",
    "vendor": "nvidia"
  },
  {
    "as_of_date": "2026-10-11",
    "catalog_match_confidence": null,
    "compatibility_note": "Inventory and observation are separated: registered_hosts vs observed_hosts and expected_gpu_count vs reporting_gpu_count.",
    "compatibility_status": "UNTESTED",
    "cpu_model": null,
    "expected_gpu_count": "1",
    "gpu_architecture": null,
    "gpu_memory_type": null,
    "gpu_model": "UNKNOWN",
    "gpu_model_confidence": null,
    "gpu_model_hf_name": null,
    "gpu_model_hf_slug": null,
    "gpu_model_raw_examples": "UNKNOWN",
    "gpu_type": null,
    "observed_hosts": "1",
    "observed_samples": "1",
    "operating_system": null,
    "registered_hosts": "1",
    "reporting_gpu_count": "0",
    "runtime_backend": "UNKNOWN",
    "system_model": null,
    "telemetry_coverage_pct": "0.0",
    "vendor": "nvidia"
  }
]
```

#### `biz_ops.tableau_ceo_concurrency_v1`

```json
[
  {
    "concurrent_gpu_jobs": "1",
    "concurrent_users": "1",
    "metric_date": "2026-10-04",
    "ts": "2026-10-04 01:27:00"
  },
  {
    "concurrent_gpu_jobs": "0",
    "concurrent_users": "0",
    "metric_date": "2026-10-04",
    "ts": "2026-10-04 01:43:56"
  },
  {
    "concurrent_gpu_jobs": "1",
    "concurrent_users": "1",
    "metric_date": "2026-10-04",
    "ts": "2026-10-04 05:15:58"
  }
]
```

#### `biz_ops.tableau_ceo_data_freshness_v1`

```json
[
  {
    "edge_rows": "2709",
    "inspected_at": "2026-10-11 15:09:52",
    "latest_edge_sample_ts": "2026-10-11 15:09:46",
    "latest_s3_mirror_observed_at": null,
    "latest_workload_event_date": "2026-10-10",
    "latest_workload_fetched_at": "2026-10-10 20:11:45",
    "mirror_location_note": "ops_ingest.s3_mirror_daily is in US location and cannot be joined into EU governed views directly.",
    "mirror_rows": null,
    "oldest_s3_mirror_observed_at": null,
    "workload_rows": "38"
  }
]
```

#### `biz_ops.tableau_ceo_digester_evaluations_v1`

_No rows._

#### `biz_ops.tableau_ceo_digester_pricing_accuracy_v1`

```json
[
  {
    "actual_operational_cost_usd": "0.147906",
    "cost_abs_error_usd": "0.052094",
    "cost_abs_pct_error": "0.352210187551553",
    "cost_overestimate_flag": "true",
    "cost_signed_error_usd": "0.052094",
    "cost_underestimate_flag": "false",
    "estimated_total_cost_usd": "0.2",
    "expected_contribution_margin_usd": null,
    "job_id": "824f96f5-5502-56fc-b40c-c7cb5c6c6f86",
    "job_status": "completed",
    "match_status": "matched_to_job",
    "message_id": "0u6rtmSd8I",
    "missing_actual_cost": "false",
    "missing_estimated_cost": "false",
    "model_size_bucket": "Medium(7-14B)",
    "predicted_dataset_ref": "72b_alpaca_train_800.jsonl",
    "predicted_model_id": "Qwen/Qwen2.5-7B-Instruct",
    "predicted_sample_count": "800",
    "prediction_date": "2026-09-05",
    "prediction_ts": "2026-09-05 04:44:39",
    "prediction_year_week": "2026-W36",
    "pricing_accuracy_bucket": "25-50%",
    "pricing_gap_note": "Customer quote + realized sell price are not present in governed source tables for this period.",
    "quoted_customer_price_usd": null,
    "realized_contribution_margin_usd": null,
    "realized_customer_price_usd": null,
    "scheduler_status": "completed",
    "selected_gpu_count": "1",
    "selected_gpu_tier": "NVIDIA A100-SXM4-80GB",
    "selected_hourly_rate_usd": "1.5",
    "session_id": "5ddz2HwBFG",
    "workload_id": "73749f1d-930e-4a55-81fc-44bce669455f"
  },
  {
    "actual_operational_cost_usd": "0.116232",
    "cost_abs_error_usd": "0.203768",
    "cost_abs_pct_error": "1.753114460733705",
    "cost_overestimate_flag": "true",
    "cost_signed_error_usd": "0.203768",
    "cost_underestimate_flag": "false",
    "estimated_total_cost_usd": "0.32",
    "expected_contribution_margin_usd": null,
    "job_id": "c2104b10-f154-53cb-9f19-4169369251b5",
    "job_status": "completed",
    "match_status": "matched_to_job",
    "message_id": "SI6ih9MYaI",
    "missing_actual_cost": "false",
    "missing_estimated_cost": "false",
    "model_size_bucket": "Medium(7-14B)",
    "predicted_dataset_ref": "support_assistant_dpo_1100.jsonl",
    "predicted_model_id": "Qwen/Qwen2.5-7B-Instruct",
    "predicted_sample_count": "1100",
    "prediction_date": "2026-09-29",
    "prediction_ts": "2026-09-29 19:10:43",
    "prediction_year_week": "2026-W40",
    "pricing_accuracy_bucket": ">100%",
    "pricing_gap_note": "Customer quote + realized sell price are not present in governed source tables for this period.",
    "quoted_customer_price_usd": null,
    "realized_contribution_margin_usd": null,
    "realized_customer_price_usd": null,
    "scheduler_status": "completed",
    "selected_gpu_count": "1",
    "selected_gpu_tier": "NVIDIA A100-SXM4-80GB",
    "selected_hourly_rate_usd": "1.5",
    "session_id": "cQmjUoxy69",
    "workload_id": "5670a18b-8bf8-4a54-a139-1b19bb47611b"
  },
  {
    "actual_operational_cost_usd": null,
    "cost_abs_error_usd": null,
    "cost_abs_pct_error": null,
    "cost_overestimate_flag": null,
    "cost_signed_error_usd": null,
    "cost_underestimate_flag": null,
    "estimated_total_cost_usd": "0.02",
    "expected_contribution_margin_usd": null,
    "job_id": null,
    "job_status": null,
    "match_status": "unmatched_prediction",
    "message_id": "X6RcD0HB5u",
    "missing_actual_cost": "true",
    "missing_estimated_cost": "false",
    "model_size_bucket": "Small(<=1.5B)",
    "predicted_dataset_ref": "alpaca_train.jsonl",
    "predicted_model_id": "Qwen/Qwen2.5-1.5B-Instruct",
    "predicted_sample_count": "800",
    "prediction_date": "2026-09-10",
    "prediction_ts": "2026-09-10 22:54:11",
    "prediction_year_week": "2026-W37",
    "pricing_accuracy_bucket": "missing_actual_or_estimate",
    "pricing_gap_note": "Customer quote + realized sell price are not present in governed source tables for this period.",
    "quoted_customer_price_usd": null,
    "realized_contribution_margin_usd": null,
    "realized_customer_price_usd": null,
    "scheduler_status": null,
    "selected_gpu_count": null,
    "selected_gpu_tier": null,
    "selected_hourly_rate_usd": null,
    "session_id": "GEPeNXhyyu",
    "workload_id": null
  }
]
```

#### `biz_ops.tableau_ceo_digester_runtime_accuracy_v1`

```json
[
  {
    "actual_operational_cost_usd": null,
    "actual_runtime_hours": null,
    "is_oom_failure": "false",
    "job_id": null,
    "job_status": null,
    "match_status": "unmatched_prediction",
    "message_id": "X6RcD0HB5u",
    "missing_actual_runtime": "true",
    "missing_predicted_runtime": "false",
    "model_size_bucket": "Small(<=1.5B)",
    "observed_peak_vram_gb": null,
    "predicted_dataset_ref": "alpaca_train.jsonl",
    "predicted_model_id": "Qwen/Qwen2.5-1.5B-Instruct",
    "predicted_operational_cost_usd": "0.02",
    "predicted_runtime_hours": "0.0103",
    "predicted_sample_count": "800",
    "prediction_date": "2026-09-10",
    "prediction_text": "I can fine-tune **Qwen/Qwen2.5-1.5B-Instruct** on **alpaca_train.jsonl** (800 training samples) using LoRA (2 epochs, lr=1e-4, LoRA rank=8). I picked the best available Odyn placement and prepared the workload builder.\n\n_Estimated training time: \u22480.0103 hours (\u2248$0.02 total) \u2014 a rough estimate, not a quote._\n\nUse the **Open Workload Builder** button when you are ready.",
    "prediction_ts": "2026-09-10 22:54:11",
    "prediction_year_week": "2026-W37",
    "runtime_abs_error_hours": null,
    "runtime_abs_pct_error": null,
    "runtime_accuracy_bucket": "missing_actual_or_prediction",
    "runtime_overestimate_flag": null,
    "runtime_signed_error_hours": null,
    "runtime_underestimate_flag": null,
    "scheduler_status": null,
    "selected_gpu_count": null,
    "selected_gpu_tier": null,
    "selected_hourly_rate_usd": null,
    "session_id": "GEPeNXhyyu",
    "workload_id": null
  },
  {
    "actual_operational_cost_usd": null,
    "actual_runtime_hours": "0.015555555555555555",
    "is_oom_failure": "false",
    "job_id": "92cb8f5d-388d-5096-b05f-8a7bfb7008e2",
    "job_status": "failed",
    "match_status": "matched_to_job",
    "message_id": "99mstWfoy0",
    "missing_actual_runtime": "false",
    "missing_predicted_runtime": "false",
    "model_size_bucket": "Small(<=1.5B)",
    "observed_peak_vram_gb": "13.145631232",
    "predicted_dataset_ref": "poetry_target_tags_10k_alpaca.jsonl",
    "predicted_model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "predicted_operational_cost_usd": "0.04",
    "predicted_runtime_hours": "0.0226",
    "predicted_sample_count": "1110",
    "prediction_date": "2026-10-09",
    "prediction_text": "I can fine-tune **Qwen/Qwen2.5-0.5B-Instruct** on **poetry_target_tags_10k_alpaca.jsonl** (1,110 training samples) using LoRA (2 epochs, lr=1e-4, LoRA rank=8).\n\n**\ud83d\udca1 A couple of suggestions on your settings:**\n- **seq_len** \u2014 seq_len 20736 is long and needs more/bigger GPUs to fit \u2014 the plan will scale hardware to match, or reduce it to 4096 if that's not the size job you meant to run. 2048 is a safe default.\n\n\n_Use the \u2713 / \u2715 buttons above to apply or keep each setting._ I picked the best available Odyn placement and prepared the workload builder.\n\n_Estimated training time: \u22480.0226 hours (\u2248$0.04 total) \u2014 a rough estimate, not a quote._\n\nUse the **Open Workload Builder** button when you are ready.",
    "prediction_ts": "2026-10-09 13:03:18",
    "prediction_year_week": "2026-W41",
    "runtime_abs_error_hours": "0.0070444444444444435",
    "runtime_abs_pct_error": "0.4528571428571428",
    "runtime_accuracy_bucket": "25-50%",
    "runtime_overestimate_flag": "true",
    "runtime_signed_error_hours": "0.0070444444444444435",
    "runtime_underestimate_flag": "false",
    "scheduler_status": "failed",
    "selected_gpu_count": "1",
    "selected_gpu_tier": "NVIDIA A100-SXM4-80GB",
    "selected_hourly_rate_usd": "1.5",
    "session_id": "Q9OpPkyi2D",
    "workload_id": "8c155feb-9711-4b0a-94ae-b06b3eccd57e"
  },
  {
    "actual_operational_cost_usd": "0.297183",
    "actual_runtime_hours": "0.1981216666666667",
    "is_oom_failure": "false",
    "job_id": "b0366d32-8991-51d0-a346-784163ecbb5e",
    "job_status": "completed",
    "match_status": "matched_to_job",
    "message_id": "bVoTWaIvqH",
    "missing_actual_runtime": "false",
    "missing_predicted_runtime": "false",
    "model_size_bucket": "Medium(7-14B)",
    "observed_peak_vram_gb": null,
    "predicted_dataset_ref": "quant_mentor_300_alpaca.jsonl",
    "predicted_model_id": "Qwen/Qwen2.5-7B-Instruct",
    "predicted_operational_cost_usd": "0.2",
    "predicted_runtime_hours": "0.13",
    "predicted_sample_count": "300",
    "prediction_date": "2026-09-06",
    "prediction_text": "I can fine-tune **Qwen/Qwen2.5-7B-Instruct** on **quant_mentor_300_alpaca.jsonl** (300 training samples) using LoRA (3 epochs, lr=1e-4, LoRA rank=16).\n\n**\ud83d\udca1 A couple of suggestions on your settings:**\n- **seq_len** \u2014 seq_len 384 is very short and will truncate most instruction pairs. 512\u20132048 is typical.\n\n\n_Use the \u2713 / \u2715 buttons above to apply or keep each setting._ I picked the best available Odyn placement and prepared the workload builder.\n\n_Estimated training time: \u22480.13 hours (\u2248$0.20 total) \u2014 a rough estimate, not a quote._\n\nUse the **Open Workload Builder** button when you are ready.",
    "prediction_ts": "2026-09-06 13:33:26",
    "prediction_year_week": "2026-W36",
    "runtime_abs_error_hours": "0.06812166666666669",
    "runtime_abs_pct_error": "0.3438375409049995",
    "runtime_accuracy_bucket": "25-50%",
    "runtime_overestimate_flag": "false",
    "runtime_signed_error_hours": "-0.06812166666666669",
    "runtime_underestimate_flag": "true",
    "scheduler_status": "completed",
    "selected_gpu_count": "1",
    "selected_gpu_tier": "NVIDIA A100-SXM4-80GB",
    "selected_hourly_rate_usd": "1.5",
    "session_id": "qnaCmviSOc",
    "workload_id": "eb9370d3-0825-4928-8177-f2fba411bf9b"
  }
]
```

#### `biz_ops.tableau_ceo_digester_vram_accuracy_v1`

```json
[
  {
    "is_oom_failure": "false",
    "job_id": "6cfd192a-c715-55fa-bf98-dff47187147b",
    "match_status": "matched_to_job",
    "message_id": "rtDVFjC5I1",
    "missing_observed_vram": "true",
    "missing_predicted_vram": "true",
    "observed_peak_vram_gb": null,
    "potential_overprovisioned_gpu_tier": "false",
    "predicted_dataset_ref": "supervised_fine_tuning_1000.jsonl",
    "predicted_model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "predicted_peak_vram_gb": null,
    "predicted_sample_count": "1000",
    "prediction_date": "2026-10-05",
    "prediction_ts": "2026-10-05 15:16:04",
    "prediction_year_week": "2026-W41",
    "selected_gpu_count": "1",
    "selected_gpu_tier": "NVIDIA A100-SXM4-80GB",
    "session_id": "MIbuwl6v3f",
    "vram_abs_error_gb": null,
    "vram_gap_note": "Predicted VRAM is not emitted in current governed Smart Digester trace payloads.",
    "vram_signed_error_gb": null,
    "workload_id": "76dee58c-c3a4-4d55-afee-bb95643faa8e"
  },
  {
    "is_oom_failure": "false",
    "job_id": "8e004e0a-cecd-5bc2-abe5-205b4f1f4f83",
    "match_status": "matched_to_job",
    "message_id": "azwzkJhqy7",
    "missing_observed_vram": "true",
    "missing_predicted_vram": "true",
    "observed_peak_vram_gb": null,
    "potential_overprovisioned_gpu_tier": "false",
    "predicted_dataset_ref": "alpaca_train_1200.jsonl",
    "predicted_model_id": "Qwen/Qwen2.5-1.5B-Instruct",
    "predicted_peak_vram_gb": null,
    "predicted_sample_count": "1200",
    "prediction_date": "2026-10-05",
    "prediction_ts": "2026-10-05 14:33:48",
    "prediction_year_week": "2026-W41",
    "selected_gpu_count": "1",
    "selected_gpu_tier": "NVIDIA A100-SXM4-40GB",
    "session_id": "YQGQzf07AW",
    "vram_abs_error_gb": null,
    "vram_gap_note": "Predicted VRAM is not emitted in current governed Smart Digester trace payloads.",
    "vram_signed_error_gb": null,
    "workload_id": "a48ce317-7160-4c9c-b31b-302d122774f0"
  },
  {
    "is_oom_failure": "false",
    "job_id": "b7da5f14-7283-52f1-9b7d-48c3016cb39e",
    "match_status": "matched_to_job",
    "message_id": "n5K06bDnFc",
    "missing_observed_vram": "true",
    "missing_predicted_vram": "true",
    "observed_peak_vram_gb": null,
    "potential_overprovisioned_gpu_tier": "false",
    "predicted_dataset_ref": "quant_mentor_700_alpaca.jsonl",
    "predicted_model_id": "Qwen/Qwen2.5-32B-Instruct",
    "predicted_peak_vram_gb": null,
    "predicted_sample_count": "700",
    "prediction_date": "2026-09-08",
    "prediction_ts": "2026-09-08 06:44:39",
    "prediction_year_week": "2026-W37",
    "selected_gpu_count": "1",
    "selected_gpu_tier": "NVIDIA A100-SXM4-80GB",
    "session_id": "MEZxrMkiIe",
    "vram_abs_error_gb": null,
    "vram_gap_note": "Predicted VRAM is not emitted in current governed Smart Digester trace payloads.",
    "vram_signed_error_gb": null,
    "workload_id": "8d7aab91-70ac-44c0-be36-3205022d5226"
  }
]
```

#### `biz_ops.tableau_ceo_fleet_machine_detail_v1`

```json
[
  {
    "agent_version": null,
    "containers": "0",
    "driver_version": "580.173.02",
    "gpu_fault_flag": "true",
    "gpu_index": "0",
    "gpu_name": "NVIDIA GB10",
    "gpu_status": "fault",
    "high_util_80_flag": "false",
    "host": "odyn-dgx1",
    "load1": "0.01",
    "mem_total_mib": null,
    "mem_used_mib": null,
    "power_w": null,
    "sample_ts": "2026-10-11 15:03:46",
    "temp_c": null,
    "ts_backend": null,
    "util_gpu_pct": null,
    "vendor": "nvidia",
    "vram_pct": null,
    "workload_id": null,
    "workload_join_note": "No governed host->workload assignment join currently available for edge telemetry samples."
  },
  {
    "agent_version": null,
    "containers": "1",
    "driver_version": "580.173.02",
    "gpu_fault_flag": "false",
    "gpu_index": "0",
    "gpu_name": "NVIDIA GB10",
    "gpu_status": "ok",
    "high_util_80_flag": "false",
    "host": "odyn-dgx3",
    "load1": "0.31",
    "mem_total_mib": null,
    "mem_used_mib": null,
    "power_w": "4.79",
    "sample_ts": "2026-10-11 15:03:46",
    "temp_c": "40.0",
    "ts_backend": null,
    "util_gpu_pct": "0.0",
    "vendor": "nvidia",
    "vram_pct": null,
    "workload_id": null,
    "workload_join_note": "No governed host->workload assignment join currently available for edge telemetry samples."
  },
  {
    "agent_version": null,
    "containers": "1",
    "driver_version": "580.159.03",
    "gpu_fault_flag": "false",
    "gpu_index": "0",
    "gpu_name": "NVIDIA GB10",
    "gpu_status": "ok",
    "high_util_80_flag": "false",
    "host": "odyn-dgx-spark-02",
    "load1": "0.0",
    "mem_total_mib": null,
    "mem_used_mib": null,
    "power_w": "10.65",
    "sample_ts": "2026-10-11 15:03:46",
    "temp_c": "36.0",
    "ts_backend": null,
    "util_gpu_pct": "0.0",
    "vendor": "nvidia",
    "vram_pct": null,
    "workload_id": null,
    "workload_join_note": "No governed host->workload assignment join currently available for edge telemetry samples."
  }
]
```

#### `biz_ops.tableau_ceo_fleet_machine_overview_v1`

```json
[
  {
    "age_s": "17",
    "containers": "1",
    "demo_readiness": "UNKNOWN",
    "demo_ready": "false",
    "display_name": "DGX Spark 3",
    "expected_gpus": "1",
    "gpu_rows": "1",
    "high_util_80_flag": "false",
    "host": "odyn-dgx3",
    "is_demo": "false",
    "last_sample_ts": "2026-10-11 15:09:46",
    "load1": "0.15",
    "machine_drill_key": "machine://odyn-dgx3",
    "machine_health_state": "online",
    "power_w_sum": "4.89",
    "state": "IDLE_WITH_CONTAINER",
    "telemetry_fresh": "true",
    "telemetry_status": "FRESH",
    "temp_c_max": "40.0",
    "util_gpu_pct_max": "0.0",
    "vendor": "nvidia"
  },
  {
    "age_s": "17",
    "containers": "0",
    "demo_readiness": "READY",
    "demo_ready": "true",
    "display_name": "2x RTX A6000 server",
    "expected_gpus": "2",
    "gpu_rows": "2",
    "high_util_80_flag": "false",
    "host": "odyn-a6000",
    "is_demo": "true",
    "last_sample_ts": "2026-10-11 15:09:46",
    "load1": "0.33",
    "machine_drill_key": "machine://odyn-a6000",
    "machine_health_state": "online",
    "power_w_sum": "32.7",
    "state": "IDLE",
    "telemetry_fresh": "true",
    "telemetry_status": "FRESH",
    "temp_c_max": "35.0",
    "util_gpu_pct_max": "0.0",
    "vendor": "nvidia"
  },
  {
    "age_s": "16278",
    "containers": null,
    "demo_readiness": "UNKNOWN",
    "demo_ready": "false",
    "display_name": "Radeon Office 2 (GMKtec EVO-X2)",
    "expected_gpus": "1",
    "gpu_rows": "1",
    "high_util_80_flag": "false",
    "host": "odyn-radeon2",
    "is_demo": "true",
    "last_sample_ts": "2026-10-11 10:38:45",
    "load1": null,
    "machine_drill_key": "machine://odyn-radeon2",
    "machine_health_state": "unknown",
    "power_w_sum": "4.063",
    "state": "NO_RECENT_SAMPLE",
    "telemetry_fresh": "false",
    "telemetry_status": "STALE",
    "temp_c_max": "28.0",
    "util_gpu_pct_max": "0.0",
    "vendor": "amd"
  }
]
```

#### `biz_ops.tableau_ceo_fleet_summary_v1`

```json
[
  {
    "availability_pct": "57.142857142857146",
    "confirmed_offline_machines": "0",
    "degraded_machines": "1",
    "expected_gpu_count": "8",
    "gpu_telemetry_coverage_pct": "87.5",
    "healthy_available_machines": "4",
    "latest_telemetry_ts": "2026-10-11 15:09:46",
    "observed_machines": "7",
    "plane": "edge",
    "registered_machines": "7",
    "reporting_gpu_count": "7",
    "reporting_machines": "5",
    "telemetry_coverage_pct": "71.42857142857143",
    "unmonitored_machines": "0"
  },
  {
    "availability_pct": null,
    "confirmed_offline_machines": null,
    "degraded_machines": null,
    "expected_gpu_count": null,
    "gpu_telemetry_coverage_pct": null,
    "healthy_available_machines": null,
    "latest_telemetry_ts": null,
    "observed_machines": null,
    "plane": "production",
    "registered_machines": null,
    "reporting_gpu_count": null,
    "reporting_machines": null,
    "telemetry_coverage_pct": null,
    "unmonitored_machines": null
  }
]
```

#### `biz_ops.tableau_ceo_gpu_utilization_v1`

```json
[
  {
    "metric_date": "2026-10-11",
    "observed_rows": "2709",
    "pct_time_above_50": "0.0",
    "plane": "edge",
    "util_avg_pct": "0.0",
    "util_coverage": "0.8246585455887782",
    "util_p95_pct": "0.0",
    "util_peak_pct": "0.0",
    "util_rows": "2234"
  }
]
```

#### `biz_ops.tableau_ceo_job_investigation_v1`

```json
[
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "assigned_gpus": null,
    "assigned_nodes": null,
    "cluster_id": null,
    "dataset_uri_sanitized": "file-21837897-1b25-48de-b4bf-73c23906316a",
    "failure_class": null,
    "failure_message_redacted": null,
    "first_assignment_at": null,
    "last_assignment_at": null,
    "missing_gpu_assignment": "true",
    "missing_outcome": "true",
    "model_available_at": "2026-10-04 05:28:32",
    "model_id": "Qwen/Qwen3.5-9B",
    "outcome_status": null,
    "payload_error": null,
    "payload_status": "completed",
    "pod": null,
    "provider": "together",
    "source_system": "together_api",
    "submitted_at": "2026-10-04 05:15:58",
    "trainer_started_at": "2026-10-04 05:21:57",
    "training_ended_at": "2026-10-04 05:25:01",
    "training_time_min": "3.066666666666667",
    "user_hmac": "818bb265c1a0e50d1a1c3369337b824356a468234679f30bab62246e445ba5c9",
    "wall_time_min": "12.55195",
    "workload_id": "ft-b61858e9-228c",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "assigned_gpus": null,
    "assigned_nodes": null,
    "cluster_id": null,
    "dataset_uri_sanitized": "file-a1bb95d0-9bb0-4fc6-9e33-8290f7c1144e",
    "failure_class": null,
    "failure_message_redacted": null,
    "first_assignment_at": null,
    "last_assignment_at": null,
    "missing_gpu_assignment": "true",
    "missing_outcome": "true",
    "model_available_at": "2026-10-09 16:04:33",
    "model_id": "openai/gpt-oss-20b",
    "outcome_status": null,
    "payload_error": null,
    "payload_status": "completed",
    "pod": null,
    "provider": "together",
    "source_system": "together_api",
    "submitted_at": "2026-10-09 15:50:04",
    "trainer_started_at": "2026-10-09 15:53:38",
    "training_ended_at": "2026-10-09 16:02:08",
    "training_time_min": "8.5",
    "user_hmac": "818bb265c1a0e50d1a1c3369337b824356a468234679f30bab62246e445ba5c9",
    "wall_time_min": "14.479933333333333",
    "workload_id": "ft-2fe19cba-b1d3",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "assigned_gpus": null,
    "assigned_nodes": null,
    "cluster_id": "e691ec85-e853-4a0e-b104-a13d2b7af085",
    "dataset_uri_sanitized": null,
    "failure_class": null,
    "failure_message_redacted": null,
    "first_assignment_at": null,
    "last_assignment_at": null,
    "missing_gpu_assignment": "true",
    "missing_outcome": "true",
    "model_available_at": null,
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "outcome_status": null,
    "payload_error": "",
    "payload_status": "ready",
    "pod": "odyn-ray-e691ec85-e853-4a0e-b104-a13d2b7af085-head-9fwm5",
    "provider": "odyn",
    "source_system": "eks_kuberay",
    "submitted_at": null,
    "trainer_started_at": null,
    "training_ended_at": null,
    "training_time_min": null,
    "user_hmac": "ab43b487f3dfaf6952aa41240e04bc86b3ab6f44f3f16708860e6cf654e2b322",
    "wall_time_min": null,
    "workload_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "workload_type": "serving"
  }
]
```

#### `biz_ops.tableau_ceo_scheduler_economics_v1`

```json
[
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "buyer_price_per_million_usd": null,
    "contribution_margin_pct": null,
    "economics_status": "UNAVAILABLE_IN_GOVERNED_BIGQUERY_V1",
    "limitation_reason": "Missing governed pricing source and token-accounting join in current BigQuery schema.",
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "provider": "odyn",
    "source_system": "eks_kuberay",
    "supplier_cost_per_million_usd": null,
    "throughput_tokens_per_s": null,
    "workload_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "workload_type": "serving"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "buyer_price_per_million_usd": null,
    "contribution_margin_pct": null,
    "economics_status": "UNAVAILABLE_IN_GOVERNED_BIGQUERY_V1",
    "limitation_reason": "Missing governed pricing source and token-accounting join in current BigQuery schema.",
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "provider": "odyn",
    "source_system": "eks_kuberay",
    "supplier_cost_per_million_usd": null,
    "throughput_tokens_per_s": null,
    "workload_id": "92fa7793-2c1d-5b15-83e4-de59fc529c14",
    "workload_type": "serving"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "buyer_price_per_million_usd": null,
    "contribution_margin_pct": null,
    "economics_status": "UNAVAILABLE_IN_GOVERNED_BIGQUERY_V1",
    "limitation_reason": "Missing governed pricing source and token-accounting join in current BigQuery schema.",
    "model_id": "Qwen/Qwen2.5-7B-Instruct",
    "provider": "odyn",
    "source_system": "eks_kuberay",
    "supplier_cost_per_million_usd": null,
    "throughput_tokens_per_s": null,
    "workload_id": "c2104b10-f154-53cb-9f19-4169369251b5",
    "workload_type": "serving"
  }
]
```

#### `biz_ops.tableau_ceo_workload_failures_v1`

```json
[
  {
    "application_failures": "0",
    "failed_job_ids": null,
    "failed_jobs": "0",
    "failure_pct": "0.0",
    "infrastructure_failures": "0",
    "oom_failures": "0",
    "provider": "together",
    "representative_failure_reasons": null,
    "scheduling_failures": "0",
    "successful_jobs": "12",
    "total_jobs_denominator": "12",
    "unknown_failures": "0",
    "workload_type": "finetune",
    "year_week": "2026-W41"
  },
  {
    "application_failures": "0",
    "failed_job_ids": null,
    "failed_jobs": "0",
    "failure_pct": "0.0",
    "infrastructure_failures": "0",
    "oom_failures": "0",
    "provider": "together",
    "representative_failure_reasons": null,
    "scheduling_failures": "0",
    "successful_jobs": "4",
    "total_jobs_denominator": "4",
    "unknown_failures": "0",
    "workload_type": "finetune",
    "year_week": "2026-W40"
  },
  {
    "application_failures": "0",
    "failed_job_ids": null,
    "failed_jobs": "0",
    "failure_pct": "0.0",
    "infrastructure_failures": "0",
    "oom_failures": "0",
    "provider": "odyn",
    "representative_failure_reasons": null,
    "scheduling_failures": "0",
    "successful_jobs": "2",
    "total_jobs_denominator": "3",
    "unknown_failures": "0",
    "workload_type": "serving",
    "year_week": "2026-W41"
  }
]
```

#### `biz_ops.workload_benchmark_flat_v1`

```json
[
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "batch_size_f": "1",
    "batch_size_kind": "per_device",
    "batch_size_raw": "1",
    "batch_size_value": "1",
    "benchmark_timing_eligible": "true",
    "benchmark_timing_eligible_reason": "requires wall_time and training_time",
    "conditions_ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "conditions_source_record_ref": null,
    "conditions_source_system": "together_api",
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_uri_sanitized": "file-a1a6d941-605e-4d8a-bcd0-03fb0e2fd80f",
    "dataset_uri_sanitized_f": "1",
    "gpu_count": null,
    "gpu_count_f": "0",
    "is_benchmark_run": "true",
    "is_customer_workload": "false",
    "learning_rate": "1.0E-4",
    "learning_rate_f": "1",
    "lora_alpha": "32",
    "lora_alpha_f": "1",
    "lora_rank": "16",
    "lora_rank_f": "1",
    "model_available_at": "2026-10-09 16:10:36",
    "model_available_at_f": "1",
    "model_available_at_source": "together.events.JOB_COMPLETE",
    "model_id": "openai/gpt-oss-20b",
    "model_id_f": "1",
    "precision": null,
    "precision_f": "0",
    "provider": "together",
    "provider_run_id": "ft-13dd5f5f-d688",
    "seq_len": "4096",
    "seq_len_f": "1",
    "submitted_at": "2026-10-09 16:01:15",
    "submitted_at_f": "1",
    "submitted_at_source": "provider_server_clock",
    "timing_ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "timing_source_system": "together_api",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "trainer_started_at": "2026-10-09 16:05:26",
    "trainer_started_at_f": "1",
    "training_ended_at": "2026-10-09 16:08:05",
    "training_ended_at_f": "1",
    "training_method": "lora",
    "training_method_f": "1",
    "training_objective": "sft",
    "training_objective_f": "1",
    "training_time_min": "2.65",
    "training_time_min_f": "1",
    "wall_time_min": "9.3458",
    "wall_time_min_f": "1",
    "workload_id": "ft-13dd5f5f-d688",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "batch_size_f": "1",
    "batch_size_kind": "per_device",
    "batch_size_raw": "1",
    "batch_size_value": "1",
    "benchmark_timing_eligible": "true",
    "benchmark_timing_eligible_reason": "requires wall_time and training_time",
    "conditions_ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "conditions_source_record_ref": null,
    "conditions_source_system": "together_api",
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_uri_sanitized": "file-a1bb95d0-9bb0-4fc6-9e33-8290f7c1144e",
    "dataset_uri_sanitized_f": "1",
    "gpu_count": null,
    "gpu_count_f": "0",
    "is_benchmark_run": "true",
    "is_customer_workload": "false",
    "learning_rate": "1.0E-4",
    "learning_rate_f": "1",
    "lora_alpha": "32",
    "lora_alpha_f": "1",
    "lora_rank": "16",
    "lora_rank_f": "1",
    "model_available_at": "2026-10-09 16:15:08",
    "model_available_at_f": "1",
    "model_available_at_source": "together.events.JOB_COMPLETE",
    "model_id": "openai/gpt-oss-20b",
    "model_id_f": "1",
    "precision": null,
    "precision_f": "0",
    "provider": "together",
    "provider_run_id": "ft-15dec247-d184",
    "seq_len": "4096",
    "seq_len_f": "1",
    "submitted_at": "2026-10-09 16:00:55",
    "submitted_at_f": "1",
    "submitted_at_source": "provider_server_clock",
    "timing_ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "timing_source_system": "together_api",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "trainer_started_at": "2026-10-09 16:04:24",
    "trainer_started_at_f": "1",
    "training_ended_at": "2026-10-09 16:12:46",
    "training_ended_at_f": "1",
    "training_method": "lora",
    "training_method_f": "1",
    "training_objective": "sft",
    "training_objective_f": "1",
    "training_time_min": "8.366666666666667",
    "training_time_min_f": "1",
    "wall_time_min": "14.210616666666665",
    "wall_time_min_f": "1",
    "workload_id": "ft-15dec247-d184",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "batch_size_f": "1",
    "batch_size_kind": "per_device",
    "batch_size_raw": "1",
    "batch_size_value": "1",
    "benchmark_timing_eligible": "true",
    "benchmark_timing_eligible_reason": "requires wall_time and training_time",
    "conditions_ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "conditions_source_record_ref": null,
    "conditions_source_system": "together_api",
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_uri_sanitized": "file-a1a6d941-605e-4d8a-bcd0-03fb0e2fd80f",
    "dataset_uri_sanitized_f": "1",
    "gpu_count": null,
    "gpu_count_f": "0",
    "is_benchmark_run": "true",
    "is_customer_workload": "false",
    "learning_rate": "1.0E-4",
    "learning_rate_f": "1",
    "lora_alpha": "32",
    "lora_alpha_f": "1",
    "lora_rank": "16",
    "lora_rank_f": "1",
    "model_available_at": "2026-10-09 15:59:07",
    "model_available_at_f": "1",
    "model_available_at_source": "together.events.JOB_COMPLETE",
    "model_id": "openai/gpt-oss-20b",
    "model_id_f": "1",
    "precision": null,
    "precision_f": "0",
    "provider": "together",
    "provider_run_id": "ft-1fce124e-17b1",
    "seq_len": "4096",
    "seq_len_f": "1",
    "submitted_at": "2026-10-09 15:50:03",
    "submitted_at_f": "1",
    "submitted_at_source": "provider_server_clock",
    "timing_ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "timing_source_system": "together_api",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "trainer_started_at": "2026-10-09 15:54:01",
    "trainer_started_at_f": "1",
    "training_ended_at": "2026-10-09 15:56:37",
    "training_ended_at_f": "1",
    "training_method": "lora",
    "training_method_f": "1",
    "training_objective": "sft",
    "training_objective_f": "1",
    "training_time_min": "2.6",
    "training_time_min_f": "1",
    "wall_time_min": "9.054183333333333",
    "wall_time_min_f": "1",
    "workload_id": "ft-1fce124e-17b1",
    "workload_type": "finetune"
  }
]
```

## Dataset: `raw_ops`

### Row counts

| Table | Type | Row count |
|---|---|---:|

| `edge_gpu_samples_v1` | BASE TABLE | 2697 |

| `pg_state_snapshot_v1` | BASE TABLE | 851 |

| `workload_conditions_raw_dedup_v1` | VIEW | 0 |

| `workload_conditions_raw_v1` | BASE TABLE | 38 |


### Top 3 rows per table

#### `raw_ops.edge_gpu_samples_v1`

```json
[
  {
    "agent_version": null,
    "boot_ts": "2026-09-28 17:06:36",
    "containers": "0",
    "driver_version": "580.173.02",
    "gpu_index": "0",
    "gpu_name": "NVIDIA GB10",
    "gpu_status": "fault",
    "host": "odyn-dgx1",
    "load1": "0.01",
    "mem_total_mib": null,
    "mem_used_mib": null,
    "power_w": null,
    "pstate": null,
    "reachable": "true",
    "sample_ts": "2026-10-11 15:03:46",
    "sampler_run_id": "edge_20261011T072208Z_814b2c",
    "site": "london-edge",
    "skipped": "false",
    "temp_c": null,
    "ts_backend": null,
    "ts_key_expiry": null,
    "util_gpu_pct": null,
    "vendor": "nvidia",
    "vpn_online": "true",
    "vram_pct": null
  },
  {
    "agent_version": null,
    "boot_ts": "2026-09-29 15:58:39",
    "containers": "1",
    "driver_version": "580.173.02",
    "gpu_index": "0",
    "gpu_name": "NVIDIA GB10",
    "gpu_status": "ok",
    "host": "odyn-dgx3",
    "load1": "0.31",
    "mem_total_mib": null,
    "mem_used_mib": null,
    "power_w": "4.79",
    "pstate": "P8",
    "reachable": "true",
    "sample_ts": "2026-10-11 15:03:46",
    "sampler_run_id": "edge_20261011T072208Z_814b2c",
    "site": "london-edge",
    "skipped": "false",
    "temp_c": "40.0",
    "ts_backend": null,
    "ts_key_expiry": null,
    "util_gpu_pct": "0.0",
    "vendor": "nvidia",
    "vpn_online": "true",
    "vram_pct": null
  },
  {
    "agent_version": null,
    "boot_ts": "2026-09-28 17:13:13",
    "containers": "1",
    "driver_version": "580.159.03",
    "gpu_index": "0",
    "gpu_name": "NVIDIA GB10",
    "gpu_status": "ok",
    "host": "odyn-dgx-spark-02",
    "load1": "0.0",
    "mem_total_mib": null,
    "mem_used_mib": null,
    "power_w": "10.65",
    "pstate": "P0",
    "reachable": "true",
    "sample_ts": "2026-10-11 15:03:46",
    "sampler_run_id": "edge_20261011T072208Z_814b2c",
    "site": "london-edge",
    "skipped": "false",
    "temp_c": "36.0",
    "ts_backend": null,
    "ts_key_expiry": null,
    "util_gpu_pct": "0.0",
    "vendor": "nvidia",
    "vpn_online": "true",
    "vram_pct": null
  }
]
```

#### `raw_ops.pg_state_snapshot_v1`

```json
[
  {
    "captured_at": "2026-10-11 10:13:15",
    "captured_date": "2026-10-11",
    "hmac_key_id": "manual_backfill_no_hmac",
    "ingest_run_id": "manual_pg_backfill_20261011T101315Z",
    "is_deleted": "false",
    "redaction_version": "extractor_v0_redact_2026_10_11",
    "row_hash": "6ab408eba921c2d4ae969625ad5be80eb4dc7e10716b85635112a89dd172b1ce",
    "row_json": "{\"compute_cost_usd\":0.061733,\"job_id\":\"227f569c-8393-52f4-b829-899dd46cc7f4\",\"updated_at\":\"2026-09-29T20:17:51.910503+00:00\",\"wall_clock_seconds\":296.317,\"workload_metric_name\":\"gpu_seconds\"}",
    "row_pk": "{\"job_id\":\"227f569c-8393-52f4-b829-899dd46cc7f4\",\"workload_metric_name\":\"gpu_seconds\"}",
    "snapshot_id": "314431da-1cb5-4702-9f29-b0c6aced64da",
    "source_row_count": "57",
    "table_name": "public.job_cost_summary"
  },
  {
    "captured_at": "2026-10-11 10:13:15",
    "captured_date": "2026-10-11",
    "hmac_key_id": "manual_backfill_no_hmac",
    "ingest_run_id": "manual_pg_backfill_20261011T101315Z",
    "is_deleted": "false",
    "redaction_version": "extractor_v0_redact_2026_10_11",
    "row_hash": "8c2716883e00dbb842094aece6f26359304a1b665aebafddd4247e8ffd8fd88f",
    "row_json": "{\"compute_cost_usd\":0.129103,\"job_id\":\"7ebd6abe-37ab-571b-9d82-c6adb1e15be8\",\"updated_at\":\"2026-09-28T17:28:36.877541+00:00\",\"wall_clock_seconds\":309.847,\"workload_metric_name\":\"gpu_seconds\"}",
    "row_pk": "{\"job_id\":\"7ebd6abe-37ab-571b-9d82-c6adb1e15be8\",\"workload_metric_name\":\"gpu_seconds\"}",
    "snapshot_id": "4cdfe27e-d9ab-49dc-ac64-5b54a5687c56",
    "source_row_count": "57",
    "table_name": "public.job_cost_summary"
  },
  {
    "captured_at": "2026-10-11 10:13:15",
    "captured_date": "2026-10-11",
    "hmac_key_id": "manual_backfill_no_hmac",
    "ingest_run_id": "manual_pg_backfill_20261011T101315Z",
    "is_deleted": "false",
    "redaction_version": "extractor_v0_redact_2026_10_11",
    "row_hash": "fe37f696af638ddcc8a4dda24fce8dee935af8fba3fc31041da8bf5850d5b2bb",
    "row_json": "{\"compute_cost_usd\":1.268274,\"job_id\":\"9ad7a8a5-23c7-574a-a045-0c41582657ef\",\"updated_at\":\"2026-09-08T08:36:48.315972+00:00\",\"wall_clock_seconds\":3043.859,\"workload_metric_name\":\"gpu_seconds\"}",
    "row_pk": "{\"job_id\":\"9ad7a8a5-23c7-574a-a045-0c41582657ef\",\"workload_metric_name\":\"gpu_seconds\"}",
    "snapshot_id": "448bf8d3-78ae-411f-9065-0182a7ad6cb4",
    "source_row_count": "57",
    "table_name": "public.job_cost_summary"
  }
]
```

#### `raw_ops.workload_conditions_raw_dedup_v1`

```json
[
  {
    "classification_rule": null,
    "event_at": "2026-10-09 15:56:59",
    "event_date": "2026-10-09",
    "fetched_at": "2026-10-10 20:08:34",
    "ingest_run_id": "bq_ingest_v1_20261010T200834Z",
    "is_benchmark_run": "true",
    "is_customer_workload": "false",
    "owner_hmac": null,
    "owner_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "payload_redacted": "{\"batch_size\":1,\"created_at\":\"2026-10-09T15:56:59.462000Z\",\"eval_steps\":0,\"events\":[{\"created_at\":\"2026-10-09T15:56:59.56Z\",\"level\":\"\",\"message\":\"Fine-tuning request created\",\"object\":\"fine-tune-event\",\"type\":\"JOB_PENDING\"},{\"created_at\":\"2026-10-09T15:58:31Z\",\"level\":\"Info\",\"message\":\"Job started\",\"object\":\"fine-tune-event\",\"type\":\"JOB_START\"},{\"created_at\":\"2026-10-09T15:58:33Z\",\"level\":\"Info\",\"message\":\"Downloading model data for togethercomputer/gpt-oss-20b-bf16\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_DOWNLOADING\"},{\"created_at\":\"2026-10-09T15:58:38Z\",\"level\":\"Info\",\"message\":\"Model data downloaded for togethercomputer/gpt-oss-20b-bf16\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_DOWNLOAD_COMPLETE\"},{\"created_at\":\"2026-10-09T15:58:41Z\",\"level\":\"Info\",\"message\":\"Data downloaded for togethercomputer/gpt-oss-20b-bf16 at Fri Oct 09 15:58:41 UTC 2026\",\"object\":\"fine-tune-event\",\"type\":\"TRAINING_DATA_DOWNLOADING\"},{\"created_at\":\"2026-10-09T15:59:33Z\",\"level\":\"Info\",\"message\":\"<REDACTED>\",\"object\":\"fine-tune-event\",\"tokenized_dataset_path\":\"<REDACTED>\",\"type\":\"<REDACTED>\"},{\"created_at\":\"2026-10-09T16:00:40Z\",\"level\":\"Info\",\"message\":\"Training started for model togethercomputer/gpt-oss-20b-bf16\",\"object\":\"fine-tune-event\",\"param_count\":20914757184,\"token_count\":\"<REDACTED>\",\"total_steps\":102,\"type\":\"TRAINING_START\"},{\"created_at\":\"2026-10-09T16:08:37Z\",\"level\":\"Info\",\"message\":\"Epoch completed, at step 102\",\"object\":\"fine-tune-event\",\"step\":102,\"type\":\"EPOCH_COMPLETE\"},{\"created_at\":\"2026-10-09T16:09:05Z\",\"level\":\"Info\",\"message\":\"Training completed for togethercomputer/gpt-oss-20b-bf16\",\"object\":\"fine-tune-event\",\"type\":\"TRAINING_COMPLETE\"},{\"created_at\":\"2026-10-09T16:10:03Z\",\"level\":\"Info\",\"message\":\"Compressing adapter model\",\"object\":\"fine-tune-event\",\"type\":\"COMPRESSING_MODEL\"},{\"created_at\":\"2026-10-09T16:10:03Z\",\"level\":\"Info\",\"message\":\"Adapter model compression complete\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_COMPRESSION_COMPLETE\"},{\"checkpoint_size_bytes\":34035362,\"created_at\":\"2026-10-09T16:10:03Z\",\"level\":\"Info\",\"message\":\"Uploading adapter model\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_UPLOADING\"},{\"created_at\":\"2026-10-09T16:10:08Z\",\"level\":\"Info\",\"message\":\"Adapter upload complete\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_UPLOAD_COMPLETE\"},{\"created_at\":\"2026-10-09T16:10:15Z\",\"level\":\"Info\",\"message\":\"Compressing output model\",\"object\":\"fine-tune-event\",\"type\":\"COMPRESSING_MODEL\"},{\"created_at\":\"2026-10-09T16:10:28Z\",\"level\":\"Info\",\"message\":\"Compression complete for output model\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_COMPRESSION_COMPLETE\"},{\"checkpoint_size_bytes\":12256374385,\"created_at\":\"2026-10-09T16:10:28Z\",\"level\":\"Info\",\"message\":\"Uploading output model\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_UPLOADING\"},{\"created_at\":\"2026-10-09T16:11:07Z\",\"level\":\"Info\",\"message\":\"Upload complete for output model\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_UPLOAD_COMPLETE\"},{\"adapter_path\":\"<REDACTED>\",\"created_at\":\"2026-10-09T16:11:37Z\",\"level\":\"Info\",\"message\":\"Job finished at 2026-10-09 16:11:37\",\"model_path\":\"<REDACTED>\",\"object\":\"fine-tune-event\",\"type\":\"JOB_COMPLETE\"}],\"gradient_accumulation_steps\":8,\"id\":\"ft-db904a53-822c\",\"learning_rate\":0.0001,\"lr_scheduler\":{\"lr_scheduler_args\":{\"num_cycles\":0.5},\"lr_scheduler_type\":\"cosine\"},\"max_grad_norm\":1,\"max_seq_length\":4096,\"max_steps\":-1,\"model\":\"openai/gpt-oss-20b\",\"model_output_name\":\"michaelsigaman_879a/gpt-oss-20b-bench-10k-9c655ccf\",\"multimodal_params\":{},\"n_checkpoints\":1,\"n_epochs\":1,\"n_evals\":0,\"packing\":true,\"progress\":{\"estimate_available\":false,\"seconds_remaining\":0},\"random_seed\":42,\"started_at\":\"2026-10-09T16:00:40Z\",\"status\":\"completed\",\"suffix\":\"bench-10k\",\"token_count\":\"<REDACTED>\",\"total_price\":4000000000,\"train_on_inputs\":null,\"training_file\":\"file-a1bb95d0-9bb0-4fc6-9e33-8290f7c1144e\",\"training_files\":null,\"training_method\":{\"method\":\"sft\",\"train_on_inputs\":\"auto\"},\"training_type\":{\"lora_alpha\":32,\"lora_r\":16,\"lora_trainable_modules\":\"k_proj,o_proj,q_proj,v_proj\",\"type\":\"Lora\"},\"updated_at\":\"2026-10-09T16:11:37.397000Z\",\"user_id\":\"<REDACTED>\",\"validation_files\":null,\"validation_split_ratio\":0,\"warmup_ratio\":0,\"warmup_steps\":0,\"weight_decay\":0}",
    "payload_sha256": "03fe51465f63e9bcb68db81861bb4de9baf15fb25cc3c7ed78236350d7c7231a",
    "provider": "together",
    "provider_run_id": "ft-db904a53-822c",
    "raw_record_id": "29b9ffeaffcdf3eed90dc257de39b572079255a9f716803959bb23427c2b82b5",
    "redaction_applied": "true",
    "redaction_scan_findings": [],
    "redaction_scan_passed": "true",
    "redaction_version": "redact_v1",
    "source_system": "together_api",
    "user_hmac": "818bb265c1a0e50d1a1c3369337b824356a468234679f30bab62246e445ba5c9",
    "user_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "workload_id": "ft-db904a53-822c",
    "workload_type": "finetune"
  },
  {
    "classification_rule": null,
    "event_at": "2026-10-10 15:36:17",
    "event_date": "2026-10-10",
    "fetched_at": "2026-10-10 20:11:45",
    "ingest_run_id": "bq_ingest_v1_20261010T201145Z",
    "is_benchmark_run": "false",
    "is_customer_workload": "true",
    "owner_hmac": null,
    "owner_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "payload_redacted": "{\"cluster_created_at\":\"2026-10-08T15:12:46+00:00\",\"cluster_id\":\"e691ec85-e853-4a0e-b104-a13d2b7af085\",\"cluster_name\":\"odyn-ray-e691ec85-e853-4a0e-b104-a13d2b7af085\",\"deployment_type\":\"chat\",\"error\":\"\",\"model_name\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"observed_at\":\"2026-10-10T15:36:17.801092+00:00\",\"pod\":\"odyn-ray-e691ec85-e853-4a0e-b104-a13d2b7af085-head-9fwm5\",\"pod_ip\":\"192.168.138.205\",\"served_model_name\":\"adapter-90cf04b2-be84-5f59-8242-046b2bff9ead\",\"source_finetune_job_id\":\"90cf04b2-be84-5f59-8242-046b2bff9ead\",\"status\":\"ready\",\"user_id\":\"<REDACTED>\"}",
    "payload_sha256": "98f08abe9df3fb54e0905df7ba0c9b0a8120bc7f3d9ecb22f821930aa1b7dba2",
    "provider": "odyn",
    "provider_run_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "raw_record_id": "f462aca30c44c5433e4df1f8fa0b7e2a0ef241ba5acf68ac8eb98cee03878e24",
    "redaction_applied": "true",
    "redaction_scan_findings": [],
    "redaction_scan_passed": "true",
    "redaction_version": "redact_v1",
    "source_system": "eks_kuberay",
    "user_hmac": "ab43b487f3dfaf6952aa41240e04bc86b3ab6f44f3f16708860e6cf654e2b322",
    "user_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "workload_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "workload_type": "serving"
  },
  {
    "classification_rule": null,
    "event_at": "2026-10-04 05:15:59",
    "event_date": "2026-10-04",
    "fetched_at": "2026-10-10 20:08:34",
    "ingest_run_id": "bq_ingest_v1_20261010T200834Z",
    "is_benchmark_run": "false",
    "is_customer_workload": "true",
    "owner_hmac": null,
    "owner_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "payload_redacted": "{\"batch_size\":2,\"created_at\":\"2026-10-04T05:15:59.320000Z\",\"eval_steps\":0,\"events\":[{\"created_at\":\"2026-10-04T05:15:59.411Z\",\"level\":\"\",\"message\":\"Fine-tuning request created\",\"object\":\"fine-tune-event\",\"type\":\"JOB_PENDING\"},{\"created_at\":\"2026-10-04T05:17:32Z\",\"level\":\"Info\",\"message\":\"Job started\",\"object\":\"fine-tune-event\",\"type\":\"JOB_START\"},{\"created_at\":\"2026-10-04T05:17:34Z\",\"level\":\"Info\",\"message\":\"Downloading model data for togethercomputer/Qwen3.5-27B\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_DOWNLOADING\"},{\"created_at\":\"2026-10-04T05:17:40Z\",\"level\":\"Info\",\"message\":\"Model data downloaded for togethercomputer/Qwen3.5-27B\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_DOWNLOAD_COMPLETE\"},{\"created_at\":\"2026-10-04T05:17:41Z\",\"level\":\"Info\",\"message\":\"Data downloaded for togethercomputer/Qwen3.5-27B at Sun Oct 04 05:17:41 UTC 2026\",\"object\":\"fine-tune-event\",\"type\":\"TRAINING_DATA_DOWNLOADING\"},{\"created_at\":\"2026-10-04T05:20:56Z\",\"level\":\"Info\",\"message\":\"<REDACTED>\",\"object\":\"fine-tune-event\",\"tokenized_dataset_path\":\"<REDACTED>\",\"type\":\"<REDACTED>\"},{\"created_at\":\"2026-10-04T05:21:48Z\",\"level\":\"Info\",\"message\":\"Training started for model togethercomputer/Qwen3.5-27B\",\"object\":\"fine-tune-event\",\"param_count\":27356728560,\"token_count\":\"<REDACTED>\",\"total_steps\":44,\"type\":\"TRAINING_START\"},{\"created_at\":\"2026-10-04T05:28:08Z\",\"level\":\"Info\",\"message\":\"Epoch completed, at step 44\",\"object\":\"fine-tune-event\",\"step\":44,\"type\":\"EPOCH_COMPLETE\"},{\"created_at\":\"2026-10-04T05:28:43Z\",\"level\":\"Info\",\"message\":\"Training completed for togethercomputer/Qwen3.5-27B\",\"object\":\"fine-tune-event\",\"type\":\"TRAINING_COMPLETE\"},{\"created_at\":\"2026-10-04T05:33:29Z\",\"level\":\"Info\",\"message\":\"Compressing adapter model\",\"object\":\"fine-tune-event\",\"type\":\"COMPRESSING_MODEL\"},{\"created_at\":\"2026-10-04T05:33:33Z\",\"level\":\"Info\",\"message\":\"Adapter model compression complete\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_COMPRESSION_COMPLETE\"},{\"checkpoint_size_bytes\":434093879,\"created_at\":\"2026-10-04T05:33:33Z\",\"level\":\"Info\",\"message\":\"Uploading adapter model\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_UPLOADING\"},{\"created_at\":\"2026-10-04T05:33:42Z\",\"level\":\"Info\",\"message\":\"Adapter upload complete\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_UPLOAD_COMPLETE\"},{\"created_at\":\"2026-10-04T05:33:47Z\",\"level\":\"Info\",\"message\":\"Compressing output model\",\"object\":\"fine-tune-event\",\"type\":\"COMPRESSING_MODEL\"},{\"created_at\":\"2026-10-04T05:34:53Z\",\"level\":\"Info\",\"message\":\"Compression complete for output model\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_COMPRESSION_COMPLETE\"},{\"checkpoint_size_bytes\":43285333913,\"created_at\":\"2026-10-04T05:34:53Z\",\"level\":\"Info\",\"message\":\"Uploading output model\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_UPLOADING\"},{\"created_at\":\"2026-10-04T05:35:52Z\",\"level\":\"Info\",\"message\":\"Upload complete for output model\",\"object\":\"fine-tune-event\",\"type\":\"MODEL_UPLOAD_COMPLETE\"},{\"adapter_path\":\"<REDACTED>\",\"created_at\":\"2026-10-04T05:36:35Z\",\"level\":\"Info\",\"message\":\"Job finished at 2026-10-04 05:36:35\",\"model_path\":\"<REDACTED>\",\"object\":\"fine-tune-event\",\"type\":\"JOB_COMPLETE\"}],\"gradient_accumulation_steps\":4,\"id\":\"ft-48fa226c-5142\",\"learning_rate\":0.0001,\"lr_scheduler\":{\"lr_scheduler_args\":{\"num_cycles\":0.5},\"lr_scheduler_type\":\"cosine\"},\"max_grad_norm\":1,\"max_seq_length\":4096,\"max_steps\":-1,\"model\":\"Qwen/Qwen3.5-27B\",\"model_output_name\":\"michaelsigaman_879a/Qwen3.5-27B-7ba2dd9e\",\"multimodal_params\":{},\"n_checkpoints\":1,\"n_epochs\":1,\"n_evals\":0,\"packing\":true,\"progress\":{\"estimate_available\":false,\"seconds_remaining\":0},\"random_seed\":42,\"started_at\":\"2026-10-04T05:21:48Z\",\"status\":\"completed\",\"suffix\":\"\",\"token_count\":\"<REDACTED>\",\"total_price\":4000000000,\"train_on_inputs\":null,\"training_file\":\"file-21837897-1b25-48de-b4bf-73c23906316a\",\"training_files\":null,\"training_method\":{\"method\":\"sft\",\"train_on_inputs\":\"auto\"},\"training_type\":{\"lora_alpha\":32,\"lora_r\":16,\"lora_trainable_modules\":\"all-linear\",\"type\":\"Lora\"},\"updated_at\":\"2026-10-04T05:36:35.238000Z\",\"user_id\":\"<REDACTED>\",\"validation_files\":null,\"validation_split_ratio\":0,\"warmup_ratio\":0,\"warmup_steps\":0,\"weight_decay\":0}",
    "payload_sha256": "e96e161b2699290b30a7e98b04cccf194f7a78f3342121f489021a4bdd3243fd",
    "provider": "together",
    "provider_run_id": "ft-48fa226c-5142",
    "raw_record_id": "33141aef2aaa4c154d613c77120f4afbacca6592ba099fd533f3da53091bd13e",
    "redaction_applied": "true",
    "redaction_scan_findings": [],
    "redaction_scan_passed": "true",
    "redaction_version": "redact_v1",
    "source_system": "together_api",
    "user_hmac": "818bb265c1a0e50d1a1c3369337b824356a468234679f30bab62246e445ba5c9",
    "user_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "workload_id": "ft-48fa226c-5142",
    "workload_type": "finetune"
  }
]
```

#### `raw_ops.workload_conditions_raw_v1`

```json
[
  {
    "classification_rule": null,
    "event_at": "2026-10-08 03:27:42",
    "event_date": "2026-10-08",
    "fetched_at": "2026-10-10 19:40:08",
    "ingest_run_id": "bq_ingest_v1_20261010T194008Z",
    "is_benchmark_run": "true",
    "is_customer_workload": "false",
    "owner_hmac": null,
    "owner_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "payload_redacted": "{\"batch_size\":1,\"created_at\":\"2026-10-08T03:27:42.733000Z\",\"eval_steps\":0,\"events\":[],\"gradient_accumulation_steps\":8,\"id\":\"ft-c8bfe61e-9d76\",\"learning_rate\":0.0001,\"lr_scheduler\":{\"lr_scheduler_args\":{\"num_cycles\":0.5},\"lr_scheduler_type\":\"cosine\"},\"max_grad_norm\":1,\"max_seq_length\":4096,\"max_steps\":-1,\"model\":\"openai/gpt-oss-20b\",\"model_output_name\":\"michaelsigaman_879a/gpt-oss-20b-bench-1k-845de3f2\",\"multimodal_params\":{},\"n_checkpoints\":1,\"n_epochs\":1,\"n_evals\":0,\"packing\":true,\"progress\":{\"estimate_available\":false,\"seconds_remaining\":0},\"random_seed\":42,\"started_at\":\"2026-10-08T03:31:13Z\",\"status\":\"completed\",\"suffix\":\"bench-1k\",\"token_count\":\"<REDACTED>\",\"total_price\":4000000000,\"train_on_inputs\":null,\"training_file\":\"file-a1a6d941-605e-4d8a-bcd0-03fb0e2fd80f\",\"training_files\":null,\"training_method\":{\"method\":\"sft\",\"train_on_inputs\":\"auto\"},\"training_type\":{\"lora_alpha\":32,\"lora_r\":16,\"lora_trainable_modules\":\"k_proj,o_proj,q_proj,v_proj\",\"type\":\"Lora\"},\"updated_at\":\"2026-10-08T03:36:22.905000Z\",\"user_id\":\"<REDACTED>\",\"validation_files\":null,\"validation_split_ratio\":0,\"warmup_ratio\":0,\"warmup_steps\":0,\"weight_decay\":0}",
    "payload_sha256": "4f141334ed59636e8998f09e3af26fdb46ea90b8c7c9730c230fbdab47e97b3b",
    "provider": "together",
    "provider_run_id": "ft-c8bfe61e-9d76",
    "raw_record_id": "9a0aca2441c05c72c204adac1b412a481dc94029d2f7b4d254081b50a2a262e2",
    "redaction_applied": "true",
    "redaction_scan_findings": [],
    "redaction_scan_passed": "true",
    "redaction_version": "redact_v1",
    "source_system": "together_api",
    "user_hmac": "818bb265c1a0e50d1a1c3369337b824356a468234679f30bab62246e445ba5c9",
    "user_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "workload_id": "ft-c8bfe61e-9d76",
    "workload_type": "finetune"
  },
  {
    "classification_rule": null,
    "event_at": "2026-10-08 03:27:43",
    "event_date": "2026-10-08",
    "fetched_at": "2026-10-10 19:40:08",
    "ingest_run_id": "bq_ingest_v1_20261010T194008Z",
    "is_benchmark_run": "true",
    "is_customer_workload": "false",
    "owner_hmac": null,
    "owner_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "payload_redacted": "{\"batch_size\":1,\"created_at\":\"2026-10-08T03:27:43.223000Z\",\"eval_steps\":0,\"events\":[],\"gradient_accumulation_steps\":8,\"id\":\"ft-79f6d24e-ff70\",\"learning_rate\":0.0001,\"lr_scheduler\":{\"lr_scheduler_args\":{\"num_cycles\":0.5},\"lr_scheduler_type\":\"cosine\"},\"max_grad_norm\":1,\"max_seq_length\":4096,\"max_steps\":-1,\"model\":\"openai/gpt-oss-20b\",\"model_output_name\":\"michaelsigaman_879a/gpt-oss-20b-bench-10k-c78c609a\",\"multimodal_params\":{},\"n_checkpoints\":1,\"n_epochs\":1,\"n_evals\":0,\"packing\":true,\"progress\":{\"estimate_available\":false,\"seconds_remaining\":0},\"random_seed\":42,\"started_at\":\"2026-10-08T03:31:32Z\",\"status\":\"completed\",\"suffix\":\"bench-10k\",\"token_count\":\"<REDACTED>\",\"total_price\":4000000000,\"train_on_inputs\":null,\"training_file\":\"file-a1bb95d0-9bb0-4fc6-9e33-8290f7c1144e\",\"training_files\":null,\"training_method\":{\"method\":\"sft\",\"train_on_inputs\":\"auto\"},\"training_type\":{\"lora_alpha\":32,\"lora_r\":16,\"lora_trainable_modules\":\"k_proj,o_proj,q_proj,v_proj\",\"type\":\"Lora\"},\"updated_at\":\"2026-10-08T03:42:06.118000Z\",\"user_id\":\"<REDACTED>\",\"validation_files\":null,\"validation_split_ratio\":0,\"warmup_ratio\":0,\"warmup_steps\":0,\"weight_decay\":0}",
    "payload_sha256": "c221416c282d418b1de5b2df248504aba33339fddd305be090685d06032ea38d",
    "provider": "together",
    "provider_run_id": "ft-79f6d24e-ff70",
    "raw_record_id": "435690dd6e843b9a8c2e14f9f29f1a6d09d499e35fbb723946137f9d55d6ec5f",
    "redaction_applied": "true",
    "redaction_scan_findings": [],
    "redaction_scan_passed": "true",
    "redaction_version": "redact_v1",
    "source_system": "together_api",
    "user_hmac": "818bb265c1a0e50d1a1c3369337b824356a468234679f30bab62246e445ba5c9",
    "user_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "workload_id": "ft-79f6d24e-ff70",
    "workload_type": "finetune"
  },
  {
    "classification_rule": null,
    "event_at": "2026-10-08 02:47:18",
    "event_date": "2026-10-08",
    "fetched_at": "2026-10-10 19:40:08",
    "ingest_run_id": "bq_ingest_v1_20261010T194008Z",
    "is_benchmark_run": "false",
    "is_customer_workload": "true",
    "owner_hmac": null,
    "owner_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "payload_redacted": "{\"batch_size\":1,\"created_at\":\"2026-10-08T02:47:18.255000Z\",\"eval_steps\":0,\"events\":[],\"gradient_accumulation_steps\":8,\"id\":\"ft-203f3d09-1cf6\",\"learning_rate\":0.0001,\"lr_scheduler\":{\"lr_scheduler_args\":{\"num_cycles\":0.5},\"lr_scheduler_type\":\"cosine\"},\"max_grad_norm\":1,\"max_seq_length\":4096,\"max_steps\":-1,\"model\":\"openai/gpt-oss-20b\",\"model_output_name\":\"michaelsigaman_879a/gpt-oss-20b-f505b159\",\"multimodal_params\":{},\"n_checkpoints\":1,\"n_epochs\":1,\"n_evals\":0,\"packing\":true,\"progress\":{\"estimate_available\":false,\"seconds_remaining\":0},\"random_seed\":42,\"started_at\":\"2026-10-08T02:50:24Z\",\"status\":\"completed\",\"suffix\":\"\",\"token_count\":\"<REDACTED>\",\"total_price\":4000000000,\"train_on_inputs\":null,\"training_file\":\"file-21837897-1b25-48de-b4bf-73c23906316a\",\"training_files\":null,\"training_method\":{\"method\":\"sft\",\"train_on_inputs\":\"auto\"},\"training_type\":{\"lora_alpha\":32,\"lora_r\":16,\"lora_trainable_modules\":\"k_proj,o_proj,q_proj,v_proj\",\"type\":\"Lora\"},\"updated_at\":\"2026-10-08T02:59:06.539000Z\",\"user_id\":\"<REDACTED>\",\"validation_files\":null,\"validation_split_ratio\":0,\"warmup_ratio\":0,\"warmup_steps\":0,\"weight_decay\":0}",
    "payload_sha256": "5f384f838bde179f4207d9771e8847fd1446fdbabcb20b8a9301479298eb77f6",
    "provider": "together",
    "provider_run_id": "ft-203f3d09-1cf6",
    "raw_record_id": "dbd6019f226bae7ae2d59b57abc9ba48e63734a8d156459f7e6a41c22781cc33",
    "redaction_applied": "true",
    "redaction_scan_findings": [],
    "redaction_scan_passed": "true",
    "redaction_version": "redact_v1",
    "source_system": "together_api",
    "user_hmac": "818bb265c1a0e50d1a1c3369337b824356a468234679f30bab62246e445ba5c9",
    "user_hmac_key_version": "benchmark-redaction-hmac-key:v1",
    "workload_id": "ft-203f3d09-1cf6",
    "workload_type": "finetune"
  }
]
```

## Dataset: `clean_ops`

### Row counts

| Table | Type | Row count |
|---|---|---:|

| `edge_machine_registry_v1` | BASE TABLE | 7 |

| `edge_machine_state_v1` | VIEW | 0 |

| `edge_machine_state_v2` | VIEW | 0 |

| `fact_gpu_telemetry_1m_v1` | BASE TABLE | 0 |

| `fact_gpu_telemetry_v1` | BASE TABLE | 0 |

| `fact_workload_gpu_assignment_v1` | BASE TABLE | 0 |

| `workload_conditions_latest_v1` | VIEW | 0 |

| `workload_conditions_v1` | BASE TABLE | 152 |

| `workload_conditions_v1__staging_53cfdb9667` | BASE TABLE | 19 |

| `workload_outcome_v1` | BASE TABLE | 0 |

| `workload_timing_latest_v1` | VIEW | 0 |

| `workload_timing_v1` | BASE TABLE | 112 |


### Top 3 rows per table

#### `clean_ops.edge_machine_registry_v1`

```json
[
  {
    "display_name": "Radeon Office 3 (GMKtec EVO-X2)",
    "expected_gpus": "1",
    "host": "odyn-radeon3",
    "is_demo": "true",
    "notes": "GMKtec EVO-X2; CPU/APU AMD Ryzen AI Max+ 395; GPU normalized Radeon 8060S (integrated/shared). Raw driver string preserved separately.",
    "site": "london-edge",
    "vendor": "amd"
  },
  {
    "display_name": "Radeon Office 2 (GMKtec EVO-X2)",
    "expected_gpus": "1",
    "host": "odyn-radeon2",
    "is_demo": "true",
    "notes": "GMKtec EVO-X2; CPU/APU AMD Ryzen AI Max+ 395; GPU normalized Radeon 8060S (integrated/shared). Raw driver string preserved separately.",
    "site": "london-edge",
    "vendor": "amd"
  },
  {
    "display_name": "Radeon Office 1 (GMKtec EVO-X2)",
    "expected_gpus": "1",
    "host": "radeon",
    "is_demo": "true",
    "notes": "GMKtec EVO-X2; CPU/APU AMD Ryzen AI Max+ 395; GPU normalized Radeon 8060S (integrated/shared). Raw driver string preserved separately.",
    "site": "london-edge",
    "vendor": "amd"
  }
]
```

#### `clean_ops.edge_machine_state_v1`

```json
[
  {
    "age_s": "684",
    "boot_ts": null,
    "containers": null,
    "gpu_index": null,
    "gpu_name": null,
    "gpu_status": null,
    "host": "odyn-a6000",
    "load1": null,
    "power_w": null,
    "pstate": null,
    "sample_ts": "2026-10-11 14:59:13",
    "state": "NO_RECENT_SAMPLE",
    "temp_c": null,
    "util_gpu_pct": null,
    "vpn_online": "true",
    "vram_pct": null
  },
  {
    "age_s": "51",
    "boot_ts": "2026-10-05 14:37:01",
    "containers": "0",
    "gpu_index": "0",
    "gpu_name": "NVIDIA RTX A6000",
    "gpu_status": "ok",
    "host": "odyn-a6000",
    "load1": "0.33",
    "power_w": "20.05",
    "pstate": "P8",
    "sample_ts": "2026-10-11 15:09:46",
    "state": "IDLE",
    "temp_c": "35.0",
    "util_gpu_pct": "0.0",
    "vpn_online": "true",
    "vram_pct": null
  },
  {
    "age_s": "51",
    "boot_ts": "2026-10-05 14:37:01",
    "containers": "0",
    "gpu_index": "1",
    "gpu_name": "NVIDIA RTX A6000",
    "gpu_status": "ok",
    "host": "odyn-a6000",
    "load1": "0.33",
    "power_w": "12.65",
    "pstate": "P8",
    "sample_ts": "2026-10-11 15:09:46",
    "state": "IDLE",
    "temp_c": "31.0",
    "util_gpu_pct": "0.0",
    "vpn_online": "true",
    "vram_pct": null
  }
]
```

#### `clean_ops.edge_machine_state_v2`

```json
[
  {
    "age_s": "53",
    "containers": "1",
    "demo_ready": "false",
    "display_name": "DGX Spark 3",
    "expected_gpus": "1",
    "gpu_rows": "1",
    "host": "odyn-dgx3",
    "is_demo": "false",
    "last_sample_ts": "2026-10-11 15:09:46",
    "load1": "0.15",
    "power_w_sum": "4.89",
    "state": "IDLE_WITH_CONTAINER",
    "temp_c_max": "40.0",
    "util_gpu_pct_max": "0.0",
    "vendor": "nvidia",
    "vpn_online": "true"
  },
  {
    "age_s": "53",
    "containers": "1",
    "demo_ready": "true",
    "display_name": "Radeon Office 1 (GMKtec EVO-X2)",
    "expected_gpus": "1",
    "gpu_rows": "1",
    "host": "radeon",
    "is_demo": "true",
    "last_sample_ts": "2026-10-11 15:09:46",
    "load1": "0.06",
    "power_w_sum": "5.071",
    "state": "IDLE_WITH_CONTAINER",
    "temp_c_max": "26.0",
    "util_gpu_pct_max": "0.0",
    "vendor": "amd",
    "vpn_online": "true"
  },
  {
    "age_s": "53",
    "containers": "1",
    "demo_ready": "true",
    "display_name": "DGX Spark 2",
    "expected_gpus": "1",
    "gpu_rows": "1",
    "host": "odyn-dgx-spark-02",
    "is_demo": "true",
    "last_sample_ts": "2026-10-11 15:09:46",
    "load1": "0.12",
    "power_w_sum": "10.64",
    "state": "IDLE_WITH_CONTAINER",
    "temp_c_max": "36.0",
    "util_gpu_pct_max": "0.0",
    "vendor": "nvidia",
    "vpn_online": "true"
  }
]
```

#### `clean_ops.fact_gpu_telemetry_1m_v1`

_No rows._

#### `clean_ops.fact_gpu_telemetry_v1`

_No rows._

#### `clean_ops.fact_workload_gpu_assignment_v1`

_No rows._

#### `clean_ops.workload_conditions_latest_v1`

```json
[
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "batch_size_f": "0",
    "batch_size_kind": "unknown",
    "batch_size_raw": null,
    "batch_size_reason": "not available",
    "batch_size_source": "unknown",
    "batch_size_value": null,
    "classification_rule": null,
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_content_hash_reason": "serving row",
    "dataset_content_hash_source": "none",
    "dataset_identity_hmac": null,
    "dataset_identity_hmac_f": "0",
    "dataset_identity_hmac_key_version": null,
    "dataset_identity_hmac_reason": "serving row",
    "dataset_identity_hmac_source": "none",
    "dataset_uri_sanitized": null,
    "dataset_uri_sanitized_f": "0",
    "dataset_uri_sanitized_reason": "serving row",
    "dataset_uri_sanitized_source": "none",
    "gpu_count": null,
    "gpu_count_f": "0",
    "gpu_count_reason": "not available",
    "gpu_count_source": "unknown",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "is_benchmark_run": "false",
    "is_customer_workload": "true",
    "learning_rate": null,
    "learning_rate_f": "0",
    "learning_rate_reason": "serving row",
    "learning_rate_source": "unknown",
    "lora_alpha": null,
    "lora_alpha_f": "0",
    "lora_alpha_reason": "serving row",
    "lora_alpha_source": "unknown",
    "lora_rank": null,
    "lora_rank_f": "0",
    "lora_rank_reason": "serving row",
    "lora_rank_source": "unknown",
    "mapper_version": null,
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "model_id_f": "1",
    "model_id_reason": null,
    "model_id_source": "eks_kuberay.model_name",
    "precision": null,
    "precision_f": "0",
    "precision_reason": "not available",
    "precision_source": "unknown",
    "provider": "odyn",
    "provider_run_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "seq_len": null,
    "seq_len_f": "0",
    "seq_len_reason": "not available",
    "seq_len_source": "unknown",
    "source_record_ref": null,
    "source_system": "eks_kuberay",
    "tokenizer_fallback_reason": "serving row",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "tokenizer_id_reason": "serving row",
    "tokenizer_id_source": "none",
    "training_method": "unknown",
    "training_method_f": "0",
    "training_method_reason": "serving row",
    "training_method_source": "unknown",
    "training_objective": "unknown",
    "training_objective_f": "0",
    "training_objective_reason": "serving row",
    "training_objective_source": "unknown",
    "workload_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "workload_type": "serving"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "batch_size_f": "0",
    "batch_size_kind": "unknown",
    "batch_size_raw": null,
    "batch_size_reason": "not available",
    "batch_size_source": "unknown",
    "batch_size_value": null,
    "classification_rule": null,
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_content_hash_reason": "serving row",
    "dataset_content_hash_source": "none",
    "dataset_identity_hmac": null,
    "dataset_identity_hmac_f": "0",
    "dataset_identity_hmac_key_version": null,
    "dataset_identity_hmac_reason": "serving row",
    "dataset_identity_hmac_source": "none",
    "dataset_uri_sanitized": null,
    "dataset_uri_sanitized_f": "0",
    "dataset_uri_sanitized_reason": "serving row",
    "dataset_uri_sanitized_source": "none",
    "gpu_count": null,
    "gpu_count_f": "0",
    "gpu_count_reason": "not available",
    "gpu_count_source": "unknown",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "is_benchmark_run": "false",
    "is_customer_workload": "true",
    "learning_rate": null,
    "learning_rate_f": "0",
    "learning_rate_reason": "serving row",
    "learning_rate_source": "unknown",
    "lora_alpha": null,
    "lora_alpha_f": "0",
    "lora_alpha_reason": "serving row",
    "lora_alpha_source": "unknown",
    "lora_rank": null,
    "lora_rank_f": "0",
    "lora_rank_reason": "serving row",
    "lora_rank_source": "unknown",
    "mapper_version": null,
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "model_id_f": "1",
    "model_id_reason": null,
    "model_id_source": "eks_kuberay.model_name",
    "precision": null,
    "precision_f": "0",
    "precision_reason": "not available",
    "precision_source": "unknown",
    "provider": "odyn",
    "provider_run_id": "92fa7793-2c1d-5b15-83e4-de59fc529c14",
    "seq_len": null,
    "seq_len_f": "0",
    "seq_len_reason": "not available",
    "seq_len_source": "unknown",
    "source_record_ref": null,
    "source_system": "eks_kuberay",
    "tokenizer_fallback_reason": "serving row",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "tokenizer_id_reason": "serving row",
    "tokenizer_id_source": "none",
    "training_method": "unknown",
    "training_method_f": "0",
    "training_method_reason": "serving row",
    "training_method_source": "unknown",
    "training_objective": "unknown",
    "training_objective_f": "0",
    "training_objective_reason": "serving row",
    "training_objective_source": "unknown",
    "workload_id": "92fa7793-2c1d-5b15-83e4-de59fc529c14",
    "workload_type": "serving"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "batch_size_f": "0",
    "batch_size_kind": "unknown",
    "batch_size_raw": null,
    "batch_size_reason": "not available",
    "batch_size_source": "unknown",
    "batch_size_value": null,
    "classification_rule": null,
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_content_hash_reason": "serving row",
    "dataset_content_hash_source": "none",
    "dataset_identity_hmac": null,
    "dataset_identity_hmac_f": "0",
    "dataset_identity_hmac_key_version": null,
    "dataset_identity_hmac_reason": "serving row",
    "dataset_identity_hmac_source": "none",
    "dataset_uri_sanitized": null,
    "dataset_uri_sanitized_f": "0",
    "dataset_uri_sanitized_reason": "serving row",
    "dataset_uri_sanitized_source": "none",
    "gpu_count": null,
    "gpu_count_f": "0",
    "gpu_count_reason": "not available",
    "gpu_count_source": "unknown",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "is_benchmark_run": "false",
    "is_customer_workload": "true",
    "learning_rate": null,
    "learning_rate_f": "0",
    "learning_rate_reason": "serving row",
    "learning_rate_source": "unknown",
    "lora_alpha": null,
    "lora_alpha_f": "0",
    "lora_alpha_reason": "serving row",
    "lora_alpha_source": "unknown",
    "lora_rank": null,
    "lora_rank_f": "0",
    "lora_rank_reason": "serving row",
    "lora_rank_source": "unknown",
    "mapper_version": null,
    "model_id": "Qwen/Qwen2.5-7B-Instruct",
    "model_id_f": "1",
    "model_id_reason": null,
    "model_id_source": "eks_kuberay.model_name",
    "precision": null,
    "precision_f": "0",
    "precision_reason": "not available",
    "precision_source": "unknown",
    "provider": "odyn",
    "provider_run_id": "c2104b10-f154-53cb-9f19-4169369251b5",
    "seq_len": null,
    "seq_len_f": "0",
    "seq_len_reason": "not available",
    "seq_len_source": "unknown",
    "source_record_ref": null,
    "source_system": "eks_kuberay",
    "tokenizer_fallback_reason": "serving row",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "tokenizer_id_reason": "serving row",
    "tokenizer_id_source": "none",
    "training_method": "unknown",
    "training_method_f": "0",
    "training_method_reason": "serving row",
    "training_method_source": "unknown",
    "training_objective": "unknown",
    "training_objective_f": "0",
    "training_objective_reason": "serving row",
    "training_objective_source": "unknown",
    "workload_id": "c2104b10-f154-53cb-9f19-4169369251b5",
    "workload_type": "serving"
  }
]
```

#### `clean_ops.workload_conditions_v1`

```json
[
  {
    "as_of_ts": "2026-10-10 20:16:16",
    "batch_size_f": "1",
    "batch_size_kind": "per_device",
    "batch_size_raw": "1",
    "batch_size_reason": null,
    "batch_size_source": "together_api.batch_size",
    "batch_size_value": "1",
    "classification_rule": null,
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_content_hash_reason": "not available in v1",
    "dataset_content_hash_source": "unavailable",
    "dataset_identity_hmac": null,
    "dataset_identity_hmac_f": "0",
    "dataset_identity_hmac_key_version": null,
    "dataset_identity_hmac_reason": "requires dedicated key pipeline",
    "dataset_identity_hmac_source": "unavailable",
    "dataset_uri_sanitized": "file-a1bb95d0-9bb0-4fc6-9e33-8290f7c1144e",
    "dataset_uri_sanitized_f": "1",
    "dataset_uri_sanitized_reason": null,
    "dataset_uri_sanitized_source": "together_api.training_file",
    "gpu_count": null,
    "gpu_count_f": "0",
    "gpu_count_reason": "not_returned_by_provider",
    "gpu_count_source": "unknown",
    "ingest_run_id": "bq_ingest_v1_20261010T201616Z",
    "is_benchmark_run": "true",
    "is_customer_workload": "false",
    "learning_rate": "1.0E-4",
    "learning_rate_f": "1",
    "learning_rate_reason": null,
    "learning_rate_source": "together_api.learning_rate",
    "lora_alpha": "32",
    "lora_alpha_f": "1",
    "lora_alpha_reason": null,
    "lora_alpha_source": "together_api.training_type.lora_alpha",
    "lora_rank": "16",
    "lora_rank_f": "1",
    "lora_rank_reason": null,
    "lora_rank_source": "together_api.training_type.lora_r",
    "mapper_version": null,
    "model_id": "openai/gpt-oss-20b",
    "model_id_f": "1",
    "model_id_reason": null,
    "model_id_source": "together_api.model",
    "precision": null,
    "precision_f": "0",
    "precision_reason": "not_returned_by_provider",
    "precision_source": "unknown",
    "provider": "together",
    "provider_run_id": "ft-f7900121-8871",
    "seq_len": "4096",
    "seq_len_f": "1",
    "seq_len_reason": null,
    "seq_len_source": "together_api.max_seq_length",
    "source_record_ref": null,
    "source_system": "together_api",
    "tokenizer_fallback_reason": "unknown",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "tokenizer_id_reason": "not returned",
    "tokenizer_id_source": "unknown",
    "training_method": "lora",
    "training_method_f": "1",
    "training_method_reason": null,
    "training_method_source": "together_api.training_type.type",
    "training_objective": "sft",
    "training_objective_f": "1",
    "training_objective_reason": null,
    "training_objective_source": "together_api.training_method.method",
    "workload_id": "ft-f7900121-8871",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "batch_size_f": "1",
    "batch_size_kind": "per_device",
    "batch_size_raw": "1",
    "batch_size_reason": null,
    "batch_size_source": "together_api.batch_size",
    "batch_size_value": "1",
    "classification_rule": null,
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_content_hash_reason": "not available in v1",
    "dataset_content_hash_source": "unavailable",
    "dataset_identity_hmac": null,
    "dataset_identity_hmac_f": "0",
    "dataset_identity_hmac_key_version": null,
    "dataset_identity_hmac_reason": "requires dedicated key pipeline",
    "dataset_identity_hmac_source": "unavailable",
    "dataset_uri_sanitized": "file-a1bb95d0-9bb0-4fc6-9e33-8290f7c1144e",
    "dataset_uri_sanitized_f": "1",
    "dataset_uri_sanitized_reason": null,
    "dataset_uri_sanitized_source": "together_api.training_file",
    "gpu_count": null,
    "gpu_count_f": "0",
    "gpu_count_reason": "not_returned_by_provider",
    "gpu_count_source": "unknown",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "is_benchmark_run": "true",
    "is_customer_workload": "false",
    "learning_rate": "1.0E-4",
    "learning_rate_f": "1",
    "learning_rate_reason": null,
    "learning_rate_source": "together_api.learning_rate",
    "lora_alpha": "32",
    "lora_alpha_f": "1",
    "lora_alpha_reason": null,
    "lora_alpha_source": "together_api.training_type.lora_alpha",
    "lora_rank": "16",
    "lora_rank_f": "1",
    "lora_rank_reason": null,
    "lora_rank_source": "together_api.training_type.lora_r",
    "mapper_version": null,
    "model_id": "openai/gpt-oss-20b",
    "model_id_f": "1",
    "model_id_reason": null,
    "model_id_source": "together_api.model",
    "precision": null,
    "precision_f": "0",
    "precision_reason": "not_returned_by_provider",
    "precision_source": "unknown",
    "provider": "together",
    "provider_run_id": "ft-f7900121-8871",
    "seq_len": "4096",
    "seq_len_f": "1",
    "seq_len_reason": null,
    "seq_len_source": "together_api.max_seq_length",
    "source_record_ref": null,
    "source_system": "together_api",
    "tokenizer_fallback_reason": "unknown",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "tokenizer_id_reason": "not returned",
    "tokenizer_id_source": "unknown",
    "training_method": "lora",
    "training_method_f": "1",
    "training_method_reason": null,
    "training_method_source": "together_api.training_type.type",
    "training_objective": "sft",
    "training_objective_f": "1",
    "training_objective_reason": null,
    "training_objective_source": "together_api.training_method.method",
    "workload_id": "ft-f7900121-8871",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "batch_size_f": "0",
    "batch_size_kind": "unknown",
    "batch_size_raw": null,
    "batch_size_reason": "not available",
    "batch_size_source": "unknown",
    "batch_size_value": null,
    "classification_rule": null,
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_content_hash_reason": "serving row",
    "dataset_content_hash_source": "none",
    "dataset_identity_hmac": null,
    "dataset_identity_hmac_f": "0",
    "dataset_identity_hmac_key_version": null,
    "dataset_identity_hmac_reason": "serving row",
    "dataset_identity_hmac_source": "none",
    "dataset_uri_sanitized": null,
    "dataset_uri_sanitized_f": "0",
    "dataset_uri_sanitized_reason": "serving row",
    "dataset_uri_sanitized_source": "none",
    "gpu_count": null,
    "gpu_count_f": "0",
    "gpu_count_reason": "not available",
    "gpu_count_source": "unknown",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "is_benchmark_run": "false",
    "is_customer_workload": "true",
    "learning_rate": null,
    "learning_rate_f": "0",
    "learning_rate_reason": "serving row",
    "learning_rate_source": "unknown",
    "lora_alpha": null,
    "lora_alpha_f": "0",
    "lora_alpha_reason": "serving row",
    "lora_alpha_source": "unknown",
    "lora_rank": null,
    "lora_rank_f": "0",
    "lora_rank_reason": "serving row",
    "lora_rank_source": "unknown",
    "mapper_version": null,
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "model_id_f": "1",
    "model_id_reason": null,
    "model_id_source": "eks_kuberay.model_name",
    "precision": null,
    "precision_f": "0",
    "precision_reason": "not available",
    "precision_source": "unknown",
    "provider": "odyn",
    "provider_run_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "seq_len": null,
    "seq_len_f": "0",
    "seq_len_reason": "not available",
    "seq_len_source": "unknown",
    "source_record_ref": null,
    "source_system": "eks_kuberay",
    "tokenizer_fallback_reason": "serving row",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "tokenizer_id_reason": "serving row",
    "tokenizer_id_source": "none",
    "training_method": "unknown",
    "training_method_f": "0",
    "training_method_reason": "serving row",
    "training_method_source": "unknown",
    "training_objective": "unknown",
    "training_objective_f": "0",
    "training_objective_reason": "serving row",
    "training_objective_source": "unknown",
    "workload_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "workload_type": "serving"
  }
]
```

#### `clean_ops.workload_conditions_v1__staging_53cfdb9667`

```json
[
  {
    "as_of_ts": "2026-10-10 19:40:08",
    "batch_size_f": "1",
    "batch_size_kind": "per_device",
    "batch_size_raw": "1",
    "batch_size_reason": null,
    "batch_size_source": "together_api.batch_size",
    "batch_size_value": "1",
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_content_hash_reason": "not available in v1",
    "dataset_content_hash_source": "unavailable",
    "dataset_identity_hmac": null,
    "dataset_identity_hmac_f": "0",
    "dataset_identity_hmac_key_version": null,
    "dataset_identity_hmac_reason": "requires dedicated key pipeline",
    "dataset_identity_hmac_source": "unavailable",
    "dataset_uri_sanitized": "file-a1bb95d0-9bb0-4fc6-9e33-8290f7c1144e",
    "dataset_uri_sanitized_f": "1",
    "dataset_uri_sanitized_reason": null,
    "dataset_uri_sanitized_source": "together_api.training_file",
    "gpu_count": null,
    "gpu_count_f": "0",
    "gpu_count_reason": "not_returned_by_provider",
    "gpu_count_source": "unknown",
    "ingest_run_id": "bq_ingest_v1_20261010T194008Z",
    "is_benchmark_run": "true",
    "is_customer_workload": "false",
    "learning_rate": "1.0E-4",
    "learning_rate_f": "1",
    "learning_rate_reason": null,
    "learning_rate_source": "together_api.learning_rate",
    "lora_alpha": "32",
    "lora_alpha_f": "1",
    "lora_alpha_reason": null,
    "lora_alpha_source": "together_api.training_type.lora_alpha",
    "lora_rank": "16",
    "lora_rank_f": "1",
    "lora_rank_reason": null,
    "lora_rank_source": "together_api.training_type.lora_r",
    "model_id": "openai/gpt-oss-20b",
    "model_id_f": "1",
    "model_id_reason": null,
    "model_id_source": "together_api.model",
    "precision": null,
    "precision_f": "0",
    "precision_reason": "not_returned_by_provider",
    "precision_source": "unknown",
    "provider": "together",
    "provider_run_id": "ft-f7900121-8871",
    "seq_len": "4096",
    "seq_len_f": "1",
    "seq_len_reason": null,
    "seq_len_source": "together_api.max_seq_length",
    "source_record_ref": null,
    "source_system": "together_api",
    "tokenizer_fallback_reason": "unknown",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "tokenizer_id_reason": "not returned",
    "tokenizer_id_source": "unknown",
    "training_method": "lora",
    "training_method_f": "1",
    "training_method_reason": null,
    "training_method_source": "together_api.training_type.type",
    "training_objective": "sft",
    "training_objective_f": "1",
    "training_objective_reason": null,
    "training_objective_source": "together_api.training_method.method",
    "workload_id": "ft-f7900121-8871",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 19:40:08",
    "batch_size_f": "0",
    "batch_size_kind": "unknown",
    "batch_size_raw": null,
    "batch_size_reason": "not available",
    "batch_size_source": "unknown",
    "batch_size_value": null,
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_content_hash_reason": "serving row",
    "dataset_content_hash_source": "none",
    "dataset_identity_hmac": null,
    "dataset_identity_hmac_f": "0",
    "dataset_identity_hmac_key_version": null,
    "dataset_identity_hmac_reason": "serving row",
    "dataset_identity_hmac_source": "none",
    "dataset_uri_sanitized": null,
    "dataset_uri_sanitized_f": "0",
    "dataset_uri_sanitized_reason": "serving row",
    "dataset_uri_sanitized_source": "none",
    "gpu_count": null,
    "gpu_count_f": "0",
    "gpu_count_reason": "not available",
    "gpu_count_source": "unknown",
    "ingest_run_id": "bq_ingest_v1_20261010T194008Z",
    "is_benchmark_run": "false",
    "is_customer_workload": "true",
    "learning_rate": null,
    "learning_rate_f": "0",
    "learning_rate_reason": "serving row",
    "learning_rate_source": "unknown",
    "lora_alpha": null,
    "lora_alpha_f": "0",
    "lora_alpha_reason": "serving row",
    "lora_alpha_source": "unknown",
    "lora_rank": null,
    "lora_rank_f": "0",
    "lora_rank_reason": "serving row",
    "lora_rank_source": "unknown",
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "model_id_f": "1",
    "model_id_reason": null,
    "model_id_source": "eks_kuberay.model_name",
    "precision": null,
    "precision_f": "0",
    "precision_reason": "not available",
    "precision_source": "unknown",
    "provider": "odyn",
    "provider_run_id": "92fa7793-2c1d-5b15-83e4-de59fc529c14",
    "seq_len": null,
    "seq_len_f": "0",
    "seq_len_reason": "not available",
    "seq_len_source": "unknown",
    "source_record_ref": null,
    "source_system": "eks_kuberay",
    "tokenizer_fallback_reason": "serving row",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "tokenizer_id_reason": "serving row",
    "tokenizer_id_source": "none",
    "training_method": "unknown",
    "training_method_f": "0",
    "training_method_reason": "serving row",
    "training_method_source": "unknown",
    "training_objective": "unknown",
    "training_objective_f": "0",
    "training_objective_reason": "serving row",
    "training_objective_source": "unknown",
    "workload_id": "92fa7793-2c1d-5b15-83e4-de59fc529c14",
    "workload_type": "serving"
  },
  {
    "as_of_ts": "2026-10-10 19:40:08",
    "batch_size_f": "0",
    "batch_size_kind": "unknown",
    "batch_size_raw": null,
    "batch_size_reason": "not available",
    "batch_size_source": "unknown",
    "batch_size_value": null,
    "dataset_content_hash": null,
    "dataset_content_hash_f": "0",
    "dataset_content_hash_reason": "serving row",
    "dataset_content_hash_source": "none",
    "dataset_identity_hmac": null,
    "dataset_identity_hmac_f": "0",
    "dataset_identity_hmac_key_version": null,
    "dataset_identity_hmac_reason": "serving row",
    "dataset_identity_hmac_source": "none",
    "dataset_uri_sanitized": null,
    "dataset_uri_sanitized_f": "0",
    "dataset_uri_sanitized_reason": "serving row",
    "dataset_uri_sanitized_source": "none",
    "gpu_count": null,
    "gpu_count_f": "0",
    "gpu_count_reason": "not available",
    "gpu_count_source": "unknown",
    "ingest_run_id": "bq_ingest_v1_20261010T194008Z",
    "is_benchmark_run": "false",
    "is_customer_workload": "true",
    "learning_rate": null,
    "learning_rate_f": "0",
    "learning_rate_reason": "serving row",
    "learning_rate_source": "unknown",
    "lora_alpha": null,
    "lora_alpha_f": "0",
    "lora_alpha_reason": "serving row",
    "lora_alpha_source": "unknown",
    "lora_rank": null,
    "lora_rank_f": "0",
    "lora_rank_reason": "serving row",
    "lora_rank_source": "unknown",
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "model_id_f": "1",
    "model_id_reason": null,
    "model_id_source": "eks_kuberay.model_name",
    "precision": null,
    "precision_f": "0",
    "precision_reason": "not available",
    "precision_source": "unknown",
    "provider": "odyn",
    "provider_run_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "seq_len": null,
    "seq_len_f": "0",
    "seq_len_reason": "not available",
    "seq_len_source": "unknown",
    "source_record_ref": null,
    "source_system": "eks_kuberay",
    "tokenizer_fallback_reason": "serving row",
    "tokenizer_fallback_used": null,
    "tokenizer_fallback_used_f": "0",
    "tokenizer_id": null,
    "tokenizer_id_f": "0",
    "tokenizer_id_reason": "serving row",
    "tokenizer_id_source": "none",
    "training_method": "unknown",
    "training_method_f": "0",
    "training_method_reason": "serving row",
    "training_method_source": "unknown",
    "training_objective": "unknown",
    "training_objective_f": "0",
    "training_objective_reason": "serving row",
    "training_objective_source": "unknown",
    "workload_id": "90cf04b2-be84-5f59-8242-046b2bff9ead",
    "workload_type": "serving"
  }
]
```

#### `clean_ops.workload_outcome_v1`

_No rows._

#### `clean_ops.workload_timing_latest_v1`

```json
[
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "benchmark_timing_eligible": "true",
    "benchmark_timing_eligible_reason": "requires wall_time and training_time",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "mapper_version": null,
    "model_available_at": "2026-10-09 16:10:36",
    "model_available_at_f": "1",
    "model_available_at_reason": null,
    "model_available_at_source": "together.events.JOB_COMPLETE",
    "provider": "together",
    "source_system": "together_api",
    "submitted_at": "2026-10-09 16:01:15",
    "submitted_at_f": "1",
    "submitted_at_reason": null,
    "submitted_at_source": "provider_server_clock",
    "trainer_started_at": "2026-10-09 16:05:26",
    "trainer_started_at_f": "1",
    "trainer_started_at_reason": null,
    "trainer_started_at_source": "together.events.TRAINING_START",
    "training_ended_at": "2026-10-09 16:08:05",
    "training_ended_at_f": "1",
    "training_ended_at_reason": null,
    "training_ended_at_source": "together.events.TRAINING_COMPLETE",
    "training_time_min": "2.65",
    "training_time_min_f": "1",
    "training_time_min_reason": null,
    "training_time_min_source": "derived(trainer_started_at,training_ended_at)",
    "wall_time_min": "9.3458",
    "wall_time_min_f": "1",
    "wall_time_min_reason": null,
    "wall_time_min_source": "derived(created_at,model_available_at)",
    "workload_id": "ft-13dd5f5f-d688",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "benchmark_timing_eligible": "true",
    "benchmark_timing_eligible_reason": "requires wall_time and training_time",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "mapper_version": null,
    "model_available_at": "2026-10-09 16:15:08",
    "model_available_at_f": "1",
    "model_available_at_reason": null,
    "model_available_at_source": "together.events.JOB_COMPLETE",
    "provider": "together",
    "source_system": "together_api",
    "submitted_at": "2026-10-09 16:00:55",
    "submitted_at_f": "1",
    "submitted_at_reason": null,
    "submitted_at_source": "provider_server_clock",
    "trainer_started_at": "2026-10-09 16:04:24",
    "trainer_started_at_f": "1",
    "trainer_started_at_reason": null,
    "trainer_started_at_source": "together.events.TRAINING_START",
    "training_ended_at": "2026-10-09 16:12:46",
    "training_ended_at_f": "1",
    "training_ended_at_reason": null,
    "training_ended_at_source": "together.events.TRAINING_COMPLETE",
    "training_time_min": "8.366666666666667",
    "training_time_min_f": "1",
    "training_time_min_reason": null,
    "training_time_min_source": "derived(trainer_started_at,training_ended_at)",
    "wall_time_min": "14.210616666666665",
    "wall_time_min_f": "1",
    "wall_time_min_reason": null,
    "wall_time_min_source": "derived(created_at,model_available_at)",
    "workload_id": "ft-15dec247-d184",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "benchmark_timing_eligible": "true",
    "benchmark_timing_eligible_reason": "requires wall_time and training_time",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "mapper_version": null,
    "model_available_at": "2026-10-09 15:59:07",
    "model_available_at_f": "1",
    "model_available_at_reason": null,
    "model_available_at_source": "together.events.JOB_COMPLETE",
    "provider": "together",
    "source_system": "together_api",
    "submitted_at": "2026-10-09 15:50:03",
    "submitted_at_f": "1",
    "submitted_at_reason": null,
    "submitted_at_source": "provider_server_clock",
    "trainer_started_at": "2026-10-09 15:54:01",
    "trainer_started_at_f": "1",
    "trainer_started_at_reason": null,
    "trainer_started_at_source": "together.events.TRAINING_START",
    "training_ended_at": "2026-10-09 15:56:37",
    "training_ended_at_f": "1",
    "training_ended_at_reason": null,
    "training_ended_at_source": "together.events.TRAINING_COMPLETE",
    "training_time_min": "2.6",
    "training_time_min_f": "1",
    "training_time_min_reason": null,
    "training_time_min_source": "derived(trainer_started_at,training_ended_at)",
    "wall_time_min": "9.054183333333333",
    "wall_time_min_f": "1",
    "wall_time_min_reason": null,
    "wall_time_min_source": "derived(created_at,model_available_at)",
    "workload_id": "ft-1fce124e-17b1",
    "workload_type": "finetune"
  }
]
```

#### `clean_ops.workload_timing_v1`

```json
[
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "benchmark_timing_eligible": "true",
    "benchmark_timing_eligible_reason": "requires wall_time and training_time",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "mapper_version": null,
    "model_available_at": "2026-10-09 16:15:49",
    "model_available_at_f": "1",
    "model_available_at_reason": null,
    "model_available_at_source": "together.events.JOB_COMPLETE",
    "provider": "together",
    "source_system": "together_api",
    "submitted_at": "2026-10-09 16:01:15",
    "submitted_at_f": "1",
    "submitted_at_reason": null,
    "submitted_at_source": "provider_server_clock",
    "trainer_started_at": "2026-10-09 16:05:05",
    "trainer_started_at_f": "1",
    "trainer_started_at_reason": null,
    "trainer_started_at_source": "together.events.TRAINING_START",
    "training_ended_at": "2026-10-09 16:13:30",
    "training_ended_at_f": "1",
    "training_ended_at_reason": null,
    "training_ended_at_source": "together.events.TRAINING_COMPLETE",
    "training_time_min": "8.416666666666666",
    "training_time_min_f": "1",
    "training_time_min_reason": null,
    "training_time_min_source": "derived(trainer_started_at,training_ended_at)",
    "wall_time_min": "14.55435",
    "wall_time_min_f": "1",
    "wall_time_min_reason": null,
    "wall_time_min_source": "derived(created_at,model_available_at)",
    "workload_id": "ft-f7900121-8871",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "benchmark_timing_eligible": "true",
    "benchmark_timing_eligible_reason": "requires wall_time and training_time",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "mapper_version": null,
    "model_available_at": "2026-10-09 16:10:36",
    "model_available_at_f": "1",
    "model_available_at_reason": null,
    "model_available_at_source": "together.events.JOB_COMPLETE",
    "provider": "together",
    "source_system": "together_api",
    "submitted_at": "2026-10-09 16:01:15",
    "submitted_at_f": "1",
    "submitted_at_reason": null,
    "submitted_at_source": "provider_server_clock",
    "trainer_started_at": "2026-10-09 16:05:26",
    "trainer_started_at_f": "1",
    "trainer_started_at_reason": null,
    "trainer_started_at_source": "together.events.TRAINING_START",
    "training_ended_at": "2026-10-09 16:08:05",
    "training_ended_at_f": "1",
    "training_ended_at_reason": null,
    "training_ended_at_source": "together.events.TRAINING_COMPLETE",
    "training_time_min": "2.65",
    "training_time_min_f": "1",
    "training_time_min_reason": null,
    "training_time_min_source": "derived(trainer_started_at,training_ended_at)",
    "wall_time_min": "9.3458",
    "wall_time_min_f": "1",
    "wall_time_min_reason": null,
    "wall_time_min_source": "derived(created_at,model_available_at)",
    "workload_id": "ft-13dd5f5f-d688",
    "workload_type": "finetune"
  },
  {
    "as_of_ts": "2026-10-10 20:17:07",
    "benchmark_timing_eligible": "true",
    "benchmark_timing_eligible_reason": "requires wall_time and training_time",
    "ingest_run_id": "bq_ingest_v1_20261010T201707Z",
    "mapper_version": null,
    "model_available_at": "2026-10-04 05:26:13",
    "model_available_at_f": "1",
    "model_available_at_reason": null,
    "model_available_at_source": "together.events.JOB_COMPLETE",
    "provider": "together",
    "source_system": "together_api",
    "submitted_at": "2026-10-04 05:15:58",
    "submitted_at_f": "1",
    "submitted_at_reason": null,
    "submitted_at_source": "provider_server_clock",
    "trainer_started_at": "2026-10-04 05:21:05",
    "trainer_started_at_f": "1",
    "trainer_started_at_reason": null,
    "trainer_started_at_source": "together.events.TRAINING_START",
    "training_ended_at": "2026-10-04 05:23:45",
    "training_ended_at_f": "1",
    "training_ended_at_reason": null,
    "training_ended_at_source": "together.events.TRAINING_COMPLETE",
    "training_time_min": "2.6666666666666665",
    "training_time_min_f": "1",
    "training_time_min_reason": null,
    "training_time_min_source": "derived(trainer_started_at,training_ended_at)",
    "wall_time_min": "10.243633333333333",
    "wall_time_min_f": "1",
    "wall_time_min_reason": null,
    "wall_time_min_source": "derived(created_at,model_available_at)",
    "workload_id": "ft-8d9597ed-cfa0",
    "workload_type": "finetune"
  }
]
```

## Timeliness Checks

### raw_ops.pg_state_snapshot_v1

```json
[
  {
    "max_captured_at": "2026-10-11 10:13:15",
    "min_captured_at": "2026-10-11 10:13:15",
    "rows_before_sep1": "0",
    "rows_since_sep1": "851",
    "total_rows": "851"
  }
]
```

### Missing capture dates since 2026-09-01

```json
[
  {
    "missing_day_list": [
      "2026-09-01",
      "2026-09-02",
      "2026-09-03",
      "2026-09-04",
      "2026-09-05",
      "2026-09-06",
      "2026-09-07",
      "2026-09-08",
      "2026-09-09",
      "2026-09-10",
      "2026-09-11",
      "2026-09-12",
      "2026-09-13",
      "2026-09-14",
      "2026-09-15",
      "2026-09-16",
      "2026-09-17",
      "2026-09-18",
      "2026-09-19",
      "2026-09-20",
      "2026-09-21",
      "2026-09-22",
      "2026-09-23",
      "2026-09-24",
      "2026-09-25",
      "2026-09-26",
      "2026-09-27",
      "2026-09-28",
      "2026-09-29",
      "2026-09-30",
      "2026-10-01",
      "2026-10-02",
      "2026-10-03",
      "2026-10-04",
      "2026-10-05",
      "2026-10-06",
      "2026-10-07",
      "2026-10-08",
      "2026-10-09",
      "2026-10-10"
    ],
    "missing_days": "40"
  }
]
```

## GPU Telemetry Checks

### clean_ops.fact_gpu_telemetry_v1 (last 365 days)

```json
[
  {
    "distinct_gpus": "0",
    "max_ts": null,
    "min_ts": null,
    "total_rows": "0"
  }
]
```

### clean_ops.fact_gpu_telemetry_1m_v1 (last 365 days)

```json
[
  {
    "distinct_gpus": "0",
    "max_ts": null,
    "min_ts": null,
    "total_rows": "0"
  }
]
```

### raw_ops.edge_gpu_samples_v1 (last 30 days)

```json
[
  {
    "distinct_host_gpu": "8",
    "distinct_hosts": "7",
    "max_ts": "2026-10-11 15:10:46",
    "min_ts": "2026-10-11 06:49:16",
    "total_rows": "2715"
  }
]
```

### raw_ops.edge_gpu_samples_v1 cadence (last 30 minutes)

```json
[
  {
    "host_gpu_with_recent_samples": "6",
    "median_interval_seconds": "60",
    "p90_interval_seconds": "333"
  }
]
```

### clean_ops.edge_machine_state_v2 freshness

```json
[
  {
    "hosts_fresh_le_2m": "5",
    "hosts_fresh_le_30s": "5",
    "hosts_total": "7",
    "max_age_s": "16343"
  }
]
```
