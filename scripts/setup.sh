#!/usr/bin/env bash
# FutureProof — one-shot install + prereq check.
#
# Verifies prerequisites (Node, Python, uv, Ollama) then installs the
# pipeline, backend, and frontend dependencies. Pulls gemma4:e4b. Copies
# .env from the template if missing. Exit 0 means you're ready to run
# ./scripts/dev.sh.

set -euo pipefail

# Color codes — degrade gracefully on terminals without color support.
if [ -t 1 ] && [ "${TERM:-}" != "dumb" ]; then
  G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; B=$'\033[1m'; X=$'\033[0m'
else
  G=""; R=""; Y=""; B=""; X=""
fi

ok()    { printf "  %s✓%s %s\n" "$G" "$X" "$1"; }
fail()  { printf "  %s✗%s %s\n" "$R" "$X" "$1"; }
warn()  { printf "  %s!%s %s\n" "$Y" "$X" "$1"; }
step()  { printf "\n%s%s%s\n" "$B" "$1" "$X"; }

# Resolve repo root from this script's location.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

failures=0

# --- Prereqs ---------------------------------------------------------------

step "Checking prerequisites"

if command -v node >/dev/null 2>&1; then
  node_version=$(node --version | sed 's/v//' | cut -d. -f1)
  if [ "$node_version" -ge 20 ]; then
    ok "Node $(node --version)"
  else
    fail "Node $(node --version) is too old (need ≥20)"
    failures=$((failures + 1))
  fi
else
  fail "Node not found — install Node 20+ (https://nodejs.org)"
  failures=$((failures + 1))
fi

if command -v python3 >/dev/null 2>&1; then
  py_major=$(python3 -c 'import sys; print(sys.version_info[0])')
  py_minor=$(python3 -c 'import sys; print(sys.version_info[1])')
  if [ "$py_major" -ge 3 ] && [ "$py_minor" -ge 11 ]; then
    ok "Python $(python3 --version | awk '{print $2}')"
  else
    fail "Python $(python3 --version | awk '{print $2}') is too old (need ≥3.11)"
    failures=$((failures + 1))
  fi
else
  fail "Python 3 not found — install Python 3.11+ (https://www.python.org)"
  failures=$((failures + 1))
fi

if command -v uv >/dev/null 2>&1; then
  ok "uv $(uv --version | awk '{print $2}')"
else
  fail "uv not found — install via 'curl -LsSf https://astral.sh/uv/install.sh | sh'"
  failures=$((failures + 1))
fi

if command -v ollama >/dev/null 2>&1; then
  ok "Ollama $(ollama --version 2>&1 | head -1 | awk '{print $NF}')"
  if curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
    ok "Ollama daemon reachable at localhost:11434"
  else
    warn "Ollama is installed but the daemon isn't running — start it before continuing"
  fi
else
  warn "Ollama not found — install from https://ollama.com (only needed for the local-inference path)"
fi

if [ "$failures" -gt 0 ]; then
  printf "\n%s%d prerequisite check(s) failed.%s Install the missing tools and re-run.\n" "$R" "$failures" "$X"
  exit 1
fi

# --- Pipeline deps ---------------------------------------------------------

step "Installing pipeline deps (uv sync)"
uv sync
ok "Pipeline deps installed"

# --- Backend deps ----------------------------------------------------------

step "Installing backend deps (uv sync --extra dev)"
(cd backend && uv sync --extra dev)
ok "Backend deps installed"

# --- Frontend deps ---------------------------------------------------------

step "Installing frontend deps (npm install)"
(cd frontend && npm install --silent)
ok "Frontend deps installed"

# --- .env ------------------------------------------------------------------

step "Configuring environment"
if [ -f .env ]; then
  ok ".env already exists — leaving it alone"
else
  cp docs/env-template.txt .env
  ok ".env created from docs/env-template.txt (defaults to Ollama + gemma4:e4b)"
fi

# --- Gemma model -----------------------------------------------------------

step "Pulling Gemma 4 model (gemma4:e4b)"
if command -v ollama >/dev/null 2>&1 && curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -q '^gemma4:e4b$'; then
    ok "gemma4:e4b already pulled"
  else
    ollama pull gemma4:e4b
    ok "gemma4:e4b pulled"
  fi
else
  warn "Skipping ollama pull — Ollama daemon not reachable. Run 'ollama pull gemma4:e4b' manually."
fi

# --- Done ------------------------------------------------------------------

printf "\n%sSetup complete.%s Next:\n" "$B" "$X"
printf "  • Start the app:      %s./scripts/dev.sh%s\n" "$B" "$X"
printf "  • Verify the install: %s./scripts/smoke.sh%s\n" "$B" "$X"
