#!/usr/bin/env bash
# Publish web/ as a static Hugging Face Space (default: astroanand/redline).
# Needs `hf auth login` with write access. Symlinked fonts and samples are copied as real files.
set -euo pipefail

SPACE="${1:-astroanand/redline}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# -L copies what the symlinks point at; hidden files (caches, .DS_Store) stay local.
rsync -aL --exclude '.*' "$ROOT/web/" "$STAGE/"
hf repos create "$SPACE" --repo-type space --space-sdk static --public --exist-ok
# --delete '*' mirrors web/ exactly: stale files go (the Hub always keeps .gitattributes).
hf upload "$SPACE" "$STAGE" . --repo-type space --delete '*' \
  --commit-message "${COMMIT_MESSAGE:-Deploy Redline web app ($(git -C "$ROOT" rev-parse --short HEAD))}"
echo "https://huggingface.co/spaces/$SPACE"
