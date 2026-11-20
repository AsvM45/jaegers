#!/bin/sh
# Start Ollama (when this image has it and RUN_OLLAMA=1), wait until it answers, then the dashboard server.
set -e
if [ "${RUN_OLLAMA:-1}" = "1" ] && command -v ollama >/dev/null 2>&1; then
  OLLAMA_HOST=127.0.0.1:11434 ollama serve >/tmp/ollama.log 2>&1 &
  i=0
  while [ $i -lt 60 ]; do
    curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    i=$((i + 1)); sleep 1
  done
  echo "ollama ready after ${i}s"
fi
exec python3 -m tower.ui.server --host "${TOWER_HOST:-0.0.0.0}" --port "${PORT:-7860}"
