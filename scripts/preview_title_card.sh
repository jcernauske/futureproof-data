#!/usr/bin/env bash
# Open an HTML file in Chrome's chromeless app mode (no address bar, no
# tabs, no bookmarks). Defaults to the title card; pass a path to override.
#
#   ./scripts/preview_title_card.sh
#   ./scripts/preview_title_card.sh docs/video/kinetic/scene-1-planning.html
#
# Once the window is open, hit Cmd+Ctrl+F to fullscreen it.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PAGE="${1:-$REPO_ROOT/docs/video/kinetic/brand-reveal-v2.html}"

if [[ ! -f "$PAGE" ]]; then
  echo "ERROR: file not found: $PAGE" >&2
  exit 1
fi

# `open -na` forces a new instance so --app takes effect even if Chrome
# is already running. realpath ensures the file:// URL is absolute.
ABS_PAGE="$(cd "$(dirname "$PAGE")" && pwd)/$(basename "$PAGE")"

open -na "Google Chrome" --args \
  --app="file://$ABS_PAGE" \
  --window-size=1920,1080
