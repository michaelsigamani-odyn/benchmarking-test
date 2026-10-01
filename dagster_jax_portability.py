"""Dagster definitions for the JAX cross-vendor portability experiment.

Asset graph:   jax_reference_run -> jax_noise_floor
               jax_relay_<name> (one per relay in the plan)
               jax_portability_report  (depends on all of the above)   + 2 asset checks

Every stage persists its leg summaries under <run_dir>/_summaries/*.json; the report is rebuilt
from those files, so the verdict is auditable outside Dagster. Config is env-driven:
  JAXFT_PLAN (default experiments/local_dryrun_plan.json), JAXFT_RUN_DIR, JAXFT_TRANSPORT=local|ssh
There are no passwords anywhere; ssh uses keys (BatchMode).
"""
import json
import os

import dagster as dg

import harness
from jaxft.device_transfer import validate_transfer_roundtrip

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN_PATH = os.path.abspath(os.environ.get("JAXFT_PLAN", os.path.join(HERE, "experiments", "local_dryrun_plan.json")))
RUN_DIR = os.path.abspath(os.environ.get("JAXFT_RUN_DIR", os.path.join(HERE, "runs", "latest")))
TRANSPORT = os.environ.get("JAXFT_TRANSPORT", "local")
PLAN = json.load(open(PLAN_PATH))
GROUP = "jax_portability"


def _tp():
    if TRANSPORT == "ssh":
        return harness.SshTransport(PLAN["hosts"], staging=os.path.join(RUN_DIR, "_staging"))
    return harness.LocalTransport({k: v["root"] for k, v in PLAN["hosts"].items()}, code_dir=HERE)


def _leg_meta(leg):
    return {"vendor": leg["env"]["vendor"], "device_kind": leg["env"]["device_kind"], "jax": leg["env"]["jax"],
            "jaxlib": leg["env"]["jaxlib"], "steps": f"{leg['start_step']+1}-{leg['end_step']}",
            "final_digest": leg["final_digest"], "seconds": leg["seconds"]}


@dg.asset(group_name=GROUP, description="Validates explicit JAX host<->accelerator data transfer using device_put/device_get.")
def jax_data_transfer_validation(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    transfer = validate_transfer_roundtrip()
    transfer_ok = transfer["roundtrip_ok"] and transfer["sum_ok"] and transfer["speed_ok"]
    if not transfer_ok:
        raise dg.Failure(description="JAX transfer validation failed", metadata=transfer)
    return dg.MaterializeResult(metadata={**transfer, "transfer_ok": transfer_ok})


@dg.asset(group_name=GROUP, description="Uninterrupted run 0->N on the reference host: the paired baseline.")
def jax_reference_run(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    ref = harness.run_reference(_tp(), PLAN, RUN_DIR)
    return dg.MaterializeResult(metadata=_leg_meta(ref))


@dg.asset(group_name=GROUP, deps=[jax_reference_run],
          description="Divergence caused by an ulp-scale init perturbation on one platform: the empirical drift floor.")
def jax_noise_floor(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    floor = harness.run_noise(_tp(), PLAN, RUN_DIR, harness._load(RUN_DIR, "reference"))
    return dg.MaterializeResult(metadata=floor or {"note": "no noise_floor section in plan"})


def _relay_asset(relay):
    @dg.asset(name=f"jax_relay_{relay['name']}", group_name=GROUP,
              description=f"Relay {' -> '.join(relay['hosts'])} with checkpoint hand-offs between legs.")
    def _a(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
        legs = harness.run_named_relay(_tp(), PLAN, relay["name"], RUN_DIR)
        return dg.MaterializeResult(metadata={f"leg{i+1}": dg.MetadataValue.json(_leg_meta(l)) for i, l in enumerate(legs)})
    return _a


relay_assets = [_relay_asset(r) for r in PLAN["relays"]]


@dg.asset(group_name=GROUP, deps=[jax_data_transfer_validation, jax_reference_run, jax_noise_floor, *relay_assets],
          description="Validation report: state transfer, resume semantics, numerical drift, scoped verdict.")
def jax_portability_report(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    rep = harness.build_report_from_disk(PLAN, RUN_DIR)
    return dg.MaterializeResult(metadata={
        "verdict": rep["verdict"]["status"], "vendors_seen": dg.MetadataValue.json(rep["verdict"]["vendors_seen"]),
        "failed_checks": dg.MetadataValue.json(rep["verdict"]["failed_checks"]),
        "noise_floor": dg.MetadataValue.json(rep["noise_floor"]), "n_checks": len(rep["checks"]),
        "report_path": dg.MetadataValue.path(os.path.join(RUN_DIR, "report.json"))})


def _report():
    with open(os.path.join(RUN_DIR, "report.json")) as f:
        return json.load(f)


@dg.asset_check(asset=jax_portability_report, description="Every required state-transfer / resume / drift check passed.")
def all_required_checks_pass() -> dg.AssetCheckResult:
    v = _report()["verdict"]
    return dg.AssetCheckResult(passed=not v["failed_checks"], metadata={"failed": dg.MetadataValue.json(v["failed_checks"])})


@dg.asset_check(asset=jax_portability_report,
                description="Two different real GPU vendors participated. WARN (not error) when only mechanics were shown.")
def cross_vendor_claim_supported() -> dg.AssetCheckResult:
    v = _report()["verdict"]
    return dg.AssetCheckResult(passed=v["status"].startswith("CROSS_VENDOR_DEMONSTRATED"),
                               severity=dg.AssetCheckSeverity.WARN,
                               metadata={"status": v["status"], "vendors_seen": dg.MetadataValue.json(v["vendors_seen"])})


@dg.asset_check(asset=jax_data_transfer_validation,
                description="JAX data transfer roundtrip remains explicit and correct.")
def jax_data_transfer_check() -> dg.AssetCheckResult:
    transfer = validate_transfer_roundtrip()
    transfer_ok = transfer["roundtrip_ok"] and transfer["sum_ok"] and transfer["speed_ok"]
    return dg.AssetCheckResult(passed=transfer_ok, metadata=transfer)


defs = dg.Definitions(assets=[jax_data_transfer_validation, jax_reference_run, jax_noise_floor, *relay_assets, jax_portability_report],
                      asset_checks=[jax_data_transfer_check, all_required_checks_pass, cross_vendor_claim_supported])

if __name__ == "__main__":
    result = dg.materialize([jax_data_transfer_validation, jax_reference_run, jax_noise_floor, *relay_assets, jax_portability_report])
    raise SystemExit(0 if result.success else 1)
