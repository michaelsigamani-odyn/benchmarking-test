#!/usr/bin/env bash
set -euo pipefail

source ~/.bashrc >/dev/null 2>&1 || true

python3 scripts/vast_offers_snapshot_v2.py "$@"
