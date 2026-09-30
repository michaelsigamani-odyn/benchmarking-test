import copy
import json
import os
import shutil
import sys

import jax
import jax.numpy as jnp
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from jaxft import ckpt as ck                                   # noqa: E402
from jaxft import data as D                                    # noqa: E402
from jaxft import hf_io, validate as V                         # noqa: E402
from jaxft.env import classify_vendor                          # noqa: E402
from jaxft.model import TINY, LoraConfig, forward, init_base_random, init_lora, masked_ce_loss  # noqa: E402
from jaxft.train import IdentityMismatch, TrainConfig, run_leg  # noqa: E402

CFG = os.path.join(ROOT, "experiments", "smoke_config.json")


@pytest.fixture()
def cfg(tmp_path):
    c = TrainConfig.from_json(CFG)
    c.data_path = os.path.join(ROOT, c.data_path)
    return c


def quiet(_):
    pass


# ----------------------------------------------------------------------------- model
def test_causality_and_lora_identity():
    l = LoraConfig()
    base = init_base_random(jax.random.key(0), TINY)
    lora = init_lora(jax.random.key(1), TINY, l)
    t = jax.random.randint(jax.random.key(2), (2, 16), 0, TINY.vocab_size)
    h = forward(base, lora, t, TINY, l)
    h2 = forward(base, lora, t.at[:, -1].set((t[:, -1] + 1) % TINY.vocab_size), TINY, l)
    assert jnp.array_equal(h[:, :-1], h2[:, :-1])                       # future tokens cannot leak
    assert jnp.array_equal(h, forward(base, {}, t, TINY, LoraConfig(targets=())))  # B=0 => identity


def test_hf_safetensors_roundtrip(tmp_path):
    base = init_base_random(jax.random.key(0), TINY)
    hf_io.write_safetensors(str(tmp_path / "m.safetensors"), hf_io.params_to_hf(base, TINY))
    back = hf_io.hf_to_params(hf_io.read_hf_dir(str(tmp_path)), TINY)
    assert jax.tree.structure(back) == jax.tree.structure(base)
    for a, b in zip(jax.tree.leaves(base), jax.tree.leaves(back)):
        assert np.asarray(a).dtype == np.asarray(b).dtype and np.array_equal(np.asarray(a), np.asarray(b))


# ----------------------------------------------------------------------------- data
def test_batches_are_pure_function_of_seed_and_step():
    a = D.batch_indices(64, 4, 17, 5)
    assert np.array_equal(a, D.batch_indices(64, 4, 17, 5))
    assert not np.array_equal(a, D.batch_indices(64, 4, 18, 5))
    seen = np.concatenate([D.batch_indices(64, 4, 17, s) for s in range(1, 17)])
    assert sorted(seen) == list(range(64))                              # exactly one pass per epoch


def test_empty_target_examples_are_dropped_not_scored_as_zero_loss():
    recs = [{"instruction": "x" * 300, "input": "", "output": "y"}, {"instruction": "hi", "input": "", "output": "there"}]
    arr = D.build_arrays(recs, D.ByteTokenizer(), 64)
    assert int(arr["n_dropped_empty"]) == 1 and arr["input_ids"].shape[0] == 1


# ----------------------------------------------------------------------------- resume semantics
def test_resume_is_bitwise_identical_to_uninterrupted(cfg, tmp_path):
    ref = run_leg(cfg, str(tmp_path / "ref"), 12, log=quiet)
    a = run_leg(cfg, str(tmp_path / "a"), 6, log=quiet)
    b = run_leg(cfg, str(tmp_path / "b"), 12, resume_from=a["ckpt_dir"], log=quiet)
    assert b["final_digest"] == ref["final_digest"]
    assert [t["loss"] for t in b["trace"]] == [t["loss"] for t in ref["trace"]]
    assert b["restore"]["roundtrip_exact"] and b["restore"]["manifest_ok"]
    assert all(t["loss"] > 0 for t in ref["trace"])                     # no fake 0.0 losses


def test_resume_refuses_changed_schedule_horizon(cfg, tmp_path):
    """The PyTorch harness launched each leg with max_steps = leg end. Here that is refused outright."""
    a = run_leg(cfg, str(tmp_path / "a"), 6, log=quiet)
    cfg2 = copy.deepcopy(cfg); cfg2.total_steps = 6
    with pytest.raises(IdentityMismatch):
        run_leg(cfg2, str(tmp_path / "b"), 6, resume_from=a["ckpt_dir"], log=quiet)


def test_changed_seed_or_lr_is_refused(cfg, tmp_path):
    a = run_leg(cfg, str(tmp_path / "a"), 6, log=quiet)
    for field, val in (("seed", 99), ("lr", 1e-3)):
        c = copy.deepcopy(cfg); setattr(c, field, val)
        with pytest.raises(IdentityMismatch):
            run_leg(c, str(tmp_path / f"b_{field}"), 9, resume_from=a["ckpt_dir"], log=quiet)


# ----------------------------------------------------------------------------- the original's blind spots
def test_silent_cpu_fallback_is_a_hard_failure(cfg, tmp_path):
    """Original: the 'AMD' leg ran on CPU and still reported a pass. Here it cannot."""
    if jax.devices()[0].platform != "cpu":
        pytest.skip("this test needs a CPU-only runtime")
    with pytest.raises(RuntimeError, match="Refusing to continue"):
        run_leg(cfg, str(tmp_path / "x"), 3, require_vendor_="amd", log=quiet)


def test_norm_check_is_blind_to_corruption_that_the_digest_catches():
    """exp_avg_sq-norm equality (the original check) passes for a permuted second-moment; digest does not."""
    nu = jax.random.uniform(jax.random.key(0), (4, 32))
    permuted = nu.reshape(-1)[::-1].reshape(4, 32)
    assert abs(float(jnp.linalg.norm(nu)) - float(jnp.linalg.norm(permuted))) < 1e-4      # old check: passes
    d1, d2 = ck.state_digest({"nu": nu}), ck.state_digest({"nu": permuted})
    assert d1["overall"] != d2["overall"] and ck.diff_digests(d1, d2)["differing"] == ["['nu']"]


def test_file_corruption_is_detected(cfg, tmp_path):
    a = run_leg(cfg, str(tmp_path / "a"), 6, log=quiet)
    copy_dir = str(tmp_path / "copied")
    shutil.copytree(a["ckpt_dir"], copy_dir)
    victim = max((os.path.join(r, n) for r, _, ns in os.walk(os.path.join(copy_dir, "orbax")) for n in ns),
                 key=os.path.getsize)
    with open(victim, "r+b") as f:
        f.seek(0); byte = f.read(1); f.seek(0); f.write(bytes([byte[0] ^ 0xFF]))
    m = ck.verify_manifest(copy_dir)
    assert not m["ok"] and m["modified"]


# ----------------------------------------------------------------------------- verdict scoping
def _leg(vendor, kind="x", end=6, start=0, digest="d", ident="i", restore=None, trace=None):
    env = {"vendor": vendor, "device_kind": kind, "jax": "1", "jaxlib": "1", "xla_flags": "", "matmul_precision": "highest"}
    tr = trace or [{"step": s, "loss": 1.0, "source": "computed"} for s in range(start + 1, end + 1)]
    return {"env": env, "final_digest": digest, "identity_hash": ident, "start_step": start, "end_step": end,
            "trace": tr, "restore": restore or {"resumed": False}}


def test_verdict_never_claims_cross_vendor_from_cpu_legs():
    v = V.verdict([V.Check("c", True)], [_leg("cpu"), _leg("cpu")])
    assert v["status"] == "MECHANICS_OK_NO_CROSS_VENDOR_CLAIM"


def test_verdict_claims_cross_vendor_only_with_two_real_gpu_vendors():
    v = V.verdict([V.Check("c", True)], [_leg("nvidia"), _leg("amd")])
    assert v["status"].startswith("CROSS_VENDOR_DEMONSTRATED")
    assert V.verdict([V.Check("c", False)], [_leg("nvidia"), _leg("amd")])["status"] == "FAILED"


def test_mislabelled_vendor_fails_handoff_check():
    src = _leg("cpu", digest="s")                                        # 'amd' host that really ran on CPU
    trace = [{"step": s, "loss": 1.0, "source": "restored" if s <= 6 else "computed"} for s in range(1, 10)]
    dst = _leg("nvidia", start=6, end=9, digest="t", trace=trace, restore={
        "resumed": True, "manifest_ok": True, "saved_digest": "s", "restored_digest": "s", "roundtrip_exact": True,
        "restored_step": 6})
    checks = V.check_handoff(src, dst, 3, expect_src="amd", expect_dst="nvidia")
    bad = [c.name for c in checks if c.passed is False]
    assert bad == ["source_ran_on_expected_vendor"]


def test_classify_vendor():
    assert classify_vendor("gpu", "cuda 13000", "NVIDIA GB10")["vendor"] == "nvidia"
    assert classify_vendor("gpu", "rocm 7.1", "AMD Radeon Graphics")["vendor"] == "amd"
    assert classify_vendor("cpu", "", "cpu")["vendor"] == "cpu"


def test_same_platform_requires_bitwise_but_cross_platform_uses_noise_floor():
    ref = _leg("nvidia", "A100", end=4)
    same = copy.deepcopy(ref); same["trace"][2]["loss"] += 1e-9
    assert V.check_trajectory("t", same, ref, abs_tol=1.0).passed is False       # same platform: any bit flip fails
    other = copy.deepcopy(ref); other["env"]["vendor"] = "amd"; other["trace"][2]["loss"] += 1e-4
    floor = {"max_abs": 1e-4}
    assert V.check_trajectory("t", other, ref, abs_tol=0.0, floor=floor, floor_mult=3.0).passed is True
    other["trace"][2]["loss"] += 1e-2
    assert V.check_trajectory("t", other, ref, abs_tol=0.0, floor=floor, floor_mult=3.0).passed is False


# ----------------------------------------------------------------------------- end to end (CPU, local transport)
def test_full_local_relay_end_to_end(tmp_path):
    import harness
    plan = json.load(open(os.path.join(ROOT, "experiments", "local_dryrun_plan.json")))
    plan["train_config"] = CFG
    plan["hosts"] = {"nvidia": {"root": str(tmp_path / "A"), "vendor": "cpu"}, "amd": {"root": str(tmp_path / "B"), "vendor": "cpu"}}
    plan["noise_floor"]["runs"] = 1
    pp = tmp_path / "plan.json"; pp.write_text(json.dumps(plan))
    tp = harness.LocalTransport({k: v["root"] for k, v in plan["hosts"].items()}, code_dir=ROOT)
    rep = harness.run_experiment(str(pp), tp, str(tmp_path / "run"))
    assert rep["verdict"]["status"] == "MECHANICS_OK_NO_CROSS_VENDOR_CLAIM" and not rep["verdict"]["failed_checks"]
    assert {l[-1]["final_digest"] for l in rep["relays"].values()} == {rep["reference"]["final_digest"]}
