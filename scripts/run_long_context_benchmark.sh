#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python experiments/03_long_context_resume.py
