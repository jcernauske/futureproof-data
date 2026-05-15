#!/usr/bin/env bash
# FutureProof — start backend + frontend together with interleaved logs.
#
# Replaces the "open two terminals" instruction. Ctrl-C kills both.

set -euo pipefail

if [ -t 1 ] && [ "${TERM:-}" != "dumb" ]; then
  BE_COLOR=$'\033[36m'   # cyan
  FE_COLOR=$'\033[35m'   # magenta
  X=$'\033[0m'
else
  BE_COLOR=""; FE_COLOR=""; X=""
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d backend/.venv ]; then
  echo "Backend deps not installed. Run ./scripts/setup.sh first." >&2
  exit 1
fi
if [ ! -d frontend/node_modules ]; then
  echo "Frontend deps not installed. Run ./scripts/setup.sh first." >&2
  exit 1
fi

prefix() {
  local color="$1"
  local tag="$2"
  while IFS= read -r line; do
    printf "%s[%s]%s %s\n" "$color" "$tag" "$X" "$line"
  done
}

# Start backend.
(
  cd backend
  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1
) | prefix "$BE_COLOR" "BE" &
BE_PID=$!

# Start frontend.
(
  cd frontend
  npm run dev 2>&1
) | prefix "$FE_COLOR" "FE" &
FE_PID=$!

cleanup() {
  echo ""
  echo "Shutting down..."
  # Kill the whole process group for each pipeline so child processes
  # (uvicorn, vite, their workers) terminate too.
  kill -TERM "$BE_PID" "$FE_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Ctrl-C to stop both."
echo ""

wait
