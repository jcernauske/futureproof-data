# Hotfix: Switch Batch Scorer to Use gemma_client.py Pattern (OpenRouter)

## Claude Code Prompt

```
Modify scripts/gemma_ai_exposure_scorer.py to use the existing gemma_client.py infrastructure pattern instead of raw Ollama HTTP calls.

The project already has a unified inference client at backend/app/services/gemma_client.py that reads INFERENCE_BACKEND from .env and supports both Ollama and OpenRouter via the OpenAI SDK. Use this same pattern.

Changes required:

1. Add python-dotenv loading at startup:
   ```python
   from dotenv import load_dotenv
   load_dotenv(_REPO_ROOT / ".env")
   ```

2. Read backend config from env vars (same pattern as gemma_client.py):
   - INFERENCE_BACKEND: "ollama" or "openrouter" (default: "openrouter" for this script)
   - OPENROUTER_API_KEY: required when INFERENCE_BACKEND=openrouter
   - OPENROUTER_MODEL: default "google/gemma-4-26b-a4b-it"
   - OLLAMA_HOST, OLLAMA_MODEL: keep as fallback

3. Replace _call_ollama() with _call_inference() that:
   - If INFERENCE_BACKEND=openrouter: use OpenAI SDK pointed at https://openrouter.ai/api/v1
   - If INFERENCE_BACKEND=ollama: keep existing Ollama HTTP logic
   - Use OpenAI chat completions format for OpenRouter:
     ```python
     from openai import OpenAI
     
     client = OpenAI(
         base_url="https://openrouter.ai/api/v1",
         api_key=os.getenv("OPENROUTER_API_KEY"),
     )
     response = client.chat.completions.create(
         model="google/gemma-4-26b-a4b-it",
         messages=[{"role": "user", "content": prompt}],
         temperature=0,
         max_tokens=512,
         response_format={"type": "json_object"},
     )
     text = response.choices[0].message.content
     ```

4. Update model_tag in output to reflect the actual model used:
   - OpenRouter: "google/gemma-4-26b-a4b-it"
   - Ollama: "gemma4:26b-a4b" (existing)

5. Error handling:
   - At startup: if INFERENCE_BACKEND=openrouter and OPENROUTER_API_KEY missing, exit with clear message
   - Handle rate limit (429) with exponential backoff in retry loop
   - Keep the 3-retry loop structure

6. Update docstring to note both backends are supported via INFERENCE_BACKEND env var

After modifying, run:
- ruff check scripts/gemma_ai_exposure_scorer.py --fix
- Verify no syntax errors: python -m py_compile scripts/gemma_ai_exposure_scorer.py

Do NOT run the actual batch yet — just update the code and verify it compiles.
```

## .env Setup (add/verify these vars in ~/code/bright/futureproof-data/.env)

```bash
# Switch to OpenRouter for batch scoring
INFERENCE_BACKEND=openrouter

# Your OpenRouter API key
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Model (optional, defaults to google/gemma-4-26b-a4b-it)
OPENROUTER_MODEL=google/gemma-4-26b-a4b-it
```

## Run Command (after code is updated and .env is set)

```bash
cd ~/code/bright/futureproof-data
uv run python scripts/gemma_ai_exposure_scorer.py
```

## Expected Behavior

- Script reads `INFERENCE_BACKEND=openrouter` from `.env`
- Uses OpenAI SDK pointed at OpenRouter
- model_tag in output shows `google/gemma-4-26b-a4b-it`
- Same checkpointing, retry logic, and output format as before
- Runtime: ~10-15 min (vs 1-2 hr for local Ollama)
- Cost: ~$0.21 for all 798 occupations

## Reference

See `backend/app/services/gemma_client.py` for the existing inference client pattern. The batch scorer should follow the same `.env` conventions:
- INFERENCE_BACKEND
- OPENROUTER_API_KEY
- OPENROUTER_MODEL
- OLLAMA_HOST
- OLLAMA_MODEL
