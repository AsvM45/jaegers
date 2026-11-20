#!/bin/sh
# Copy the control tower into a Hugging Face Space and push it, which builds and starts the app.
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

git clone "$SPACE" "$WORK/space"
# Mirror the app into the Space, leaving out what is built in the image, local-only, or a binary file
# (Spaces refuse binary files in a plain git push: screenshots, the challenge .docx).
rsync -a --delete --exclude ".git" \
  --exclude "node_modules" --exclude "desktop/" --exclude "models/" --exclude ".venv/" \
  --exclude "__pycache__" --exclude "*.pyc" --exclude "tower/ui/dist/" \
  --exclude "runs/.reset/" --exclude "runs/live/" --exclude "runs/screenshots/" --exclude "runs/blind100_seed2/" \
  --exclude "tower/channels/channels.json" --exclude "tower/channels/contacts.json" --exclude ".env" \
  --exclude "* [0-9].*" \
  --exclude "*.png" --exclude "*.jpg" --exclude "*.jpeg" --exclude "*.gif" --exclude "*.pdf" \
  --exclude "*.docx" --exclude "*.zip" --exclude "*.bin" --exclude "*.ico" --exclude "*.icns" \
  "$HERE/" "$WORK/space/"
# The Space's README carries its settings (Docker, port 7860).
cp "$HERE/deploy/huggingface/README.md" "$WORK/space/README.md"

cd "$WORK/space"
git add -A
if git diff --cached --quiet; then
  echo "Nothing changed since the last push."
  exit 0
fi
git commit -q -m "Deploy the control tower"
git push
echo "Pushed. The Space is building: open $SPACE to watch the build log."
