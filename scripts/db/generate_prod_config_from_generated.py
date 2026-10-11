#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "scripts" / "db" / "pg_ingest_columns.generated.json"
OUTPUT = ROOT / "config" / "pg_state_extractor_v0.prod.sample.json"

CADENCE_BY_TABLE = {
    "ray_train_jobs": "change_only",
    "post_training_workloads": "change_only",
    "scheduler_workload_requests": "change_only",
    "finetune_billing_intervals": "change_only",
    "job_cost_summary": "daily_full",
    "finetune_metrics_history": "change_only",
    "gpu_reservations": "change_only",
    "gpu_baseline_rates": "daily_full",
    "nodes": "daily_full",
    "gpu_inventory": "change_only",
    "ray_clusters": "change_only",
    "ray_cluster_workers": "change_only",
    "container_gpu_assignments": "change_only",
    "ingest_job_placement_v1": "change_only",
}

PK_BY_TABLE = {
    "ray_train_jobs": ["id"],
    "post_training_workloads": ["id"],
    "scheduler_workload_requests": ["id"],
    "finetune_billing_intervals": ["id"],
    "job_cost_summary": ["job_id"],
    "finetune_metrics_history": ["id"],
    "gpu_reservations": ["id"],
    "gpu_baseline_rates": ["provider", "sku", "intake_type"],
    "nodes": ["id"],
    "gpu_inventory": ["gpu_key"],
    "ray_clusters": ["id"],
    "ray_cluster_workers": ["id"],
    "container_gpu_assignments": ["container_id", "gpu_key"],
    "ingest_job_placement_v1": ["job_id"],
}

HMAC_BY_TABLE = {
    "ray_train_jobs": ["owner_user_id", "dataset_s3_key"],
    "post_training_workloads": ["owner_user_id"],
    "scheduler_workload_requests": ["user_id"],
    "finetune_billing_intervals": ["owner_user_id"],
    "job_cost_summary": ["tenant_id"],
    "gpu_reservations": ["user_id"],
    "ray_clusters": ["user_id"],
    "ingest_job_placement_v1": ["job_id", "gpu_reservation_id"],
}

JSON_ALLOWLISTS_BY_TABLE = {
    "scheduler_workload_requests": {
        "accepted_recommendation_json": True,
        "response_json": True,
    }
}


def main() -> None:
    raw = json.loads(GENERATED.read_text(encoding="utf-8"))
    tables = raw["tables"]

    out_tables = []
    for t in tables:
        table = str(t["table"])
        cols = list(t.get("columns") or [])
        out_tables.append(
            {
                "schema": str(t.get("schema", "public")),
                "table": table,
                "cadence": CADENCE_BY_TABLE.get(table, "change_only"),
                "columns": cols,
                "pk_columns": PK_BY_TABLE.get(table, ["id"]),
                "hmac_fields": HMAC_BY_TABLE.get(table, []),
                "json_allowlists": JSON_ALLOWLISTS_BY_TABLE.get(table, {}),
            }
        )

    cfg = {
        "pg_dsn_env": "ODYN_REPLICA_DSN",
        "pg_database": "marketplace",
        "sslmode": "prefer",
        "pg_password_secret_name": "odyn/ingest-ro-db",
        "pg_password_secret_region": "us-west-2",
        "gcs_bucket": "inbound-dahlia-507808-g1-raw-landing",
        "gcs_prefix": "pg",
        "kms_hmac_key_arn": "arn:aws:kms:us-west-2:123456789012:key/REPLACE_WITH_REAL_KEY",
        "hmac_key_version": "kms-hmac-v1",
        "tables": out_tables,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
