#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "DECASTATE — THE AI STATE RUNTIME"
echo "Real repository context → checkpoint → wake → coder/reviewer/security forks"
echo
.venv/bin/python experiments/06_coding_agent_demo.py
echo
echo "PUBLIC CLAIM BOUNDARY"
echo "Verified: native MLX save/wake, checkpoint/rollback, physical-copy fork."
echo "Not claimed: COW savings, cross-runtime migration, cross-model portability."
