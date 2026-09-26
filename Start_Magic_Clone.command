#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "======================================"
echo "Magic Clone Local - macOS Launcher"
echo "======================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install Python 3.10+ and retry."
  exit 1
fi

if [ -z "$HF_TOKEN" ]; then
  echo "HF_TOKEN is not set."
  echo "Set it and retry: export HF_TOKEN='hf_your_token_here'"
  exit 1
fi

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 magic_clone.py
