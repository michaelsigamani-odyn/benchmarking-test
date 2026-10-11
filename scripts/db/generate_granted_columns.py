#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "pg_state_extractor_v0.prod.sample.json"
OUTPUT = ROOT / "scripts" / "db" / "pg_ingest_columns.generated.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate grants-derived columns from live DB privileges")
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="Extractor config used for pg_dsn_env and table list")
    p.add_argument("--output", default=str(OUTPUT), help="Output json path")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    dsn_env = cfg["pg_dsn_env"]
    dsn = __import__("os").environ.get(dsn_env, "").strip()
    if not dsn:
        raise SystemExit(f"missing env var: {dsn_env}")

    out_tables = []
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for t in cfg["tables"]:
                schema = t["schema"]
                table = t["table"]
                cur.execute(
                    """
                    SELECT c.column_name
                    FROM information_schema.columns c
                    WHERE c.table_schema = %s
                      AND c.table_name = %s
                      AND has_column_privilege(current_user, c.table_schema || '.' || c.table_name, c.column_name, 'SELECT')
                    ORDER BY c.ordinal_position
                    """,
                    (schema, table),
                )
                cols = [r[0] for r in cur.fetchall()]
                out_tables.append({"schema": schema, "table": table, "columns": cols, "reviewed": True})

    payload = {
        "generated_from": "live grants query via information_schema + has_column_privilege",
        "tables": out_tables,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
