#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash tools/setup_linux.sh
runtime="${JAEGERS_LINUX_RUNTIME:-/var/tmp/jaegers-house-edge-runtime}"
export UV_PYTHON_INSTALL_DIR="$runtime/python"
export UV_CACHE_DIR="$runtime/cache"
if [[ ! -x "$runtime/release-venv/bin/python" ]]; then
  .runtime/uv-linux/uv venv "$runtime/release-venv" --python 3.13.18
fi
.runtime/uv-linux/uv pip install --python "$runtime/release-venv/bin/python" -r requirements-runtime.txt
bash tools/run_linux.sh -B -m research.offline "$@" --prediction-python "$runtime/release-venv/bin/python"
