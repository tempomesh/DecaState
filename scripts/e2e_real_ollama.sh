#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${DECASTATE_MODEL:-qwen2.5:14b}"
STATE_DIR="$(mktemp -d /tmp/decastate-e2e.XXXXXX).dstate"
trap 'rm -rf "$STATE_DIR"' EXIT

echo "[1/5] Checking existing Ollama model: $MODEL"
ollama list | grep -F "$MODEL" >/dev/null

echo "[2/5] Running real model inference"
OUTPUT="$(.venv/bin/decastate run 'Reply with exactly: DECASTATE_E2E_OK' --model "$MODEL")"
echo "$OUTPUT" | grep -F "DECASTATE_E2E_OK" >/dev/null

echo "[3/5] Creating metadata capsule"
.venv/bin/decastate save "$STATE_DIR" --model "$MODEL" >/dev/null

echo "[4/5] Verifying capsule is explicit about restore capability"
.venv/bin/decastate inspect "$STATE_DIR" | grep -F '"supported": false' >/dev/null

echo "[5/5] Verifying unsafe wake is rejected"
if .venv/bin/decastate wake "$STATE_DIR" >/dev/null 2>&1; then
  echo "ERROR: unsupported wake unexpectedly succeeded" >&2
  exit 1
fi

echo "E2E PASS: real Ollama inference completed; unsupported native restore was rejected."
