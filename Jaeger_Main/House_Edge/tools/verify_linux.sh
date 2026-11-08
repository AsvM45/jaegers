#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash tools/setup_linux.sh
bash tools/run_linux.sh -B -m research.offline "$@"
