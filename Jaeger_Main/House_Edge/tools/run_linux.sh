#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python_exe="$(cat .runtime/linux-python.txt)"
exec "$python_exe" "$@"
