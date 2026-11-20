#!/usr/bin/env bash
# Publish web/ as a static Hugging Face Space (default: astroanand/redline).
# Needs `hf auth login` with write access. Symlinked fonts and samples are copied as real files.
set -euo pipefail

SPACE="${1:-astroanand/redline}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

rsync -aL --exclude '.DS_Store' "$ROOT/web/" "$STAGE/"
hf repos create "$SPACE" --repo-type space --space-sdk static --public --exist-ok
hf upload "$SPACE" "$STAGE" . --repo-type space \
  --commit-message "${COMMIT_MESSAGE:-Deploy Redline web app ($(git -C "$ROOT" rev-parse --short HEAD))}"
echo "https://huggingface.co/spaces/$SPACE"
