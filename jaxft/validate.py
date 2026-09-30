"""Validation of relay runs, written to separate *three different claims* that the PyTorch test blurred:

1. STATE TRANSFER   - the checkpoint arrived intact and restored to the identical state
                      (bitwise; file hashes + canonical array digests; no tolerance involved).
2. RESUME SEMANTICS - training continued from the right step with the same config/data/base and
                      the right history (contiguous steps, restored history == source history).
3. NUMERICAL DRIFT  - a *paired* comparison of computed losses against a reference trajectory on the
                      same batches. Same platform => must be bitwise equal. Different platform =>
                      floating-point kernels differ, so compare against a measured noise floor.

The verdict is scoped: nothing says "cross-vendor" unless two different real GPU vendors ran legs.
"""
from __future__ import annotations

import dataclasses
import math
from typing import Any, Dict, List, Optional


@dataclasses.dataclass
class Check:
    name: str
    passed: Optional[bool]          # None = informational only
    detail: Any = None
    required: bool = True

    def as_dict(self):
        return dataclasses.asdict(self)


def env_fingerprint(env: Dict[str, Any]) -> tuple:
    return (env["vendor"], env["device_kind"], env["jax"], env["jaxlib"], env["xla_flags"], env["matmul_precision"])


def paired_diff(leg_trace, ref_trace, only_computed: bool = True) -> Dict[str, Any]:
    ref = {r["step"]: r["loss"] for r in ref_trace}
    pairs = [(r["step"], r["loss"], ref[r["step"]]) for r in leg_trace
             if r["step"] in ref and (r.get("source") == "computed" or not only_computed)]
    if not pairs:
        return {"n": 0}
    d = [a - b for _, a, b in pairs]
    ad = [abs(x) for x in d]
    return {"n": len(pairs), "first_step": pairs[0][0], "last_step": pairs[-1][0],
            "max_abs": max(ad), "mean_abs": sum(ad) / len(ad), "rmse": math.sqrt(sum(x * x for x in d) / len(d)),
            "max_rel": max(abs(x) / max(abs(b), 1e-12) for x, (_, _, b) in zip(d, pairs)),
            "bitwise_equal": all(x == 0.0 for x in d),
            "per_step": [{"step": s, "diff": a - b} for s, a, b in pairs]}


def check_handoff(src: Dict[str, Any], dst: Dict[str, Any], min_extra_steps: int, expect_src: Optional[str],
                  expect_dst: Optional[str]) -> List[Check]:
    r, out = dst["restore"], []
    out.append(Check("resumed_flag", bool(r.get("resumed")), {"resume_from": r.get("resume_from")}))
    out.append(Check("file_integrity", bool(r.get("manifest_ok")), r.get("manifest")))
    out.append(Check("saved_digest_matches_source_final", r.get("saved_digest") == src["final_digest"],
                     {"source_final": src["final_digest"], "target_saved": r.get("saved_digest")}))
    out.append(Check("restore_roundtrip_bitwise", bool(r.get("roundtrip_exact")),
                     {"leaf_diff": r.get("leaf_diff")}))
    out.append(Check("identity_equal", dst["identity_hash"] == src["identity_hash"]))
    steps_new = [t["step"] for t in dst["trace"] if t["source"] == "computed"]
    steps_old = [t["step"] for t in dst["trace"] if t["source"] == "restored"]
    ok_steps = (dst["start_step"] == src["end_step"] == r.get("restored_step")
                and steps_new == list(range(src["end_step"] + 1, dst["end_step"] + 1))
                and steps_old == list(range(1, src["end_step"] + 1)))
    out.append(Check("step_handoff_contiguous", ok_steps,
                     {"src_end": src["end_step"], "dst_start": dst["start_step"], "restored_step": r.get("restored_step")}))
    out.append(Check("min_extra_steps", len(steps_new) >= min_extra_steps, {"extra": len(steps_new), "min": min_extra_steps}))
    src_hist = [(t["step"], t["loss"]) for t in src["trace"]]
    dst_hist = [(t["step"], t["loss"]) for t in dst["trace"] if t["source"] == "restored"]
    out.append(Check("restored_history_equals_source", src_hist == dst_hist))
    if expect_src:
        out.append(Check("source_ran_on_expected_vendor", src["env"]["vendor"] == expect_src,
                         {"expected": expect_src, "actual": src["env"]["vendor"], "device_kind": src["env"]["device_kind"]}))
    if expect_dst:
        out.append(Check("target_ran_on_expected_vendor", dst["env"]["vendor"] == expect_dst,
                         {"expected": expect_dst, "actual": dst["env"]["vendor"], "device_kind": dst["env"]["device_kind"]}))
    return out


def noise_floor(baseline_trace, perturbed_traces) -> Dict[str, Any]:
    """Divergence produced by an ulp-scale perturbation of the init on the SAME platform.
    Cross-vendor drift should be comparable to this if kernels differ only by rounding."""
    diffs = [paired_diff(t, baseline_trace, only_computed=False) for t in perturbed_traces]
    return {"n_runs": len(diffs), "max_abs": max(d["max_abs"] for d in diffs),
            "rmse": max(d["rmse"] for d in diffs)}


def check_trajectory(name: str, leg: Dict[str, Any], ref: Dict[str, Any], *, abs_tol: float,
                     floor: Optional[Dict[str, Any]] = None, floor_mult: float = 3.0) -> Check:
    d = paired_diff(leg["trace"], ref["trace"])
    if d["n"] == 0:
        return Check(name, False, "no overlapping computed steps")
    same = env_fingerprint(leg["env"]) == env_fingerprint(ref["env"])
    slim = {k: v for k, v in d.items() if k != "per_step"}
    if same:
        return Check(name, d["bitwise_equal"], dict(slim, mode="same-platform: must be bitwise equal"))
    if floor:
        tol = max(floor_mult * floor["max_abs"], 1e-6)
        return Check(name, d["max_abs"] <= tol, dict(slim, mode="cross-platform vs measured noise floor",
                                                     tolerance=tol, noise_floor=floor, mult=floor_mult))
    return Check(name, d["max_abs"] <= abs_tol,
                 dict(slim, mode="cross-platform, UNCALIBRATED absolute tolerance", tolerance=abs_tol,
                      warning="no noise floor measured; treat pass/fail as provisional"))


def verdict(checks: List[Check], legs: List[Dict[str, Any]]) -> Dict[str, Any]:
    failed = [c.name for c in checks if c.required and c.passed is False]
    vendors = sorted({l["env"]["vendor"] for l in legs})
    gpu_vendors = [v for v in vendors if v in ("nvidia", "amd")]
    uncal = any(isinstance(c.detail, dict) and "warning" in c.detail for c in checks)
    if failed:
        status = "FAILED"
    elif len(gpu_vendors) >= 2:
        status = "CROSS_VENDOR_DEMONSTRATED" + ("_TOLERANCE_UNCALIBRATED" if uncal else "")
    else:
        status = "MECHANICS_OK_NO_CROSS_VENDOR_CLAIM"
    return {"status": status, "failed_checks": failed, "vendors_seen": vendors,
            "scope": "single-device, short-horizon LoRA relay for this model/data/config only; "
                     "not evidence for multi-GPU, tensor-parallel, larger models or long horizons."}
