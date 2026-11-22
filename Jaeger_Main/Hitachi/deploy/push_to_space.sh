#!/bin/sh
# Copy the control tower into a Hugging Face Space and push it, which builds and starts the app.
# The Space is the free Gradio type: it runs app.py (deploy/space/app.py), which loads the AI model and
# starts the dashboard. The dashboard is built here first, since that Space type has no Node.
#
#   deploy/push_to_space.sh https://huggingface.co/spaces/<your-user>/<space-name>
#
# git asks for a user name and password: your Hugging Face user name, and an access token with
# "write" permission (huggingface.co/settings/tokens) as the password.
set -e
SPACE="$1"
if [ -z "$SPACE" ]; then
  echo "usage: deploy/push_to_space.sh https://huggingface.co/spaces/<your-user>/<space-name>" >&2
  exit 1
fi
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "Building the dashboard…"
(cd "$HERE/tower/ui/web" && { [ -d node_modules ] || npm ci --no-audit --no-fund; } && npm run build >/dev/null)

git clone "$SPACE" "$WORK/space"
# Mirror the app into the Space, leaving out what is built in the image, local-only, or a binary file
# (Spaces refuse binary files in a plain git push: screenshots, the challenge .docx).
# The Space starts fresh and shows only the demo's given tests: of runs/ only the ontology export goes,
# and the blind test sets, their tools, the saved runs and the design notes stay on this computer.
# Start from an empty folder (keeping only the Space's git history), so a file left out here is also
# removed from the Space if an earlier push sent it.
find "$WORK/space" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
rsync -a --delete --exclude ".git" \
  --include "runs/" --include "runs/ontology/***" --exclude "runs/*" \
  --include "deploy/" --include "deploy/space/***" --exclude "deploy/*" \
  --exclude "tests/blind*" --exclude "tests/make_blind.py" --exclude "tests/run_blind.py" \
  --exclude "tests/run_model*.py" --exclude "tests/expected_graphs*.json" --exclude "tests/test_failures*.py" \
  --exclude "DESIGN_CARD.md" \
  --exclude "node_modules" --exclude "desktop/" --exclude "models/" --exclude ".venv/" \
  --exclude "__pycache__" --exclude "*.pyc" --exclude "Dockerfile*" --exclude ".dockerignore" \
  --exclude "runs/.reset/" --exclude "runs/live/" --exclude "runs/ws/" --exclude "runs/screenshots/" --exclude "runs/blind100_seed2/" \
  --exclude "tower/channels/channels.json" --exclude "tower/channels/contacts.json" --exclude ".env" \
  --exclude "* [0-9].*" \
  --exclude "*.png" --exclude "*.jpg" --exclude "*.jpeg" --exclude "*.gif" --exclude "*.pdf" \
  --exclude "*.docx" --exclude "*.zip" --exclude "*.bin" --exclude "*.ico" --exclude "*.icns" \
  "$HERE/" "$WORK/space/"
# The Space's README carries its settings; app.py and requirements.txt go at the top.
cp "$HERE/deploy/huggingface/README.md" "$WORK/space/README.md"
cp "$HERE/deploy/space/app.py" "$HERE/deploy/space/requirements.txt" "$WORK/space/"

cd "$WORK/space"
git add -A
if git diff --cached --quiet; then
  echo "Nothing changed since the last push."
  exit 0
fi
git commit -q -m "Deploy the control tower"
git push
echo "Pushed. The Space is building: open $SPACE to watch the build log."
