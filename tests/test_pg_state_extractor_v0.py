from __future__ import annotations

import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import psycopg
from pgserver import get_server


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pg_state_extractor_v0.py"
spec = importlib.util.spec_from_file_location("pg_state_extractor_v0", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules["pg_state_extractor_v0"] = mod
spec.loader.exec_module(mod)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SQL = REPO_ROOT / "tests" / "fixtures" / "extractor_fixture.sql"
GRANTS_SQL = REPO_ROOT / "scripts" / "db" / "fixture_grants.sql"
GENERATED_COLUMNS = REPO_ROOT / "scripts" / "db" / "pg_ingest_columns.generated.json"


class SpyKMS:
    def __init__(self):
        self.key_ids: list[str] = []
        self.messages: list[str] = []

    def generate_mac(self, KeyId, Message, MacAlgorithm):  # noqa: N803
        # Reject key/<id> and aliases. Accept full key ARN or bare key id/uuid only.
        if str(KeyId).startswith("key/") or ":alias/" in str(KeyId) or str(KeyId).startswith("alias/"):
            raise RuntimeError(f"invalid KeyId form: {KeyId}")
        if not mod.is_valid_kms_key_ref(str(KeyId)):
            raise RuntimeError(f"invalid KeyId form: {KeyId}")
        if len(Message) < 1:
            raise RuntimeError("ValidationException: Member must have length greater than or equal to 1")
        self.key_ids.append(str(KeyId))
        self.messages.append(Message.decode("utf-8"))
        return {"Mac": hashlib.sha256(Message).digest()}


class ExtractorRealPostgresFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pgdata = Path(tempfile.mkdtemp(prefix="pgserver-"))
        cls.server = get_server(cls.pgdata, cleanup_mode="delete")
        cls.uri = cls.server.get_uri("postgres")

    @classmethod
    def tearDownClass(cls):
        with contextlib.suppress(Exception):
            cls.server.cleanup()
        with contextlib.suppress(Exception):
            shutil.rmtree(cls.pgdata, ignore_errors=True)

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="extractor-tests-"))
        self.sink_dir = self.tmpdir / "sink"
        self.state_dir = self.tmpdir / "state"
        self.kms = SpyKMS()
        self._reset_db()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _reset_db(self):
        self.server.psql(FIXTURE_SQL.read_text(encoding="utf-8"))
        self.server.psql(GRANTS_SQL.read_text(encoding="utf-8"))

    def _all_tables_config(self):
        generated = json.loads(GENERATED_COLUMNS.read_text(encoding="utf-8"))["tables"]
        by_name = {t["table"]: t for t in generated}
        cfg_tables = []
        for table in [
            "ray_train_jobs",
            "post_training_workloads",
            "scheduler_workload_requests",
            "finetune_billing_intervals",
            "job_cost_summary",
            "finetune_metrics_history",
            "gpu_reservations",
            "gpu_baseline_rates",
            "nodes",
            "gpu_inventory",
            "ray_clusters",
            "ray_cluster_workers",
            "container_gpu_assignments",
            "ingest_job_placement_v1",
        ]:
            cols = list(by_name[table]["columns"])
            pk = {
                "job_cost_summary": ["job_id"],
                "gpu_baseline_rates": ["provider", "sku", "intake_type"],
                "gpu_inventory": ["gpu_key"],
                "container_gpu_assignments": ["container_id", "gpu_key"],
                "ingest_job_placement_v1": ["job_id"],
            }.get(table, ["id"])
            hmac = {
                "ray_train_jobs": ["owner_user_id", "dataset_s3_key"],
                "post_training_workloads": ["owner_user_id"],
                "finetune_billing_intervals": ["owner_user_id"],
                "scheduler_workload_requests": ["user_id"],
                "ray_clusters": ["user_id"],
                "gpu_reservations": ["user_id"],
                "job_cost_summary": ["tenant_id"],
                "ingest_job_placement_v1": ["job_id", "gpu_reservation_id"],
            }.get(table, [])
            allowlists = {"accepted_recommendation_json": True, "response_json": True} if table == "scheduler_workload_requests" else {}
            cfg_tables.append(
                {
                    "schema": "public",
                    "table": table,
                    "cadence": "change_only" if table not in {"job_cost_summary", "gpu_baseline_rates", "nodes"} else "daily_full",
                    "columns": cols,
                    "pk_columns": pk,
                    "hmac_fields": hmac,
                    "json_allowlists": allowlists,
                }
            )

        return mod.ExtractorConfig(
            pg_dsn_env="UNUSED",
            pg_database="postgres",
            sslmode="prefer",
            sslmode_explicit=True,
            pg_password_secret_name="odyn/ingest-ro-db",
            pg_password_secret_region="us-west-2",
            gcs_bucket="unused",
            gcs_prefix="pg",
            kms_hmac_key_arn="arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012",
            hmac_key_version="kms-hmac-v1",
            tables=cfg_tables,
        )

    def _run(self, *, cfg=None, run_id=None, dry_run=False):
        cfg = cfg or self._all_tables_config()
        sink = mod.LocalDirectorySink(self.sink_dir)
        state = mod.JsonStateStore(self.state_dir)
        with psycopg.connect(self.uri) as conn:
            with conn.cursor() as cur:
                cur.execute("SET ROLE odyn_ingest_ro")
            result = mod.run(
                cfg,
                since=None,
                limit_per_table=5000,
                kms_client=self.kms,
                sink=sink,
                state_store=state,
                conn=conn,
                ingest_run_id=run_id,
                dry_run=dry_run,
            )
        return result

    def _db_exec(self, sql, params=None):
        with psycopg.connect(self.uri) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
            conn.commit()

    def _manifest_path(self, run_id: str) -> Path:
        return self.sink_dir / f"pg/v1/run={run_id}/_manifest.json"

    def _all_records_from_manifest(self, run_id: str) -> list[dict]:
        manifest = json.loads(self._manifest_path(run_id).read_text(encoding="utf-8"))
        out: list[dict] = []
        for item in manifest.get("files", []):
            p = self.sink_dir / item["object"]
            if p.suffix != ".gz":
                continue
            with gzip.open(p, "rt", encoding="utf-8") as fp:
                out.extend(json.loads(line) for line in fp if line.strip())
        return out

    def test_01_kms_keyid_uses_full_arn_not_key_slash_id(self):
        self._run()
        self.assertGreater(len(self.kms.key_ids), 0)
        for kid in self.kms.key_ids:
            self.assertTrue(kid.startswith("arn:aws:kms:"))
            self.assertFalse(kid.startswith("key/"))

    def test_02_state_saved_only_after_manifest_full_run(self):
        cfg = self._all_tables_config()
        self._run(cfg=cfg, run_id="baseline")

        baseline_state_t1 = json.loads((self.state_dir / "public.ray_train_jobs.state.json").read_text(encoding="utf-8"))

        bad_cfg = self._all_tables_config()
        table2 = next(t for t in bad_cfg.tables if t["table"] == "post_training_workloads")
        table2["columns"] = table2["columns"] + ["not_granted_col"]
        with self.assertRaises(RuntimeError):
            self._run(cfg=bad_cfg, run_id="fail_mid")

        # state remains untouched after failed run
        after_fail = json.loads((self.state_dir / "public.ray_train_jobs.state.json").read_text(encoding="utf-8"))
        self.assertEqual(after_fail, baseline_state_t1)

        self._db_exec("UPDATE public.ray_train_jobs SET status='changed' WHERE id=%s", ("rtj-normal",))
        rerun = self._run(cfg=cfg, run_id="rerun")
        t1 = next(t for t in rerun["tables"] if t["table_name"] == "public.ray_train_jobs")
        self.assertEqual(t1["emitted_row_count"], 1)

    def test_03_pk_columns_must_be_granted_columns(self):
        cfg = self._all_tables_config()
        t = next(x for x in cfg.tables if x["table"] == "nodes")
        t["pk_columns"] = ["missing_pk"]
        with self.assertRaises(RuntimeError):
            self._run(cfg=cfg)

    def test_04_required_hmac_fields_validation(self):
        cfg = self._all_tables_config()
        t = next(x for x in cfg.tables if x["table"] == "ray_train_jobs")
        t["hmac_fields"] = ["owner_user_id"]  # missing dataset_s3_key
        with self.assertRaises(RuntimeError):
            self._run(cfg=cfg)

    def test_05_recursive_json_string_scanning_and_mask_abort(self):
        # free-text value in JSON should mask and alert
        self._db_exec(
            "UPDATE public.scheduler_workload_requests SET response_json=%s::jsonb WHERE id=%s",
            ('{"status":"ok","next_route":"hello user@example.com"}', "swr-normal"),
        )
        res = self._run()
        self.assertTrue(res["alert"])

        # id-path value in JSON should abort
        self._db_exec(
            "UPDATE public.scheduler_workload_requests SET accepted_recommendation_json=%s::jsonb WHERE id=%s",
            ('{"selected_placement":{"node_id":"arn:aws:iam::000000000000:role/x"}}', "swr-normal"),
        )
        with self.assertRaises(RuntimeError):
            self._run()

    def test_06_url_pattern_and_signed_param_masking(self):
        txt = "https://s-host.example/path?X-Amz-Signature=abc&X-Amz-Credential=def prose ? mark"
        masked, hits = mod.mask_free_text(txt)
        self.assertIn("signed_url_param", hits)
        self.assertNotIn("X-Amz-Signature=abc", masked)
        self.assertNotIn("X-Amz-Credential=def", masked)

    def test_07_dry_run_does_not_build_gcs_client(self):
        original = mod.GcsSink

        class BoomSink:
            def __init__(self, *args, **kwargs):
                raise AssertionError("GcsSink should not be constructed in dry-run")

        mod.GcsSink = BoomSink
        try:
            cfg = self._all_tables_config()
            state = mod.JsonStateStore(self.state_dir)
            stdout = io.StringIO()
            with psycopg.connect(self.uri) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET ROLE odyn_ingest_ro")
                with contextlib.redirect_stdout(stdout):
                    result = mod.run(
                        cfg,
                        since=None,
                        limit_per_table=5000,
                        kms_client=self.kms,
                        sink=None,
                        state_store=state,
                        conn=conn,
                        dry_run=True,
                    )
            out = stdout.getvalue()
            self.assertIn("FREE_TEXT_FIELDS:", out)
            self.assertIn("STRUCTURED_FIELDS:", out)
            self.assertIn("FINDING table=", out)
            self.assertIn("findings", result)
            self.assertEqual(result["findings_count"], len(result["findings"]))
        finally:
            mod.GcsSink = original

    def test_08_manifest_has_file_hashes_and_loader_verifies(self):
        res = self._run(run_id="hashrun")
        manifest_path = self._manifest_path("hashrun")
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertIn("files", manifest)
        self.assertGreater(len(manifest["files"]), 0)
        for f in manifest["files"]:
            self.assertIn("sha256", f)
            self.assertIn("bytes", f)

        mod.validate_local_manifest_files(manifest, self.sink_dir)

        first_data = manifest["files"][0]["object"]
        p = self.sink_dir / first_data
        p.write_bytes(p.read_bytes() + b"x")
        with self.assertRaises(RuntimeError):
            mod.validate_local_manifest_files(manifest, self.sink_dir)

        self.assertEqual(res["sink_write_order"][-1], f"pg/v1/run=hashrun/_manifest.json")

    def test_09_removed_fixture_literals_from_scan_patterns(self):
        names = [name for name, _ in mod.SCAN_PATTERNS]
        self.assertNotIn("fake_literal", names)
        self.assertNotIn("customer_secret_literal", names)
        self.assertNotIn("other_supplier_literal", names)
        self.assertNotIn("supplier_host_literal", names)

    def test_10_config_matches_grants_all_14_tables(self):
        cfg = self._all_tables_config()
        with psycopg.connect(self.uri) as conn:
            with conn.cursor() as cur:
                cur.execute("SET ROLE odyn_ingest_ro")
            for t in cfg.tables:
                cols, _types = mod.assert_config_matches_grants(conn, t)
                self.assertEqual(set(cols), set(t["columns"]))

    def test_11_sslmode_require_fails_and_prefer_logs_false(self):
        cfg = self._all_tables_config()
        cfg.sslmode = "require"
        stderr = io.StringIO()
        with self.assertRaises(RuntimeError):
            with contextlib.redirect_stderr(stderr):
                self._run(cfg=cfg)

        cfg2 = self._all_tables_config()
        stderr2 = io.StringIO()
        with contextlib.redirect_stderr(stderr2):
            self._run(cfg=cfg2)
        err = stderr2.getvalue()
        self.assertIn("INFO effective_sslmode=prefer", err)
        self.assertIn("connection_encrypted=false", err)

    def test_12_output_contains_masked_url_and_json_lines(self):
        res = self._run(run_id="outcheck")
        manifest = json.loads(self._manifest_path("outcheck").read_text(encoding="utf-8"))
        file_blob = ""
        for item in manifest["files"]:
            p = self.sink_dir / item["object"]
            if p.suffix == ".gz":
                file_blob += gzip.open(p, "rt", encoding="utf-8", errors="ignore").read()
            else:
                file_blob += p.read_text(encoding="utf-8", errors="ignore")
        self.assertNotIn("X-Amz-Signature=abc", file_blob)
        self.assertIn("[REDACTED]", file_blob)
        self.assertEqual(res["status"], "ok")

    def test_13_print_granted_config_skeleton_contains_all_tables(self):
        cfg = self._all_tables_config()
        with psycopg.connect(self.uri) as conn:
            with conn.cursor() as cur:
                cur.execute("SET ROLE odyn_ingest_ro")
            skeleton = mod.build_granted_config_skeleton(conn, cfg)
        self.assertEqual(len(skeleton["tables"]), 14)
        names = {f"{t['schema']}.{t['table']}" for t in skeleton["tables"]}
        self.assertIn("public.ingest_job_placement_v1", names)
        self.assertIn("public.job_cost_summary", names)

    def test_14_empty_and_whitespace_hmac_inputs_emit_empty_string(self):
        # SpyKMS rejects empty Message. Run must still succeed with '' and whitespace-only values.
        res = self._run(run_id="emptyhmac")
        self.assertEqual(res["status"], "ok")

        records = self._all_records_from_manifest("emptyhmac")
        self.assertGreater(len(records), 0)

        def rows(table_name: str) -> list[dict]:
            return [r for r in records if r.get("table_name") == table_name and not r.get("is_deleted")]

        # ray_train_jobs: owner_user_id + dataset_s3_key include empty/whitespace/null/normal
        rtj_rows = rows("public.ray_train_jobs")
        self.assertTrue(any(r["row_json"].get("owner_user_id") == "" for r in rtj_rows))
        self.assertTrue(any(r["row_json"].get("dataset_s3_key") == "" for r in rtj_rows))
        self.assertTrue(any(r["row_json"].get("owner_user_id") is None for r in rtj_rows))

        swr_rows = rows("public.scheduler_workload_requests")
        self.assertTrue(any(r["row_json"].get("user_id") == "" for r in swr_rows))
        self.assertTrue(any(r["row_json"].get("user_id") is None for r in swr_rows))

        jcs_rows = rows("public.job_cost_summary")
        self.assertTrue(any(r["row_json"].get("tenant_id") == "" for r in jcs_rows))
        self.assertTrue(any(r["row_json"].get("tenant_id") is None for r in jcs_rows))

        ijp_rows = rows("public.ingest_job_placement_v1")
        self.assertTrue(any(r["row_json"].get("job_id") == "" for r in ijp_rows))
        self.assertTrue(any(r["row_json"].get("gpu_reservation_id") == "" for r in ijp_rows))
        self.assertTrue(any(r["row_json"].get("job_id") is None for r in ijp_rows))
        self.assertTrue(any(r["row_json"].get("gpu_reservation_id") is None for r in ijp_rows))

    def test_15_transform_errors_include_table_field_rowpk_not_value(self):
        class ExplodingKMS(SpyKMS):
            def generate_mac(self, KeyId, Message, MacAlgorithm):  # noqa: N803
                raise RuntimeError("kms explode")

        self.kms = ExplodingKMS()
        with self.assertRaises(RuntimeError) as ctx:
            self._run(run_id="ctxfail")
        msg = str(ctx.exception)
        self.assertIn("transform error table=public.ray_train_jobs", msg)
        self.assertIn("field=owner_user_id", msg)
        self.assertIn("row_pk=", msg)
        self.assertNotIn("owner-normal", msg)

    def test_16_dry_run_finding_line_identifies_ingest_column_pattern(self):
        # non-aborting finding in ingest view via dropped array element
        self._db_exec(
            "UPDATE public.ingest_job_placement_fixture_src SET gpu_identifiers=%s::jsonb WHERE row_id=%s",
            ('["GPU-123e4567-e89b-12d3-a456-426614174000", 5]', "ijp-normal"),
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            res = self._run(run_id="dryingest", dry_run=True)

        out = stdout.getvalue()
        self.assertIn("TABLE public.ingest_job_placement_v1", out)
        self.assertIn("FREE_TEXT_FIELDS: <none>", out)
        self.assertIn("STRUCTURED_FIELDS: 9", out)
        self.assertIn("FINDING table=public.ingest_job_placement_v1 field=gpu_identifiers pattern=gpu_identifiers_element", out)
        self.assertIn("\"gpu_identifiers\":1", out)  # DROPPED_ARRAY_ELEMENTS evidence
        self.assertIn("findings", res)
        self.assertTrue(any(f.get("table") == "public.ingest_job_placement_v1" and f.get("pattern") == "gpu_identifiers_element" for f in res["findings"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
