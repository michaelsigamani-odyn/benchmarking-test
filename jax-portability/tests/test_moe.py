import copy
import dataclasses
import json
import os
import sys

import jax
import jax.numpy as jnp
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from jaxft import hf_io, validate as V                                   # noqa: E402
from jaxft.model import (TINY, TINY_MOE, LoraConfig, ModelConfig, forward_with_aux, init_base_random,  # noqa: E402
                         init_lora, loss_and_aux, route, routing_probe, validate_targets, count_params)
from jaxft.train import IdentityMismatch, TrainConfig, run_leg           # noqa: E402

CFG = os.path.join(ROOT, "experiments", "moe_smoke_config.json")
F32 = dataclasses.replace(TINY_MOE, dtype="float32")
ALL_T = ("q", "v", "e_gate", "e_up", "e_down", "s_gate", "s_up", "s_down")


def quiet(_):
    pass


@pytest.fixture()
def cfg():
    c = TrainConfig.from_json(CFG)
    c.data_path = os.path.join(ROOT, c.data_path)
    return c


def _lora_nonzero(cfg_, lcfg):
    lora = init_lora(jax.random.key(1), cfg_, lcfg)
    for i, n in enumerate(sorted(lora)):
        lora[n]["b"] = 0.05 * jax.random.normal(jax.random.key(100 + i), lora[n]["b"].shape)  # make every adapter contribute
    return lora


# ----------------------------------------------------------------------------- dispatch correctness
def test_dropless_grouped_dispatch_matches_dense_oracle_forward_and_grad():
    l = LoraConfig(r=4, alpha=8, dropout=0.0, targets=ALL_T)
    base, lora = init_base_random(jax.random.key(0), F32), _lora_nonzero(F32, l)
    toks = jax.random.randint(jax.random.key(2), (2, 12), 0, F32.vocab_size)
    mask = jnp.ones((2, 12), bool)
    hr, _ = forward_with_aux(base, lora, toks, F32, l, moe_impl="ragged")
    hd, _ = forward_with_aux(base, lora, toks, F32, l, moe_impl="dense")
    assert float(jnp.abs(hr - hd).max()) < 1e-5
    g = lambda impl: jax.grad(lambda lo: loss_and_aux(base, lo, toks, mask, F32, l, moe_impl=impl, aux_coef=0.01)[0])(lora)
    gr, gd = g("ragged"), g("dense")
    scale = max(float(jnp.abs(x).max()) for x in jax.tree.leaves(gd))
    assert max(float(jnp.abs(a - b).max()) for a, b in zip(jax.tree.leaves(gr), jax.tree.leaves(gd))) < 1e-5 * max(scale, 1.0)
    assert all(float(jnp.abs(x).max()) > 0 for x in jax.tree.leaves(gr))         # every adapter (incl. every expert target) gets gradient


def test_routing_invariants_and_no_token_is_dropped():
    base = init_base_random(jax.random.key(0), F32)
    x = jax.random.normal(jax.random.key(3), (200, F32.hidden))
    _, probs, idx, w = route(x, base["layers"]["router_w"][0], F32)
    idx = np.asarray(idx)
    assert idx.shape == (200, F32.top_k) and (np.diff(np.sort(idx, axis=-1), axis=-1) > 0).all()   # K distinct experts per token
    assert np.allclose(np.asarray(w).sum(-1), 1.0, atol=1e-6)                                    # renormalised top-k
    counts = np.bincount(idx.reshape(-1), minlength=F32.num_experts)
    assert counts.sum() == 200 * F32.top_k                                                       # dropless: every assignment is served


def test_norm_topk_false_keeps_raw_probabilities():
    c = dataclasses.replace(F32, norm_topk_prob=False)
    x = jax.random.normal(jax.random.key(3), (50, c.hidden))
    _, probs, idx, w = route(x, init_base_random(jax.random.key(0), c)["layers"]["router_w"][0], c)
    assert np.allclose(np.asarray(w), np.take_along_axis(np.asarray(probs), np.asarray(idx), -1), atol=1e-7)
    assert (np.asarray(w).sum(-1) < 1.0).all()


def _hf_balance(logits, k, mask):
    """Independent NumPy transcription of HF's load_balancing_loss_func for one layer (written from memory of that function)."""
    p = np.exp(logits - logits.max(-1, keepdims=True)); p /= p.sum(-1, keepdims=True)
    top = np.argsort(-logits, axis=-1, kind="stable")[:, :k]; E = logits.shape[-1]
    em = np.eye(E)[top]; m = mask.reshape(-1, 1, 1).astype(float)
    tpe = (em * m).sum(0) / m.sum()
    rpe = (p * mask.reshape(-1, 1)).sum(0) / mask.sum()
    return (tpe * rpe[None, :]).sum() * E


def test_balance_loss_matches_numpy_reference_with_padding_mask():
    l = LoraConfig(targets=("q", "v"))
    base, lora = init_base_random(jax.random.key(0), F32), init_lora(jax.random.key(1), F32, l)
    toks = jax.random.randint(jax.random.key(2), (2, 12), 0, F32.vocab_size)
    valid = np.ones((2, 12), bool); valid[:, 9:] = False
    _, aux = forward_with_aux(base, lora, toks, F32, l, valid=jnp.asarray(valid), return_router=True)
    lg = np.asarray(aux["router_logits"])
    for L in range(F32.layers):
        ref = _hf_balance(lg[L].reshape(-1, F32.num_experts), F32.top_k, valid.reshape(-1))
        assert abs(float(aux["aux"][L]) - ref) < 1e-5
    # padded positions must not influence the loss: change the padding tokens, aux is unchanged
    toks2 = jnp.where(jnp.asarray(valid), toks, (toks + 7) % F32.vocab_size)
    _, aux2 = forward_with_aux(base, lora, toks2, F32, l, valid=jnp.asarray(valid))
    assert np.allclose(np.asarray(aux["aux"]), np.asarray(aux2["aux"]), atol=1e-6)


def test_aux_coefficient_changes_objective_but_not_reported_task_loss():
    l = LoraConfig(targets=("q", "v"), dropout=0.0)
    base, lora = init_base_random(jax.random.key(0), F32), init_lora(jax.random.key(1), F32, l)
    toks = jax.random.randint(jax.random.key(2), (2, 12), 0, F32.vocab_size); m = jnp.ones((2, 12), bool)
    t0, i0 = loss_and_aux(base, lora, toks, m, F32, l, aux_coef=0.0)
    t1, i1 = loss_and_aux(base, lora, toks, m, F32, l, aux_coef=0.5)
    assert float(i0["ce"]) == float(i1["ce"]) and abs(float(t1 - t0) - 0.5 * float(i1["aux"])) < 1e-5


def test_router_is_frozen_and_never_enters_the_checkpoint_state(cfg):
    l = LoraConfig(targets=ALL_T)
    lora = init_lora(jax.random.key(1), F32, l)
    flat = ["".join(str(k) for k in p) for p, _ in jax.tree_util.tree_flatten_with_path(lora)[0]]
    assert flat and not any("router" in f for f in flat)
    assert lora["e_gate"]["a"].shape == (F32.layers, F32.num_experts, F32.hidden, l.r)      # per-expert adapters


# ----------------------------------------------------------------------------- configs and loaders
HF = {
    "qwen2_moe": dict(model_type="qwen2_moe", vocab_size=100, hidden_size=64, intermediate_size=128, num_hidden_layers=2,
                      num_attention_heads=4, num_key_value_heads=2, num_experts=8, num_experts_per_tok=2,
                      moe_intermediate_size=32, shared_expert_intermediate_size=48, norm_topk_prob=False),
    "qwen3_moe": dict(model_type="qwen3_moe", vocab_size=100, hidden_size=64, intermediate_size=128, num_hidden_layers=2,
                      num_attention_heads=4, num_key_value_heads=2, head_dim=32, num_experts=8, num_experts_per_tok=2,
                      moe_intermediate_size=32, norm_topk_prob=True, decoder_sparse_step=1, mlp_only_layers=[]),
    "mixtral": dict(model_type="mixtral", vocab_size=100, hidden_size=64, intermediate_size=96, num_hidden_layers=2,
                    num_attention_heads=4, num_key_value_heads=2, num_local_experts=8, num_experts_per_tok=2, sliding_window=None),
    "olmoe": dict(model_type="olmoe", vocab_size=100, hidden_size=64, intermediate_size=32, num_hidden_layers=2,
                  num_attention_heads=4, num_key_value_heads=4, num_experts=8, num_experts_per_tok=2, clip_qkv=None),
}


@pytest.mark.parametrize("family", list(HF))
def test_config_parsing_and_weight_roundtrip_per_family(family, tmp_path):
    cfg_ = ModelConfig.from_hf_config(HF[family], dtype="bfloat16")
    assert cfg_.is_moe and cfg_.num_experts == 8 and cfg_.top_k == 2 and hf_io.family_of(cfg_) == family
    base = init_base_random(jax.random.key(0), cfg_)
    tens = hf_io.params_to_hf(base, cfg_)
    hf_io.write_safetensors(str(tmp_path / "m.safetensors"), tens)
    back = hf_io.hf_to_params(hf_io.read_hf_dir(str(tmp_path)), cfg_)
    assert jax.tree.structure(back) == jax.tree.structure(base)
    for a, b in zip(jax.tree.leaves(base), jax.tree.leaves(back)):
        assert np.asarray(a).dtype == np.asarray(b).dtype and np.array_equal(np.asarray(a), np.asarray(b))
    keys = list(tens)
    if family == "mixtral":
        assert "model.layers.0.block_sparse_moe.experts.0.w1.weight" in keys and not any(".mlp." in k for k in keys)
    else:
        assert "model.layers.0.mlp.experts.0.gate_proj.weight" in keys and "model.layers.0.mlp.gate.weight" in keys
    assert (family == "qwen2_moe") == ("model.layers.0.mlp.shared_expert_gate.weight" in keys)


def test_family_specific_semantics_from_config():
    q3 = ModelConfig.from_hf_config(HF["qwen3_moe"]); assert q3.qk_norm == "head" and q3.head_dim == 32 and q3.norm_topk_prob
    q2 = ModelConfig.from_hf_config(HF["qwen2_moe"]); assert q2.qkv_bias and q2.shared_intermediate == 48 and not q2.norm_topk_prob
    mx = ModelConfig.from_hf_config(HF["mixtral"]); assert mx.moe_intermediate == 96 and mx.norm_topk_prob and not mx.qkv_bias
    ol = ModelConfig.from_hf_config(HF["olmoe"]); assert ol.qk_norm == "full" and ol.moe_intermediate == 32


@pytest.mark.parametrize("patch,msg", [
    ({"mlp_only_layers": [0]}, "mixed dense/MoE"),
    ({"decoder_sparse_step": 2}, "mixed dense/MoE"),
    ({"use_sliding_window": True}, "sliding-window"),
    ({"clip_qkv": 8.0}, "clip_qkv"),
])
def test_unsupported_architectures_fail_loudly_instead_of_loading_wrongly(patch, msg):
    with pytest.raises(NotImplementedError, match=msg):
        ModelConfig.from_hf_config({**HF["qwen3_moe"], **patch})


def test_missing_tensor_names_the_exact_key(tmp_path):
    cfg_ = ModelConfig.from_hf_config(HF["mixtral"])
    tens = hf_io.params_to_hf(init_base_random(jax.random.key(0), cfg_), cfg_)
    del tens["model.layers.1.block_sparse_moe.experts.5.w2.weight"]
    hf_io.write_safetensors(str(tmp_path / "m.safetensors"), tens)
    with pytest.raises(KeyError, match="experts.5.w2"):
        hf_io.hf_to_params(hf_io.read_hf_dir(str(tmp_path)), cfg_)


def test_lora_target_validation_guides_moe_vs_dense():
    with pytest.raises(ValueError, match="MoE model: use e_gate"):
        validate_targets(TINY_MOE, LoraConfig(targets=("q", "gate")))
    with pytest.raises(ValueError, match="dense model"):
        validate_targets(TINY, LoraConfig(targets=("q", "e_gate")))
    with pytest.raises(ValueError):
        validate_targets(dataclasses.replace(TINY_MOE, shared_intermediate=0), LoraConfig(targets=("s_gate",)))


# ----------------------------------------------------------------------------- resume semantics for MoE
def test_moe_resume_is_bitwise_identical_and_records_routing(cfg, tmp_path):
    ref = run_leg(cfg, str(tmp_path / "ref"), 12, log=quiet, probe_steps=[6, 12])
    a = run_leg(cfg, str(tmp_path / "a"), 6, log=quiet, probe_steps=[6])
    b = run_leg(cfg, str(tmp_path / "b"), 12, resume_from=a["ckpt_dir"], log=quiet, probe_steps=[12])
    assert b["final_digest"] == ref["final_digest"]
    key = lambda s: [(t["loss"], t["aux"], t["load_max"]) for t in s["trace"]]
    assert key(b) == key(ref) and b["restore"]["roundtrip_exact"]
    for st, leg in (("6", a), ("12", b)):
        pa, pb = V.load_probe(ref["probes"][st]["path"]), V.load_probe(leg["probes"][st]["path"])
        assert V.routing_compare(pa, pb)["n_flips"] == 0
    assert ref["model"]["is_moe"] and ref["probes"]["6"]["shape"][-1] == 2


@pytest.mark.parametrize("field,val", [("aux_coef", 0.5), ("moe_impl", "dense"), ("z_coef", 0.1)])
def test_moe_hyperparameters_are_part_of_run_identity(cfg, tmp_path, field, val):
    a = run_leg(cfg, str(tmp_path / "a"), 3, log=quiet)
    c = copy.deepcopy(cfg); setattr(c, field, val)
    with pytest.raises(IdentityMismatch):
        run_leg(c, str(tmp_path / "b"), 6, resume_from=a["ckpt_dir"], log=quiet)


def test_unknown_lora_target_is_rejected_before_any_training(cfg, tmp_path):
    c = copy.deepcopy(cfg); c.lora = dict(c.lora, targets=["q", "gate"])
    with pytest.raises(ValueError, match="MoE model"):
        run_leg(c, str(tmp_path / "x"), 3, log=quiet)


# ----------------------------------------------------------------------------- routing validation logic
def _probe(tmp_path, name, idx, margin, valid, step=6):
    p = str(tmp_path / f"{name}.npz")
    np.savez_compressed(p, idx=idx.astype(np.int16), margin=margin.astype(np.float32), valid=valid, step=np.int64(step))
    return p


def _synthetic(tmp_path, n_flip, flip_margin=1e-4):
    L, B, T, K = 2, 2, 50, 2
    rng = np.random.default_rng(0)
    idx = np.sort(rng.integers(0, 8, (L, B, T, K)), axis=-1); idx[..., 1] = np.maximum(idx[..., 1], idx[..., 0] + 1) % 8
    idx = np.sort(idx, axis=-1)
    margin = rng.uniform(0.05, 2.0, (L, B, T)); valid = np.ones((B, T), bool); valid[:, 40:] = False
    idx2 = idx.copy(); flat_valid = [(l, b, t) for l in range(L) for b in range(B) for t in range(40)]
    for (l, b, t) in flat_valid[:n_flip]:
        idx2[l, b, t, 0] = (idx2[l, b, t, 0] + 3) % 8; idx2[l, b, t] = np.sort(idx2[l, b, t]); margin[l, b, t] = flip_margin
    return (_probe(tmp_path, "ref", idx, margin, valid), _probe(tmp_path, "leg", idx2, margin, valid))


def test_routing_compare_counts_only_valid_tokens_and_reports_flip_margins(tmp_path):
    ref, leg = _synthetic(tmp_path, n_flip=5)
    r = V.routing_compare(V.load_probe(ref), V.load_probe(leg))
    assert r["n_decisions"] == 2 * 2 * 40 and r["n_flips"] >= 4                                    # padded positions excluded
    assert r["flip_margin_ref"]["median_percentile_in_population"] < 0.05                          # flips sit on the near-ties


def _leg_with_probe(vendor, path, end=6, kind="x"):
    env = {"vendor": vendor, "device_kind": kind, "jax": "1", "jaxlib": "1", "xla_flags": "", "matmul_precision": "highest"}
    return {"env": env, "end_step": end, "probes": {str(end): {"local_path": path}}}


def test_same_platform_routing_must_be_identical(tmp_path):
    ref, leg = _synthetic(tmp_path, n_flip=1)
    c = V.check_routing("r", _leg_with_probe("nvidia", leg), _leg_with_probe("nvidia", ref), floor=None, floor_mult=3.0, abs_tol=0.5)
    assert c.passed is False and "identical" in c.detail["mode"]
    c = V.check_routing("r", _leg_with_probe("nvidia", ref), _leg_with_probe("nvidia", ref), floor=None, floor_mult=3.0, abs_tol=0.0)
    assert c.passed is True


def test_cross_platform_routing_uses_measured_floor_and_flags_uncalibrated(tmp_path):
    ref, leg = _synthetic(tmp_path, n_flip=5)                    # ~3% of 160 decisions
    lr, rr = _leg_with_probe("amd", leg), _leg_with_probe("nvidia", ref)
    ok = V.check_routing("r", lr, rr, floor={"6": {"max_disagreement": 0.02}}, floor_mult=3.0, abs_tol=0.0)
    bad = V.check_routing("r", lr, rr, floor={"6": {"max_disagreement": 0.001}}, floor_mult=3.0, abs_tol=0.0)
    unc = V.check_routing("r", lr, rr, floor=None, floor_mult=3.0, abs_tol=0.5)
    assert ok.passed and not bad.passed and "cross-platform vs measured" in ok.detail["mode"]
    assert unc.passed and "warning" in unc.detail                # provisional: verdict will say TOLERANCE_UNCALIBRATED
    v = V.verdict([unc], [{"env": {"vendor": "nvidia"}}, {"env": {"vendor": "amd"}}])
    assert v["status"] == "CROSS_VENDOR_DEMONSTRATED_TOLERANCE_UNCALIBRATED"


def test_missing_probe_fails_instead_of_passing_silently(tmp_path):
    ref, _ = _synthetic(tmp_path, n_flip=0)
    leg = {"env": _leg_with_probe("cpu", ref)["env"], "end_step": 6, "probes": {}}
    assert V.check_routing("r", leg, _leg_with_probe("cpu", ref), floor=None, floor_mult=3.0, abs_tol=1.0).passed is False


def test_non_finite_metrics_are_caught():
    ok = {"trace": [{"step": 1, "loss": 1.0, "aux": 2.0}]}
    bad = {"trace": [{"step": 1, "loss": 1.0, "aux": 2.0}, {"step": 2, "loss": float("nan"), "aux": 2.0}]}
    assert V.check_finite("f", ok).passed and not V.check_finite("f", bad).passed and V.check_finite("f", bad).detail["non_finite_steps"] == [2]


# ----------------------------------------------------------------------------- end to end
def test_full_local_moe_relay_end_to_end(tmp_path):
    import harness
    plan = json.load(open(os.path.join(ROOT, "experiments", "moe_local_dryrun_plan.json")))
    plan["train_config"] = CFG
    plan["hosts"] = {"nvidia": {"root": str(tmp_path / "A"), "vendor": "cpu"}, "amd": {"root": str(tmp_path / "B"), "vendor": "cpu"}}
    plan["noise_floor"]["runs"] = 1
    plan["relays"] = [plan["relays"][1]]
    pp = tmp_path / "plan.json"; pp.write_text(json.dumps(plan))
    tp = harness.LocalTransport({k: v["root"] for k, v in plan["hosts"].items()}, code_dir=ROOT)
    rep = harness.run_experiment(str(pp), tp, str(tmp_path / "run"))
    assert rep["verdict"]["status"] == "MECHANICS_OK_NO_CROSS_VENDOR_CLAIM" and not rep["verdict"]["failed_checks"]
    routing = [c for c in rep["checks"] if "routing" in c["name"]]
    assert len(routing) == 3 and all(c["passed"] for c in routing)
    assert set(rep["noise_floor"]["routing"]) == {"6", "9", "12"}
    assert any(c["name"].endswith("all_metrics_finite") for c in rep["checks"])


# ----------------------------------------------------------------------------- real Qwen configs
FIX = os.path.join(ROOT, "tests", "fixtures")


@pytest.mark.parametrize("fname,total,active,family", [
    ("qwen1.5-moe-a2.7b.config.json", 14.3e9, 2.7e9, "qwen2_moe"),   # HF model card: "14.3B parameters in total and 2.7B activated"
    ("qwen3-30b-a3b.config.json", 30.5e9, 3.3e9, "qwen3_moe"),       # HF model card: "30.5B in total and 3.3B activated"
])
def test_real_qwen_moe_configs_parse_and_reproduce_published_parameter_counts(fname, total, active, family):
    """Independent check on architecture accounting: counts derived from the config must match the vendor's published numbers."""
    m = ModelConfig.from_hf_config(os.path.join(FIX, fname))
    n = count_params(m)
    assert hf_io.family_of(m) == family
    assert abs(n["total"] - total) / total < 0.01, n
    assert abs(n["active"] - active) / active < 0.03, n


def test_qwen15_moe_specifics_and_sliding_window_guard_does_not_misfire():
    m = ModelConfig.from_hf_config(os.path.join(FIX, "qwen1.5-moe-a2.7b.config.json"))   # has sliding_window=32768 but use_sliding_window=false
    assert (m.num_experts, m.top_k, m.moe_intermediate, m.shared_intermediate) == (60, 4, 1408, 5632)
    assert m.qkv_bias and not m.norm_topk_prob and m.kv_heads == m.heads == 16 and m.head_dim == 128
    q3 = ModelConfig.from_hf_config(os.path.join(FIX, "qwen3-30b-a3b.config.json"))
    assert (q3.num_experts, q3.top_k, q3.moe_intermediate, q3.kv_heads, q3.head_dim) == (128, 8, 768, 4, 128)
    assert q3.qk_norm == "head" and q3.norm_topk_prob and not q3.qkv_bias and q3.shared_intermediate == 0
    assert q3.heads * q3.head_dim != q3.hidden          # Qwen3 decouples head_dim from hidden/heads: must not be inferred


@pytest.mark.parametrize("family", list(HF))
def test_count_params_equals_actual_parameter_count_of_initialised_model(family):
    m = ModelConfig.from_hf_config(HF[family])
    actual = sum(int(np.prod(x.shape)) for x in jax.tree.leaves(init_base_random(jax.random.key(0), m)))
    assert count_params(m)["total"] == actual
