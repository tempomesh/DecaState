#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
echo "[1/7] Package and CLI"
.venv/bin/python -m pip install -e . >/dev/null
.venv/bin/decastate doctor >/tmp/decastate-production-doctor.txt
echo "[2/7] Unit tests"
.venv/bin/python -m pytest -q
echo "[3/7] Native save/wake"
make phase1 >/tmp/decastate-production-phase1.txt
grep -F "PHASE 1 NATIVE REPLAY" /tmp/decastate-production-phase1.txt >/dev/null
echo "[4/7] Long-context benchmark"
make bench-long >/tmp/decastate-production-long.txt
echo "[5/7] Checkpoint/rollback"
make checkpoint >/tmp/decastate-production-checkpoint.txt
grep -F "CHECKPOINT / ROLLBACK GATE: PASS" /tmp/decastate-production-checkpoint.txt >/dev/null
echo "[6/7] Fork and public demo"
make fork >/tmp/decastate-production-fork.txt
grep -F "FORK CORRECTNESS GATE: PASS" /tmp/decastate-production-fork.txt >/dev/null
make public-demo >/tmp/decastate-production-demo.txt
grep -F "CODING AGENT DEMO: PASS" /tmp/decastate-production-demo.txt >/dev/null
echo "[7/7] Ollama compatibility boundary"
make e2e >/tmp/decastate-production-ollama.txt
grep -F "E2E PASS" /tmp/decastate-production-ollama.txt >/dev/null
echo "PRODUCTION MVP CHECK: PASS"
