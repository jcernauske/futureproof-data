.PHONY: setup dev smoke test eval-p0 eval-p1 eval-all eval-latency eval-test eval-p0-no-rubric

# One-shot install + prereq check. See scripts/setup.sh.
setup:
	./scripts/setup.sh

# Start backend + frontend together with interleaved logs.
dev:
	./scripts/dev.sh

# Post-install smoke check — verify the install actually works.
smoke:
	./scripts/smoke.sh

# Full test suite: backend lint + types + pytest, frontend types + vitest.
test:
	cd backend && uv run ruff check . && uv run mypy app/ && uv run pytest
	cd frontend && npx tsc --noEmit && npx vitest run

# eval/ is at repo root and imports backend's app package, which is
# installed editable via `cd backend && uv sync --extra dev`. Run all
# eval commands from the repo root so `python -m eval.runner` resolves.

# Run P0 surfaces against golden cases. Requires:
#   - Gemma backend reachable (Ollama running or OPENROUTER_API_KEY set)
#   - ANTHROPIC_API_KEY set if rubric scoring is enabled (omit --no-rubric)
eval-p0:
	python -m eval.runner --tier P0

eval-p1:
	python -m eval.runner --tier P1

eval-all:
	python -m eval.runner --tier P0
	python -m eval.runner --tier P1
	python -m eval.runner --tier P2

# Aggregate latency from logs/gemma.jsonl for all 20 surfaces. No adapter runs.
# Free, fast — runs on existing production log without spending tokens.
eval-latency:
	python -m eval.runner --latency-only

# Run scorer/adapter unit tests (no live LLM calls)
eval-test:
	pytest eval/tests -v

# P0 without rubric scoring — useful when you don't want to spend Anthropic API tokens
eval-p0-no-rubric:
	python -m eval.runner --tier P0 --no-rubric
