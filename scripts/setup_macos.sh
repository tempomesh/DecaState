#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -e '.[mlx,dev]'
echo "Setup complete. Existing Ollama models are not downloaded or modified."
