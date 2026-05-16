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

# uv installs to $HOME/.local/bin by default but doesn't touch PATH for new
# shells. Probe that location so this script works without the user having
# to first edit their shell rc — setup.sh already warned about the PATH
# fix for new terminals.
if ! command -v uv >/dev/null 2>&1 && [ -x "$HOME/.local/bin/uv" ]; then
  export PATH="$HOME/.local/bin:$PATH"
fi

if [ ! -d backend/.venv ]; then
  echo "Backend deps not installed. Run ./scripts/setup.sh first." >&2
  exit 1
fi
if [ ! -d frontend/node_modules ]; then
  echo "Frontend deps not installed. Run ./scripts/setup.sh first." >&2
  exit 1
fi

# Inference pre-flight — non-fatal. Without this, the UI starts but reports
# "offline" with no obvious cause, sending users hunting through logs.
if [ -t 1 ] && [ "${TERM:-}" != "dumb" ]; then
  WARN=$'\033[33m'; X_WARN=$'\033[0m'
else
  WARN=""; X_WARN=""
fi
inference_backend="ollama"
if [ -f .env ]; then
  inference_backend=$(awk -F= '/^INFERENCE_BACKEND=/ { print $2 }' .env | tr -d '[:space:]')
  [ -z "$inference_backend" ] && inference_backend="ollama"
fi
if [ "$inference_backend" = "ollama" ]; then
  # Prefer `ollama list` for diagnosing because it can succeed even when
  # our curl probe doesn't, letting us report the more actionable "model
  # not pulled" hint instead of a misleading "daemon not reachable" one.
  if ollama_models=$(ollama list 2>/dev/null) && [ -n "$ollama_models" ]; then
    if ! echo "$ollama_models" | awk 'NR>1 {print $1}' | grep -q '^gemma4:e4b$'; then
      printf "%s! gemma4:e4b not pulled — the UI will load but show 'offline'. Run: ollama pull gemma4:e4b%s\n" "$WARN" "$X_WARN" >&2
    fi
  elif ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
    printf "%s! Ollama not responding on localhost:11434 — the UI will load but show 'offline'. Open the Ollama app (or 'ollama serve'), then 'ollama pull gemma4:e4b' if you haven't yet.%s\n" "$WARN" "$X_WARN" >&2
  fi
elif [ "$inference_backend" = "openrouter" ]; then
  if ! grep -qE '^OPENROUTER_API_KEY=sk-or-' .env 2>/dev/null; then
    printf "%s! INFERENCE_BACKEND=openrouter but OPENROUTER_API_KEY is missing/unset in .env — the UI will show 'offline'.%s\n" "$WARN" "$X_WARN" >&2
  fi
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
  # (uvicorn, vite, their workers) terminate too. READY_PID may not exist
  # yet if cleanup fires before we reach the poller.
  kill -TERM "$BE_PID" "$FE_PID" ${READY_PID:+"$READY_PID"} 2>/dev/null || true
  wait 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173 (booting...)"
echo "Ctrl-C to stop both."
echo ""

# Poll the frontend in the background; once vite is serving, print a
# prominent banner so the "open this URL" line lands AFTER the noisy
# startup logs instead of being scrolled off-screen by them.
(
  if [ -t 1 ] && [ "${TERM:-}" != "dumb" ]; then
    BOLD=$'\033[1m'; GREEN=$'\033[32m'; RESET=$'\033[0m'
  else
    BOLD=""; GREEN=""; RESET=""
  fi
  for _ in $(seq 1 60); do
    if curl -fsS http://localhost:5173 >/dev/null 2>&1; then
      printf "\n%s%s→ OPEN: http://localhost:5173%s  (frontend is ready)\n\n" "$BOLD" "$GREEN" "$RESET"
      exit 0
    fi
    sleep 1
  done
) &
READY_PID=$!

wait "$BE_PID" "$FE_PID"
