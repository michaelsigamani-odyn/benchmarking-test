"""Data pipeline whose batch at step `s` is a pure function of (seed, s).

Why this matters for portability: the PyTorch version relied on framework RNG/DataLoader state
saved in the checkpoint, and torch's CUDA RNG state is not meaningful on another vendor. Here
there is no data-loader state at all, so any leg on any machine sees exactly the same batches,
which also makes loss comparisons between runs *paired* (no data-order noise).
"""
from __future__ import annotations

import functools
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class ByteTokenizer:
    """UTF-8 bytes + 3 specials. Used for tests/smoke runs so no network or HF hub is needed."""
    pad_id, bos_id, eos_id, vocab_size = 256, 257, 258, 272

    def encode(self, text: str) -> List[int]:
        return list(text.encode("utf-8"))


class HFTokenizer:
    def __init__(self, name_or_path: str):
        from transformers import AutoTokenizer  # only needed on the machine that prepares data
        self.tok = AutoTokenizer.from_pretrained(name_or_path)
        self.eos_id = self.tok.eos_token_id
        self.pad_id = self.tok.pad_token_id if self.tok.pad_token_id is not None else self.eos_id
        self.vocab_size = len(self.tok)

    def encode(self, text: str) -> List[int]:
        return self.tok.encode(text, add_special_tokens=False)


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path) as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    assert rows, f"dataset is empty: {path}"
    return rows


def render(record: Dict[str, Any]) -> Tuple[str, str]:
    """Same template as the PyTorch repo, split so the loss can be restricted to the response."""
    ins, inp, out = (str(record.get(k, "")).strip() for k in ("instruction", "input", "output"))
    return f"Instruction: {ins}\nInput: {inp or 'N/A'}\nResponse:", f" {out}"


def build_arrays(records, tok, max_len: int, loss_on: str = "response",
                 drop_empty: bool = True) -> Dict[str, np.ndarray]:
    """Returns arrays plus `dropped` (indices of examples with no target token after truncation).

    An example whose prompt fills the context has an all-False loss mask; left in, a batch of such
    examples yields loss 0/0 -> 0.0, a silent fake value. They are dropped (and counted) by default.
    """
    ids = np.full((len(records), max_len), tok.pad_id, np.int32)
    mask = np.zeros((len(records), max_len), np.bool_)
    valid = np.zeros((len(records), max_len), np.bool_)   # real (non-padding) positions: needed by MoE balance loss
    for i, r in enumerate(records):
        p, o = (tok.encode(s) for s in render(r))
        seq = (p + o + [tok.eos_id])[:max_len]
        ids[i, : len(seq)] = seq
        valid[i, : len(seq)] = True
        lo = len(p) if loss_on == "response" else 0
        mask[i, lo : len(seq)] = True  # padding is never a target; a real EOS is
    empty = np.where(mask.sum(1) == 0)[0]
    if drop_empty and len(empty):
        keep = np.setdiff1d(np.arange(len(records)), empty)
        ids, mask, valid = ids[keep], mask[keep], valid[keep]
    return {"input_ids": ids, "loss_mask": mask, "valid_mask": valid, "n_dropped_empty": np.asarray(len(empty), np.int64)}


def arrays_digest(arrays: Dict[str, np.ndarray]) -> str:
    h = hashlib.sha256()
    for k in sorted(arrays):
        h.update(k.encode()); h.update(str(arrays[k].shape).encode()); h.update(arrays[k].tobytes())
    return h.hexdigest()


def save_arrays(path: str, arrays: Dict[str, np.ndarray]) -> str:
    np.savez(path, **arrays)
    return arrays_digest(arrays)


def load_arrays(path: str) -> Tuple[Dict[str, np.ndarray], str]:
    z = np.load(path)
    arrays = {k: z[k] for k in z.files}
    return arrays, arrays_digest(arrays)


@functools.lru_cache(maxsize=8)
def _epoch_perm(n: int, seed: int, epoch: int) -> np.ndarray:
    return np.random.Generator(np.random.Philox(key=[seed, epoch])).permutation(n)


def batch_indices(n: int, batch_size: int, seed: int, step: int) -> np.ndarray:
    """Indices for global step `step` (1-based). Pure function of (n, batch_size, seed, step).

    A fresh permutation per epoch from a counter-based Philox generator keyed by (seed, epoch);
    Philox is integer arithmetic, so it is bit-identical on every CPU/OS.
    """
    start = (step - 1) * batch_size
    out = np.empty(batch_size, np.int64)
    for j in range(batch_size):
        g = start + j
        epoch, pos = divmod(g, n)
        out[j] = _epoch_perm(n, seed, epoch)[pos]
    return out


def batch_for_step(arrays: Dict[str, np.ndarray], batch_size: int, seed: int, step: int):
    idx = batch_indices(len(arrays["input_ids"]), batch_size, seed, step)
    assert arrays["loss_mask"][idx].any(axis=1).all(), "batch contains an example with no target tokens"
    return arrays["input_ids"][idx], arrays["loss_mask"][idx], arrays["valid_mask"][idx]
