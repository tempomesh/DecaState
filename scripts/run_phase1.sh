#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
RESULT="benchmarks/results/phase1_native_state.json"
CACHE=".decastate/phase1/prompt-cache.safetensors"

echo "[1/4] Same-process native replay"
.venv/bin/python experiments/phase1_native_state.py same-process --result "$RESULT"

echo "[2/4] Process A: prefill, capture, serialize, exit"
.venv/bin/python experiments/phase1_native_state.py process-a --cache "$CACHE" --result "$RESULT"

echo "[3/4] Process B: load model, restore cache, continue"
.venv/bin/python experiments/phase1_native_state.py process-b --cache "$CACHE" --result "$RESULT"

echo "[4/5] Wrong fingerprint rejection"
if .venv/bin/python experiments/phase1_native_state.py process-b --cache "$CACHE" --result "$RESULT" --expected-model wrong-model >/tmp/decastate-fingerprint.log 2>&1; then
  echo "ERROR: wrong fingerprint was accepted" >&2
  exit 1
fi
grep -F "FINGERPRINT_REJECTED" /tmp/decastate-fingerprint.log >/dev/null

echo "[5/5] Results"
cat "$RESULT"
echo "PHASE 1 NATIVE REPLAY, PROCESS-DEATH RESTORE, PREFILL AVOIDANCE, AND FINGERPRINT GUARD: PASS"
