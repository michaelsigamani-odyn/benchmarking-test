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
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg import errors
from pgserver import get_server


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pg_state_extractor_v0.py"
spec = importlib.util.spec_from_file_location("pg_state_extractor_v0", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules["pg_state_extractor_v0"] = mod
spec.loader.exec_module(mod)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SQL = REPO_ROOT / "tests" / "fixtures" / "extractor_fixture.sql"
GRANTS_SQL = REPO_ROOT / "scripts" / "db" / "pg_ingest_role.sql"
GENERATED_COLUMNS = REPO_ROOT / "scripts" / "db" / "pg_ingest_columns.generated.json"
TMP_ROOT = Path("/private/var/folders/gr/smmqbxt15ns1fjd5_9rhhd0m0000gn/T/opencode")


class FakeKMS:
    def __init__(self):
        self.messages = []

    def generate_mac(self, KeyId, Message, MacAlgorithm):  # noqa: N803
        assert KeyId
        assert MacAlgorithm == "HMAC_SHA_256"
        text = Message.decode("utf-8")
        self.messages.append(text)
        return {"Mac": hashlib.sha256(Message).digest()}


class ExtractorRealPostgresFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pgdata = Path(tempfile.mkdtemp(prefix="pgserver-", dir=str(TMP_ROOT)))
        cls.server = get_server(cls.pgdata, cleanup_mode="delete")
        cls.uri = cls.server.get_uri("postgres")

    @classmethod
    def tearDownClass(cls):
        with contextlib.suppress(Exception):
            cls.server.cleanup()
        with contextlib.suppress(Exception):
            shutil.rmtree(cls.pgdata, ignore_errors=True)

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="extractor-tests-", dir=str(TMP_ROOT)))
        self.sink_dir = self.tmpdir / "sink"
        self.state_dir = self.tmpdir / "state"
        self.kms = FakeKMS()
        self._reset_db()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _reset_db(self):
        self.server.psql(FIXTURE_SQL.read_text(encoding="utf-8"))
        self.server.psql(GRANTS_SQL.read_text(encoding="utf-8"))

    def _config(self):
        all_tables = json.loads(GENERATED_COLUMNS.read_text(encoding="utf-8"))["tables"]
        ingest = next(t for t in all_tables if t["table"] == "ingest_job_placement_v1")
        cols = ingest["columns"]
        return mod.ExtractorConfig(
            pg_dsn_env="UNUSED",
            pg_database="postgres",
            sslmode="prefer",
            sslmode_explicit=True,
            pg_password_secret_name="odyn/ingest-ro-db",
            pg_password_secret_region="us-west-2",
            gcs_bucket="unused",
            gcs_prefix="pg",
            kms_hmac_key_arn="arn:aws:kms:eu-west-1:123456789012:key/fixture",
            hmac_key_version="kms-hmac-v1",
            tables=[
                {
                    "schema": "public",
                    "table": "ingest_job_placement_v1",
                    "cadence": "change_only",
                    "columns": cols,
                    "pk_columns": ["job_id"],
                    "hmac_fields": ["job_id", "gpu_reservation_id"],
                    "json_allowlists": {
                        "accepted_recommendation_json": True,
                        "response_json": True,
                    },
                }
            ],
        )

    def _run(self, *, limit=100, run_id=None, dry_run=False):
        cfg = self._config()
        sink = mod.LocalDirectorySink(self.sink_dir)
        state = mod.JsonStateStore(self.state_dir)
        with psycopg.connect(self.uri) as conn:
            with conn.cursor() as cur:
                cur.execute("SET ROLE odyn_ingest_ro")
            result = mod.run(
                cfg,
                since=None,
                limit_per_table=limit,
                kms_client=self.kms,
                sink=sink,
                state_store=state,
                conn=conn,
                ingest_run_id=run_id,
                dry_run=dry_run,
            )
        return result

    def _read_run_outputs(self, run_id):
        base = self.sink_dir / f"pg/v1/table=public.ingest_job_placement_v1"
        run_dir = list(base.glob(f"dt=*/run={run_id}"))[0]
        data_file = run_dir / "part-0000.jsonl.gz"
        manifest_file = run_dir / "_manifest.json"
        with gzip.open(data_file, "rt", encoding="utf-8") as fp:
            lines = [json.loads(x) for x in fp if x.strip()]
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        return run_dir, data_file, manifest_file, lines, manifest

    def _db_exec(self, sql, params=None):
        with psycopg.connect(self.uri) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
            conn.commit()

    # 1) numeric exact string + captured_at UTC conversion with microseconds.
    def test_01_numeric_exact_string_and_utc_microseconds(self):
        res = self._run()
        _, _, _, lines, _ = self._read_run_outputs(res["ingest_run_id"])
        self.assertEqual(len(lines), 1)
        row_json = lines[0]["row_json"]
        self.assertEqual(row_json["price_book_hourly_rate_usd"], "1.2500000000")
        self.assertRegex(lines[0]["captured_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")

    # 2) scanner ignores token-like column names.
    def test_02_token_named_columns_are_allowed(self):
        self.assertEqual(mod.scan_text_patterns("num_input_tokens_seen dataset_train_token_count context_length_tokens"), [])
        res = self._run()
        _, _, _, lines, _ = self._read_run_outputs(res["ingest_run_id"])
        self.assertEqual(lines[0]["row_json"]["lifecycle_attempt"], "3")

    # 3) structured poison aborts.
    def test_03_structured_poison_aborts_run(self):
        self._db_exec(
            "UPDATE public.ingest_job_placement_fixture_src SET gpu_model_class=%s",
            ("arn:aws:iam::000000000000:role/bad",),
        )
        with self.assertRaises(RuntimeError):
            self._run()

    # 4) finding present, finding has no matched text.
    def test_04_free_text_mask_and_finding_without_secret(self):
        self._db_exec(
            "UPDATE public.ingest_job_placement_fixture_src SET gpu_identifiers=%s::jsonb",
            ('["GPU-123e4567-e89b-12d3-a456-426614174000", 5]',),
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            res = self._run()
        _, _, _, lines, manifest = self._read_run_outputs(res["ingest_run_id"])
        self.assertIn("ALERT run_id=", stderr.getvalue())
        findings_blob = json.dumps(manifest["findings"])
        self.assertIn("gpu_identifiers_element", findings_blob)
        self.assertNotIn("GPU-123e4567-e89b-12d3-a456-426614174000", findings_blob)
        sample_finding = manifest["findings"][0]
        self.assertEqual(set(sample_finding.keys()), {"table", "row_pk", "field", "pattern"})
        self.assertEqual(manifest["findings_count"], len(manifest["findings"]))
        self.assertEqual(mod.exit_code_for_result(res), mod.EXIT_ALERT)

    # 5) strict grants/privileges behavior.
    def test_05_config_equals_grants_and_privilege_checks(self):
        cfg = self._config()
        bad_cfg = dict(cfg.tables[0])
        bad_cfg["columns"] = bad_cfg["columns"][:-1]
        bad_cfg_extra = dict(cfg.tables[0])
        bad_cfg_extra["columns"] = list(bad_cfg_extra["columns"]) + ["not_granted_internal_note"]
        with psycopg.connect(self.uri) as conn:
            with conn.cursor() as cur:
                cur.execute("SET ROLE odyn_ingest_ro")
            with self.assertRaises(RuntimeError):
                mod.assert_config_matches_grants(conn, bad_cfg)
            with self.assertRaises(RuntimeError):
                mod.assert_config_matches_grants(conn, bad_cfg_extra)

            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM public.ingest_job_placement_v1")
                self.assertEqual(cur.fetchone()[0], 1)
                with self.assertRaises(errors.InsufficientPrivilege):
                    cur.execute("SELECT not_granted_internal_note FROM public.ingest_job_placement_fixture_src")

    # 6) sanitize before HMAC + id normalization + empty string stable.
    def test_06_hmac_input_ordering_and_normalization(self):
        self._db_exec(
            "UPDATE public.ingest_job_placement_fixture_src SET gpu_reservation_id=%s",
            ("  https://X.example/path?q=1#f  ",),
        )
        self.assertEqual(mod.normalize_hmac_input("job_id", "  ABC-123  "), "abc-123")
        self.assertEqual(mod.normalize_hmac_input("job_id", ""), "")
        self._run()
        self.assertIn("https://x.example/path", self.kms.messages)

    # 7) repeatable read and row-limit guard.
    def test_07_repeatable_read_and_limit_guard(self):
        called = {"n": 0}
        original = mod.begin_readonly_repeatable_read

        def wrapped(conn):
            called["n"] += 1
            return original(conn)

        mod.begin_readonly_repeatable_read = wrapped
        try:
            with self.assertRaises(RuntimeError):
                self._run(limit=0)
            self.assertEqual(called["n"], 1)
        finally:
            mod.begin_readonly_repeatable_read = original

        ok = self._run()
        self.assertEqual(ok["transaction"]["transaction_isolation"], "repeatable read")
        self.assertEqual(ok["transaction"]["transaction_read_only"], "on")

    # 8) element-shape filters + sanitization-only.
    def test_08_json_allowlists_and_sanitization_only(self):
        res = self._run()
        _, _, _, lines, manifest = self._read_run_outputs(res["ingest_run_id"])
        row_json = lines[0]["row_json"]
        self.assertEqual(row_json["gpu_identifiers"], ["GPU-123e4567-e89b-12d3-a456-426614174000", "123e4567-e89b-12d3-a456-426614174001"])
        self.assertEqual(row_json["node_ids"], ["node-a"])
        self.assertEqual(set(row_json.keys()) & {"classification", "trust_level", "mapped_provider"}, set())
        self.assertEqual(manifest["tables"][0]["dropped_keys"], {})
        self.assertEqual(manifest["tables"][0]["dropped_array_elements"], {})

    # 9) row_json contains only view columns.
    def test_09_view_columns_only(self):
        res = self._run()
        _, _, _, lines, _ = self._read_run_outputs(res["ingest_run_id"])
        row_json = lines[0]["row_json"]
        self.assertEqual(
            set(row_json.keys()),
            {
                "job_id",
                "gpu_identifiers",
                "node_ids",
                "gpu_reservation_id",
                "gpu_model_class",
                "min_gpu_vram_gb",
                "num_workers",
                "price_book_hourly_rate_usd",
                "lifecycle_attempt",
            },
        )

    # 10) re-run no changes emits zero rows.
    def test_10_rerun_with_no_changes_emits_zero_rows(self):
        first = self._run()
        second = self._run()
        _, _, _, lines2, manifest2 = self._read_run_outputs(second["ingest_run_id"])
        self.assertEqual(len(lines2), 0)
        self.assertEqual(manifest2["tables"][0]["emitted_row_count"], 0)
        self.assertNotEqual(first["ingest_run_id"], second["ingest_run_id"])

    # 11) mutation: 1 changed, 1 tombstone, 1 new.
    def test_11_mutation_emits_changed_tombstone_new(self):
        self._db_exec(
            """
            INSERT INTO public.ingest_job_placement_fixture_src (
              job_id,gpu_identifiers,node_ids,gpu_reservation_id,gpu_model_class,min_gpu_vram_gb,
              num_workers,price_book_hourly_rate_usd,lifecycle_attempt,created_at,observed_at,
              error_message,error_summary,failure_reason,accepted_recommendation_json,response_json,
              num_input_tokens_seen,dataset_train_token_count,context_length_tokens,nullable_note,unicode_note,not_granted_internal_note
            ) VALUES (
              %s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s
            )
            """,
            (
                "660e8400-e29b-41d4-a716-446655440000",
                '["GPU-9"]',
                '["node-z"]',
                "https://x.example/r",
                "l40",
                48,
                1,
                Decimal("0.7500000000"),
                1,
                "2026-10-11 05:11:00.123456+00",
                "2026-10-11 05:11:00.123456+00",
                "ok",
                "ok",
                "ok",
                '{"candidate_id":"c2"}',
                '{"status":"ok"}',
                1,
                2,
                3,
                None,
                "µ",
                "hidden",
            ),
        )
        self._run()  # baseline state with 2 rows

        self._db_exec(
            "UPDATE public.ingest_job_placement_fixture_src SET gpu_model_class=%s WHERE job_id=%s::uuid",
            ("h100", "550e8400-e29b-41d4-a716-446655440000"),
        )
        self._db_exec(
            "DELETE FROM public.ingest_job_placement_fixture_src WHERE job_id=%s::uuid",
            ("660e8400-e29b-41d4-a716-446655440000",),
        )
        self._db_exec(
            """
            INSERT INTO public.ingest_job_placement_fixture_src (
              job_id,gpu_identifiers,node_ids,gpu_reservation_id,gpu_model_class,min_gpu_vram_gb,
              num_workers,price_book_hourly_rate_usd,lifecycle_attempt,created_at,observed_at,
              error_message,error_summary,failure_reason,accepted_recommendation_json,response_json,
              num_input_tokens_seen,dataset_train_token_count,context_length_tokens,nullable_note,unicode_note,not_granted_internal_note
            ) VALUES (
              %s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s
            )
            """,
            (
                "770e8400-e29b-41d4-a716-446655440000",
                '["GPU-new"]',
                '["node-new"]',
                "https://new.example/r",
                "h200",
                80,
                4,
                Decimal("2.2500000000"),
                1,
                "2026-10-11 05:12:00.123456+00",
                "2026-10-11 05:12:00.123456+00",
                "ok",
                "ok",
                "ok",
                '{"candidate_id":"c3"}',
                '{"status":"ok"}',
                9,
                8,
                7,
                None,
                "µ2",
                "hidden",
            ),
        )

        res = self._run()
        _, _, _, lines, manifest = self._read_run_outputs(res["ingest_run_id"])
        self.assertEqual(len(lines), 3)
        deletes = [x for x in lines if x["is_deleted"]]
        live = [x for x in lines if not x["is_deleted"]]
        self.assertEqual(len(deletes), 1)
        self.assertEqual(len(live), 2)
        self.assertEqual(manifest["tables"][0]["emitted_row_count"], 3)

    # 12) layout/manifest-last and loader-side missing-file check.
    def test_12_layout_manifest_last_and_loader_missing_file_failure(self):
        res = self._run()
        run_dir, data_file, manifest_file, _, manifest = self._read_run_outputs(res["ingest_run_id"])
        self.assertIn("/v1/table=public.ingest_job_placement_v1/", str(data_file))
        self.assertTrue(res["sink_write_order"][-1].endswith("/_manifest.json"))
        mod.validate_local_manifest_files(manifest, self.sink_dir)
        data_file.unlink()
        with self.assertRaises(RuntimeError):
            mod.validate_local_manifest_files(manifest, self.sink_dir)

        # canary writes only one tiny object and no table data.
        canary_sink = mod.LocalDirectorySink(self.tmpdir / "canary_sink")
        canary = mod.run_canary(self._config(), sink=canary_sink, run_id="canary_test")
        self.assertEqual(canary["object"], "_canary/canary_test.json")
        self.assertEqual(canary_sink.write_order, ["_canary/canary_test.json"])

    # 13) same-run-id overwrite fails + 4KB truncation marker helper.
    def test_13_same_run_overwrite_fails_and_4kb_marker(self):
        huge = "Z" * 7000
        truncated = mod.truncate_utf8_with_marker(huge)
        self.assertTrue(truncated.endswith(mod.TRUNCATION_MARKER))
        self.assertLessEqual(len(truncated.encode("utf-8")), mod.MAX_TEXT_BYTES)

        fixed = "extractor_v0_fixed_run_for_test"
        first = self._run(run_id=fixed)
        self.assertEqual(first["ingest_run_id"], fixed)
        with self.assertRaises(FileExistsError):
            self._run(run_id=fixed)

        # dry-run prints per-table summary and does not write sink files.
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            dry = self._run(run_id="dry_run_case", dry_run=True)
        self.assertEqual(dry["status"], "ok")
        out = stdout.getvalue()
        self.assertIn("TABLE public.ingest_job_placement_v1", out)
        self.assertIn("COLUMNS:", out)
        self.assertIn("SOURCE_COUNT:", out)
        self.assertIn("SAMPLE_REDACTED_ROW:", out)
        self.assertIn("FINDINGS_COUNT:", out)
        self.assertIn("DROPPED_KEYS:", out)
        self.assertIn("DROPPED_ARRAY_ELEMENTS:", out)

    # 14) poison absence in output + stdout/stderr.
    def test_14_no_poison_in_output_or_stdio(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            res = self._run()

        out_blob = stdout.getvalue() + "\n" + stderr.getvalue()
        run_dir, _, _, _, _ = self._read_run_outputs(res["ingest_run_id"])
        file_blob = ""
        for p in run_dir.glob("*"):
            if p.suffix == ".gz":
                file_blob += gzip.open(p, "rt", encoding="utf-8", errors="ignore").read()
            else:
                file_blob += p.read_text(encoding="utf-8", errors="ignore")

        poison_values = [
            "FAKEFAKEFAKE",
            "hf_FAKE",
            "@example.invalid",
            "10.1.2.3",
            "ip-10-1-2-3.ec2.internal",
            "arn:aws:iam::000000000000",
            "BEGIN PRIVATE KEY",
            "X-Amz-Signature",
            "X-Amz-Credential",
            "CUSTOMER SECRET",
            "other-supplier",
            "10.9.9.9",
            "supplier-host-1",
        ]
        for marker in poison_values:
            self.assertNotIn(marker, file_blob)
            self.assertNotIn(marker, out_blob)

    # 15) sslmode=require must fail against TLS-off local server.
    def test_15_sslmode_require_fails_when_unencrypted(self):
        cfg = self._config()
        cfg.sslmode = "require"
        cfg.sslmode_explicit = True
        sink = mod.LocalDirectorySink(self.sink_dir)
        state = mod.JsonStateStore(self.state_dir)
        with psycopg.connect(self.uri) as conn:
            with conn.cursor() as cur:
                cur.execute("SET ROLE odyn_ingest_ro")
            with self.assertRaises(RuntimeError):
                mod.run(
                    cfg,
                    since=None,
                    limit_per_table=100,
                    kms_client=self.kms,
                    sink=sink,
                    state_store=state,
                    conn=conn,
                )

    # 16) sslmode=prefer logs connection_encrypted=false.
    def test_16_sslmode_prefer_logs_unencrypted_status(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self._run()
        err = stderr.getvalue()
        self.assertIn("INFO effective_sslmode=prefer", err)
        self.assertIn("connection_encrypted=false", err)

    # 17) unchanged finding does not re-alert.
    def test_17_unchanged_finding_not_realerted(self):
        self._db_exec(
            "UPDATE public.ingest_job_placement_fixture_src SET gpu_identifiers=%s::jsonb",
            ('["GPU-123e4567-e89b-12d3-a456-426614174000", 5]',),
        )
        first_err = io.StringIO()
        with contextlib.redirect_stderr(first_err):
            first = self._run()
        self.assertTrue(first["alert"])
        self.assertGreater(first["findings_count"], 0)
        self.assertIn("ALERT run_id=", first_err.getvalue())

        second_err = io.StringIO()
        with contextlib.redirect_stderr(second_err):
            second = self._run()
        self.assertFalse(second["alert"])
        self.assertEqual(second["findings_count"], 0)
        self.assertNotIn("ALERT run_id=", second_err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
