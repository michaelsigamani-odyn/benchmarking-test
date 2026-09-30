import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def pytest_configure(config):
    out = os.path.join(ROOT, "data", "story3_bytes256.npz")
    if not os.path.exists(out):  # derived artifact; regenerate deterministically
        subprocess.run([sys.executable, os.path.join(ROOT, "prepare_data.py"), "--jsonl", os.path.join(ROOT, "data", "story3_dataset.jsonl"),
                        "--out", out, "--tokenizer", "byte", "--max-len", "256"], check=True, cwd=ROOT, capture_output=True)
