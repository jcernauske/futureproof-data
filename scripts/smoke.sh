#!/usr/bin/env bash
# FutureProof — post-install smoke check.
#
# Verifies the install actually works without starting the dev server:
#   • backend Python can import app.main and construct the FastAPI app
#   • frontend node_modules are present and the TS build is clean
#   • Ollama has gemma4:e4b pulled (when using the local-inference path)
#   • .env exists
#
# Exit 0 = ready to run. Run this after ./scripts/setup.sh.

set -euo pipefail

if [ -t 1 ] && [ "${TERM:-}" != "dumb" ]; then
  G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; X=$'\033[0m'
else
  G=""; R=""; Y=""; X=""
fi

ok()   { printf "  %s✓%s %s\n" "$G" "$X" "$1"; }
fail() { printf "  %s✗%s %s\n" "$R" "$X" "$1"; }
warn() { printf "  %s!%s %s\n" "$Y" "$X" "$1"; }

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# uv installs to $HOME/.local/bin by default but doesn't touch PATH for new
# shells. Probe that location so this script works without the user having
# to first edit their shell rc — setup.sh already warned about the PATH
# fix for new terminals.
if ! command -v uv >/dev/null 2>&1 && [ -x "$HOME/.local/bin/uv" ]; then
  export PATH="$HOME/.local/bin:$PATH"
fi

failures=0

# --- .env ------------------------------------------------------------------

if [ -f .env ]; then
  ok ".env exists"
  inference_backend=$(awk -F= '/^INFERENCE_BACKEND=/ { print $2 }' .env | tr -d '[:space:]')
else
  fail ".env missing — run ./scripts/setup.sh"
  failures=$((failures + 1))
  inference_backend=""
fi

# --- Backend ---------------------------------------------------------------

if [ -d backend/.venv ]; then
  ok "backend/.venv exists"
else
  fail "backend/.venv missing — run ./scripts/setup.sh"
  failures=$((failures + 1))
fi

backend_import_log=$(mktemp)
if (cd backend && uv run python -c "from app.main import create_app; create_app()") >"$backend_import_log" 2>&1; then
  ok "Backend imports cleanly (FastAPI app constructs)"
  rm -f "$backend_import_log"
else
  fail "Backend import failed — error below:"
  sed 's/^/      /' "$backend_import_log"
  rm -f "$backend_import_log"
  failures=$((failures + 1))
fi

# --- Frontend --------------------------------------------------------------

if [ -d frontend/node_modules ]; then
  ok "frontend/node_modules exists"
else
  fail "frontend/node_modules missing — run ./scripts/setup.sh"
  failures=$((failures + 1))
fi

if (cd frontend && npx --no-install tsc --noEmit >/dev/null 2>&1); then
  ok "Frontend TypeScript check clean"
else
  fail "Frontend TypeScript check failed — try (cd frontend && npx tsc --noEmit)"
  failures=$((failures + 1))
fi

# --- Ollama (only when INFERENCE_BACKEND=ollama or unset) ------------------

if [ -z "$inference_backend" ] || [ "$inference_backend" = "ollama" ]; then
  daemon_up=0
  if curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
    daemon_up=1
    ok "Ollama daemon reachable"
  fi

  # Always try `ollama list` — it can succeed even when our curl probe
  # doesn't (different port, IPv6-only bind, etc.), so we can still report
  # the more actionable "model not pulled" message instead of a misleading
  # "daemon not reachable" warning.
  if ollama_models=$(ollama list 2>/dev/null) && [ -n "$ollama_models" ]; then
    if echo "$ollama_models" | awk 'NR>1 {print $1}' | grep -q '^gemma4:e4b$'; then
      ok "gemma4:e4b is pulled"
    else
      fail "gemma4:e4b not pulled — run 'ollama pull gemma4:e4b'"
      failures=$((failures + 1))
    fi
  elif [ "$daemon_up" -eq 0 ]; then
    warn "Ollama not responding on localhost:11434 — open the Ollama app (or run 'ollama serve'), then 'ollama pull gemma4:e4b' if you haven't yet."
  fi
elif [ "$inference_backend" = "openrouter" ]; then
  if grep -qE '^OPENROUTER_API_KEY=sk-or-' .env; then
    ok "OPENROUTER_API_KEY is set (openrouter path)"
  else
    fail "INFERENCE_BACKEND=openrouter but OPENROUTER_API_KEY is missing or unset in .env"
    failures=$((failures + 1))
  fi
fi

# --- Done ------------------------------------------------------------------

echo ""
if [ "$failures" -eq 0 ]; then
  printf "%sAll checks passed.%s Run %s./scripts/dev.sh%s to start the app.\n" "$G" "$X" "$G" "$X"
else
  printf "%s%d check(s) failed.%s Fix the issues above and re-run.\n" "$R" "$failures" "$X"
  exit 1
fi
