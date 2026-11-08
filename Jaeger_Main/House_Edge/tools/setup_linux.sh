#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .runtime/uv-linux
if [[ ! -x .runtime/uv-linux/uv ]]; then
  curl -fL --retry 2 https://github.com/astral-sh/uv/releases/download/0.13.7/uv-x86_64-unknown-linux-gnu.tar.gz -o .runtime/uv-linux.tar.gz
  tar -xzf .runtime/uv-linux.tar.gz --strip-components=1 -C .runtime/uv-linux
fi
runtime="${JAEGERS_LINUX_RUNTIME:-/tmp/jaegers-house-edge-runtime}"
mkdir -p "$runtime"
export UV_PYTHON_INSTALL_DIR="$runtime/python"
export UV_CACHE_DIR="$runtime/cache"
.runtime/uv-linux/uv python install 3.13.18 --no-bin
if [[ ! -x "$runtime/venv/bin/python" ]]; then
  .runtime/uv-linux/uv venv "$runtime/venv" --python 3.13.18
fi
.runtime/uv-linux/uv pip install --python "$runtime/venv/bin/python" -r requirements-research.txt
printf '%s\n' "$runtime/venv/bin/python" > .runtime/linux-python.txt
"$runtime/venv/bin/python" --version
