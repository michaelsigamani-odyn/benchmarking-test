"""Tokenize once, on one machine, and ship the resulting .npz to every host.

Tokenization is done once so all hosts train on byte-identical token ids (a tokenizers/transformers
version difference between vendors' hosts cannot change the data). The npz digest is part of the
run identity.
"""
import argparse, json
from jaxft.data import ByteTokenizer, HFTokenizer, build_arrays, read_jsonl, save_arrays

p = argparse.ArgumentParser()
p.add_argument("--jsonl", required=True)
p.add_argument("--out", required=True)
p.add_argument("--tokenizer", default="byte", help="'byte' (no network; tests) or an HF name/path e.g. Qwen/Qwen2.5-1.5B")
p.add_argument("--max-len", type=int, default=128)
p.add_argument("--loss-on", choices=["response", "all"], default="response")
a = p.parse_args()
tok = ByteTokenizer() if a.tokenizer == "byte" else HFTokenizer(a.tokenizer)
arrays = build_arrays(read_jsonl(a.jsonl), tok, a.max_len, a.loss_on)
digest = save_arrays(a.out, arrays)
print(json.dumps({"out": a.out, "examples_kept": int(arrays["input_ids"].shape[0]), "dropped_no_target_after_truncation": int(arrays["n_dropped_empty"]), "max_len": a.max_len,
                  "target_tokens": int(arrays["loss_mask"].sum()), "vocab_size": tok.vocab_size, "digest": digest}, indent=2))
