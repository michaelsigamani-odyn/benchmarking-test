"""Relay harness: reference run, same-vendor control relay, cross-vendor relays, noise floor.

Transports
  LocalTransport  every "host" is a directory on this machine (used for tests / dry runs)
  SshTransport    key-based ssh + rsync --checksum. NOT exercised in the sandbox this was written in.
                  Remote legs are launched *detached* (nohup) and polled with short ssh calls, so a
                  dropped connection during a long leg cannot kill the run (this was the failure mode
                  of the 0/3 Story-3 report: "Read from remote host ... Operation timed out").
No passwords: BatchMode=yes, keys only.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from jaxft import validate as V


# --------------------------------------------------------------------------- transports
class LocalTransport:
    def __init__(self, roots: Dict[str, str], code_dir: str):
        self.roots, self.code_dir = roots, os.path.abspath(code_dir)

    def _p(self, host, rel):
        return rel if os.path.isabs(rel) else os.path.join(self.roots[host], rel)

    def run_leg(self, host: str, cfg_path: str, out_rel: str, end_step: int, resume_abs: Optional[str],
                require_vendor: Optional[str], extra: List[str]) -> Dict[str, Any]:
        out = self._p(host, out_rel); os.makedirs(out, exist_ok=True)
        cmd = [sys.executable, os.path.join(self.code_dir, "run_leg.py"), "--config", cfg_path, "--out-dir", out,
               "--end-step", str(end_step), *extra]
        if resume_abs: cmd += ["--resume-from", resume_abs]
        if require_vendor: cmd += ["--require-vendor", require_vendor]
        with open(os.path.join(out, "leg.log"), "w") as log:
            r = subprocess.run(cmd, cwd=self.code_dir, stdout=log, stderr=subprocess.STDOUT)
        if r.returncode != 0:
            raise RuntimeError(f"leg failed on {host} (rc={r.returncode}); tail of {out}/leg.log:\n"
                               + open(os.path.join(out, "leg.log")).read()[-1500:])
        with open(os.path.join(out, "leg_summary.json")) as f:
            return json.load(f)

    def fetch(self, host: str, remote_abs: str, local_path: str) -> None:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copyfile(remote_abs, local_path)

    def transfer(self, src_host: str, src_abs: str, dst_host: str, dst_rel: str) -> str:
        dst = self._p(dst_host, dst_rel)
        shutil.rmtree(dst, ignore_errors=True); os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copytree(src_abs, dst)
        return dst


class SshTransport:
    SSH = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=6"]

    def __init__(self, hosts: Dict[str, Dict[str, str]], staging: str, retries: int = 5, poll_s: int = 20,
                 leg_timeout_s: int = 6 * 3600):
        self.h, self.staging, self.retries, self.poll_s, self.leg_timeout_s = hosts, staging, retries, poll_s, leg_timeout_s

    def _ssh(self, host: str, cmd: str, check=True) -> subprocess.CompletedProcess:
        last = None
        for i in range(self.retries):
            last = subprocess.run(["ssh", *self.SSH, self.h[host]["ssh"], cmd], text=True, capture_output=True)
            if last.returncode == 0 or not check:
                return last
            time.sleep(min(2 ** i, 30))
        raise RuntimeError(f"ssh {host}: {cmd!r} failed after {self.retries} tries: {last.stderr[-500:]}")

    def _root(self, host): return self.h[host]["root"]

    def run_leg(self, host, cfg_path, out_rel, end_step, resume_abs, require_vendor, extra):
        root, out = self._root(host), f"{self._root(host)}/{out_rel}"
        remote_cfg = f"{root}/_cfg/{os.path.basename(cfg_path)}"   # ship the exact config used, byte for byte
        self._ssh(host, f"mkdir -p {root}/_cfg")
        subprocess.run(["rsync", "-a", "--checksum", "-e", "ssh " + " ".join(self.SSH), cfg_path,
                        f"{self.h[host]['ssh']}:{remote_cfg}"], check=True)
        args = ["python3", "run_leg.py", "--config", remote_cfg, "--out-dir", out, "--end-step", str(end_step), *extra]
        if resume_abs: args += ["--resume-from", resume_abs]
        if require_vendor: args += ["--require-vendor", require_vendor]
        inner = f"cd {root} && rm -f {out}/EXIT && mkdir -p {out} && " \
                f"{self.h[host].get('activate', 'true')} && {shlex.join(args)} > {out}/leg.log 2>&1; echo $? > {out}/EXIT"
        self._ssh(host, f"nohup bash -c {shlex.quote(inner)} >/dev/null 2>&1 &")
        t0 = time.time()
        while time.time() - t0 < self.leg_timeout_s:
            time.sleep(self.poll_s)
            r = self._ssh(host, f"cat {out}/EXIT 2>/dev/null", check=False)  # transient ssh errors just retry next poll
            if r.returncode == 0 and r.stdout.strip():
                if r.stdout.strip() != "0":
                    tail = self._ssh(host, f"tail -c 1500 {out}/leg.log", check=False).stdout
                    raise RuntimeError(f"leg failed on {host} rc={r.stdout.strip()}:\n{tail}")
                return json.loads(self._ssh(host, f"cat {out}/leg_summary.json").stdout)
        raise TimeoutError(f"leg on {host} exceeded {self.leg_timeout_s}s (still running detached at {out})")

    def fetch(self, host, remote_abs, local_path):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        subprocess.run(["rsync", "-a", "--checksum", "--partial", "-e", "ssh " + " ".join(self.SSH),
                        f"{self.h[host]['ssh']}:{remote_abs}", local_path], check=True)

    def transfer(self, src_host, src_abs, dst_host, dst_rel):
        stage = os.path.join(self.staging, os.path.basename(src_abs.rstrip("/")))
        os.makedirs(self.staging, exist_ok=True)
        dst = f"{self._root(dst_host)}/{dst_rel}"
        for a, b in ((f"{self.h[src_host]['ssh']}:{src_abs}/", stage + "/"), (stage + "/", f"{self.h[dst_host]['ssh']}:{dst}/")):
            subprocess.run(["rsync", "-a", "--checksum", "--partial", "-e", "ssh " + " ".join(self.SSH), a, b], check=True)
        return dst


# --------------------------------------------------------------------------- experiment
def run_relay(tp, plan, cfg_path, relay, run_dir, extra) -> List[Dict[str, Any]]:
    steps = [plan["legs"][k] for k in ("leg1", "leg2", "leg3")]
    legs, resume = [], None
    for i, (h, end) in enumerate(zip(relay["hosts"], steps)):
        out = f"{run_dir}/{relay['name']}/leg{i + 1}_{h}"
        legs.append(_collect(tp, h, tp.run_leg(h, cfg_path, out, end, resume, plan["hosts"][h]["vendor"], _extra(plan, extra)),
                             run_dir, f"{relay['name']}/leg{i + 1}"))
        if i < len(steps) - 1:
            resume = tp.transfer(h, legs[-1]["ckpt_dir"], relay["hosts"][i + 1], f"{run_dir}/{relay['name']}/in_{i + 1}_ckpt-{end}")
    return legs


def _host_vendor(plan, h): return plan["hosts"][h]["vendor"]


def _extra(plan, extra) -> List[str]:
    """Every leg saves routing probes at the plan's leg boundaries (ignored by dense models)."""
    steps = ",".join(str(plan["legs"][k]) for k in ("leg1", "leg2", "leg3"))
    return ["--probe-steps", steps, "--probe-n", str(plan.get("probe_n", 8)), *list(extra)]


def _collect(tp, host, leg, run_dir, label):
    """Pull routing-probe files from the host that produced them, so validation can compare them locally."""
    for step, pr in leg.get("probes", {}).items():
        local = os.path.join(run_dir, "_probes", label.replace("/", "__"), f"step{step}.npz")
        tp.fetch(host, pr["path"], local)
        pr["local_path"] = local
    return leg


def _save(run_dir: str, label: str, obj: Any) -> None:
    d = os.path.join(run_dir, "_summaries"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{label}.json"), "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def _load(run_dir: str, label: str) -> Any:
    with open(os.path.join(run_dir, "_summaries", f"{label}.json")) as f:
        return json.load(f)


def run_reference(tp, plan, run_dir, extra=()) -> Dict[str, Any]:
    h, cfg_path = plan["reference"]["host"], os.path.abspath(plan["train_config"])
    ref = _collect(tp, h, tp.run_leg(h, cfg_path, f"{run_dir}/reference", plan["legs"]["leg3"], None, _host_vendor(plan, h),
                                     _extra(plan, extra)), run_dir, "reference")
    _save(run_dir, "reference", ref)
    return ref


def run_noise(tp, plan, run_dir, reference, extra=()) -> Optional[Dict[str, Any]]:
    nf = plan.get("noise_floor")
    if not nf:
        return None
    cfg_path = os.path.abspath(plan["train_config"]); base_cfg = json.load(open(cfg_path)); traces, probes = [], []
    for k in range(nf["runs"]):
        pp = os.path.join(os.path.dirname(cfg_path), f".noise_{k}.json")
        json.dump(dict(base_cfg, init_perturb=nf["init_perturb"], init_perturb_seed=k), open(pp, "w"))
        leg = _collect(tp, nf["host"], tp.run_leg(nf["host"], pp, f"{run_dir}/noise_{k}", plan["legs"]["leg3"], None,
                                                  _host_vendor(plan, nf["host"]), _extra(plan, extra)), run_dir, f"noise_{k}")
        traces.append(leg["trace"]); probes.append({st: p["local_path"] for st, p in leg.get("probes", {}).items()})
    floor = V.noise_floor(reference["trace"], traces)
    ref_probes = {st: p["local_path"] for st, p in reference.get("probes", {}).items()}
    if ref_probes:
        floor["routing"] = V.routing_floor(ref_probes, probes)
    _save(run_dir, "noise_floor", floor)
    return floor


def run_named_relay(tp, plan, name, run_dir, extra=()) -> List[Dict[str, Any]]:
    relay = next(r for r in plan["relays"] if r["name"] == name)
    legs = run_relay(tp, plan, os.path.abspath(plan["train_config"]), relay, run_dir, list(extra))
    _save(run_dir, f"relay_{name}", legs)
    return legs


def build_report_from_disk(plan, run_dir) -> Dict[str, Any]:
    floor = _load(run_dir, "noise_floor") if os.path.exists(os.path.join(run_dir, "_summaries", "noise_floor.json")) else None
    return build_report(plan, _load(run_dir, "reference"), floor,
                        {r["name"]: _load(run_dir, f"relay_{r['name']}") for r in plan["relays"]}, run_dir)


def build_report(plan, reference, floor, relay_legs: Dict[str, List[Dict[str, Any]]], run_dir) -> Dict[str, Any]:
    tol, checks, all_legs, relays_out = plan["tolerances"], [], [reference], {}
    for relay in plan["relays"]:
        legs = relay_legs[relay["name"]]; all_legs += legs
        relays_out[relay["name"]] = [{"host": h, "end_step": l["end_step"], "vendor": l["env"]["vendor"],
                                      "device_kind": l["env"]["device_kind"], "final_digest": l["final_digest"]}
                                     for h, l in zip(relay["hosts"], legs)]
        for i in range(1, len(legs)):
            for c in V.check_handoff(legs[i - 1], legs[i], plan["min_extra_steps"], _host_vendor(plan, relay["hosts"][i - 1]),
                                     _host_vendor(plan, relay["hosts"][i])):
                c.name = f"{relay['name']}/hop{i}/{c.name}"; checks.append(c)
        for i, l in enumerate(legs):
            checks.append(V.check_trajectory(f"{relay['name']}/leg{i + 1}_vs_reference", l, reference,
                                             abs_tol=tol["abs_tol_uncalibrated"], floor=floor, floor_mult=tol["floor_mult"]))
            checks.append(V.Check(f"{relay['name']}/leg{i + 1}/identity_equals_reference", l["identity_hash"] == reference["identity_hash"]))
            checks.append(V.check_finite(f"{relay['name']}/leg{i + 1}/all_metrics_finite", l))
            if l.get("model", {}).get("is_moe"):
                checks.append(V.check_routing(f"{relay['name']}/leg{i + 1}_routing_vs_reference", l, reference,
                                              floor=(floor or {}).get("routing"), floor_mult=tol["floor_mult"],
                                              abs_tol=tol.get("routing_disagreement_uncalibrated", 0.02)))
    vers = {(l["env"]["jax"], l["env"]["jaxlib"], ".".join(l["env"]["python"].split(".")[:2])) for l in all_legs}
    checks.append(V.Check("jax_jaxlib_python_minor_uniform_across_legs", len(vers) == 1, sorted(vers), required=False))
    report = {"experiment": plan["experiment_name"], "noise_floor": floor, "relays": relays_out,
              "checks": [c.as_dict() for c in checks], "verdict": V.verdict(checks, all_legs),
              "reference": {"vendor": reference["env"]["vendor"], "device_kind": reference["env"]["device_kind"],
                            "final_digest": reference["final_digest"]},
              "envs": {l["env"]["hostname"] + ":" + l["env"]["vendor"]: {k: l["env"][k] for k in
                       ("jax", "jaxlib", "device_kind", "platform_version", "python", "xla_flags", "vendor_evidence")} for l in all_legs}}
    os.makedirs(run_dir, exist_ok=True)
    json.dump(report, open(os.path.join(run_dir, "report.json"), "w"), indent=2)
    return report


def run_experiment(plan_path: str, tp, run_dir: str, extra: Optional[List[str]] = None) -> Dict[str, Any]:
    plan = json.load(open(plan_path)); extra = extra or []
    ref = run_reference(tp, plan, run_dir, extra)
    floor = run_noise(tp, plan, run_dir, ref, extra)
    relays = {r["name"]: run_named_relay(tp, plan, r["name"], run_dir, extra) for r in plan["relays"]}
    return build_report(plan, ref, floor, relays, run_dir)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True); ap.add_argument("--run-dir", required=True)
    ap.add_argument("--transport", choices=["local", "ssh"], required=True)
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    if a.transport == "ssh":
        tp = SshTransport(plan["hosts"], staging=os.path.join(a.run_dir, "_staging"))
    else:
        tp = LocalTransport({k: v["root"] for k, v in plan["hosts"].items()}, code_dir=os.path.dirname(os.path.abspath(__file__)))
    rep = run_experiment(a.plan, tp, a.run_dir)
    print(json.dumps(rep["verdict"], indent=2))
    sys.exit(0 if not rep["verdict"]["failed_checks"] else 1)
