"""Checkpoint = the *entire* training state as one pytree: {lora, opt_state, step}.

There is no hidden framework state (no RNG snapshot, no dataloader cursor, no scheduler object):
* randomness is derived from (seed, step) keys
* the LR schedule is a pure function of `count` inside `opt_state`
* batches are a pure function of (seed, step)
so "state transferred" is a checkable statement about arrays, not about framework internals.

Two independent pieces of evidence are written next to every checkpoint:
* `digest.json`         canonical sha256 of every array (dtype+shape+bytes), independent of Orbax
* `files_manifest.json` sha256 of every file on disk, to verify the copy between hosts
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional

import jax
import jax.numpy as jnp
import numpy as np
import orbax.checkpoint as ocp

from .device_transfer import tree_to_host


def _leaf_bytes(x) -> bytes:
    a = np.ascontiguousarray(np.asarray(x))
    return a.tobytes()


def state_digest(tree: Any) -> Dict[str, Any]:
    """Canonical digest of a pytree of arrays: per-leaf sha256 plus one overall hash."""
    flat, _ = jax.tree_util.tree_flatten_with_path(tree_to_host(tree))
    leaves, overall = {}, hashlib.sha256()
    for path, x in flat:
        a = np.asarray(x)
        key = jax.tree_util.keystr(path)
        h = hashlib.sha256(f"{key}|{a.dtype}|{a.shape}|".encode() + _leaf_bytes(a)).hexdigest()
        leaves[key] = h
        overall.update(h.encode())
    return {"overall": overall.hexdigest(), "n_leaves": len(leaves), "leaves": leaves}


def diff_digests(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    la, lb = a["leaves"], b["leaves"]
    return {"only_a": sorted(set(la) - set(lb)), "only_b": sorted(set(lb) - set(la)),
            "differing": sorted(k for k in set(la) & set(lb) if la[k] != lb[k])}


def file_manifest(directory: str, exclude=("files_manifest.json",)) -> Dict[str, Any]:
    files = {}
    for root, _, names in os.walk(directory):
        for n in sorted(names):
            if n in exclude:
                continue
            p = os.path.join(root, n)
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            files[os.path.relpath(p, directory)] = {"sha256": h.hexdigest(), "bytes": os.path.getsize(p)}
    return {"n_files": len(files), "files": dict(sorted(files.items()))}


def abstract_like(tree: Any) -> Any:
    return jax.tree.map(lambda x: jax.ShapeDtypeStruct(np.shape(x), jnp.asarray(x).dtype), tree)


def save_checkpoint(ckpt_dir: str, state: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(ckpt_dir, exist_ok=True)
    ckptr = ocp.StandardCheckpointer()
    ckptr.save(os.path.join(ckpt_dir, "orbax"), state, force=True)
    ckptr.wait_until_finished()
    digest = state_digest(state)
    for name, payload in (("meta.json", meta), ("digest.json", digest)):
        with open(os.path.join(ckpt_dir, name), "w") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
    with open(os.path.join(ckpt_dir, "files_manifest.json"), "w") as f:
        json.dump(file_manifest(ckpt_dir), f, indent=2, sort_keys=True)  # written last; covers everything else
    return digest


def read_meta(ckpt_dir: str) -> Dict[str, Any]:
    with open(os.path.join(ckpt_dir, "meta.json")) as f:
        return json.load(f)


def restore_checkpoint(ckpt_dir: str, template_state: Dict[str, Any]) -> Dict[str, Any]:
    ckptr = ocp.StandardCheckpointer()
    return ckptr.restore(os.path.join(ckpt_dir, "orbax"), abstract_like(template_state))


def verify_manifest(ckpt_dir: str) -> Dict[str, Any]:
    """Recompute file hashes and compare with the manifest that was written at save time."""
    with open(os.path.join(ckpt_dir, "files_manifest.json")) as f:
        want = json.load(f)
    got = file_manifest(ckpt_dir)
    wf, gf = want["files"], got["files"]
    return {"ok": wf == gf, "missing": sorted(set(wf) - set(gf)), "unexpected": sorted(set(gf) - set(wf)),
            "modified": sorted(k for k in set(wf) & set(gf) if wf[k] != gf[k])}
