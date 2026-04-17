# Cloud Gemma Deployment — Setup Spec

*FutureProof inference backend via OpenRouter*

**Owner:** Jeff
**Priority:** High — needed before frontend integration
**Time estimate:** ~15 minutes to be live

---

## Strategy

Two inference backends, one OpenAI-compatible interface. Your FastAPI backend abstracts this behind a config switch.

| Backend | Use Case | Cost |
|---|---|---|
| **Ollama local** | Dev, testing, Ollama track video, Tier 3 demo | $0 |
| **OpenRouter (this spec)** | Live demo for judges, deployed URL, dev when local GPU isn't available | ~$0.12/M input tokens |

**Model choice:** Gemma 4 26B MoE (`google/gemma-4-26b-a4b-it`). Activates only 3.8B params per token — faster and cheaper than the 31B dense, benchmarks within ~1 point on reasoning. Native function calling and 256K context window. If output quality is insufficient, swap to the 31B dense (`google/gemma-4-31b-it`) at $0.14/M input — one line config change.

**Why OpenRouter works for the hackathon:**

- OpenAI-compatible API — identical interface to Ollama's `/v1/chat/completions`, so your FastAPI backend doesn't care which one it's talking to
- No infrastructure to manage. No GPU quota to request. No cold starts.
- Cost is negligible. A full career guidance query (system prompt + tool calls + synthesis) is maybe 3-5K tokens round trip. At $0.12/M input + $0.40/M output, that's ~$0.002 per query. The entire hackathon demo could cost $1.
- Free tier exists for dev/testing (rate limited: 20 req/min, 200 req/day)
- Both the 26B MoE and 31B have free-tier variants with 32K max output cap — sufficient for FutureProof queries

**What you lose vs. self-hosted:** You can't say "we're running this on our own GPU in the cloud" in the writeup. But that was never a judging criterion — the Ollama track prize cares about local deployment, and the Main Track cares about the product working. The live demo URL just needs to work. Judges don't care how inference happens behind it.

---

## Setup

### Step 1: Create OpenRouter account

1. Go to https://openrouter.ai
2. Sign up (Google auth or email)
3. Go to **Keys** → **Create Key**
4. Name it `futureproof-hackathon`
5. Copy the key — you'll need it for your FastAPI config

### Step 2: Add credits (optional — free tier works for dev)

For guaranteed availability during the live demo:

1. Go to **Credits** → **Add Credits**
2. Add $5. This covers thousands of queries. You will not run out.

For dev and testing, skip this — the free tier models work fine.

### Step 3: Verify function calling works

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "model": "google/gemma-4-26b-a4b-it",
  "messages": [
    {"role": "user", "content": "Look up career outcomes for Indiana State University business administration graduates."}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_school_data",
        "description": "Get College Scorecard data for a specific school",
        "parameters": {
          "type": "object",
          "properties": {
            "school_name": {
              "type": "string",
              "description": "Name of the school"
            }
          },
          "required": ["school_name"]
        }
      }
    }
  ],
  "max_tokens": 512
}'
```

If the response includes a `tool_calls` array with `get_school_data`, you're good.

### Step 4: Test with the free tier model (optional)

For dev/testing without spending credits:

```bash
# Same API, just swap the model string — adds ":free" suffix
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "model": "google/gemma-4-26b-a4b-it:free",
  "messages": [
    {"role": "user", "content": "What are the top career paths for a finance major?"}
  ],
  "max_tokens": 256
}'
```

Free tier is rate limited (20 req/min, 200/day) and output capped at 32K tokens. Fine for dev, not for the live demo.

---

## FastAPI Backend Integration

### .env file

Add to your project root `.env` (this file is gitignored — never commit API keys):

```bash
# ~/code/future_proof/.env

# Inference backend: "ollama" or "openrouter"
INFERENCE_BACKEND=ollama

# OpenRouter API key (only needed when INFERENCE_BACKEND=openrouter)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
```

Make sure `.env` is in your `.gitignore`:

```bash
echo ".env" >> ~/code/future_proof/.gitignore
```

### Config

```python
# config.py
import os
from dotenv import load_dotenv
from enum import Enum

load_dotenv()  # Reads from .env in project root

class InferenceBackend(str, Enum):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"

INFERENCE_CONFIG = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",  # Ollama ignores this but the SDK requires a value
        "model": "gemma4:26b-a4b",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "model": "google/gemma-4-26b-a4b-it",
    },
}

def get_inference_config():
    backend = os.getenv("INFERENCE_BACKEND", "ollama")
    return INFERENCE_CONFIG[backend]
```

Requires `python-dotenv` — add to your requirements if not already present:

```bash
pip install python-dotenv
```

### Inference client

```python
# inference.py
from openai import OpenAI
from config import get_inference_config

config = get_inference_config()

client = OpenAI(
    base_url=config["base_url"],
    api_key=config["api_key"],
)

def call_gemma(messages, tools=None):
    """Unified inference call — works identically across both backends."""
    kwargs = {
        "model": config["model"],
        "messages": messages,
        "max_tokens": 2048,
    }
    if tools:
        kwargs["tools"] = tools
    return client.chat.completions.create(**kwargs)
```

### Switching backends

Edit `INFERENCE_BACKEND` in your `.env` file:

```bash
# Local dev — Ollama
INFERENCE_BACKEND=ollama

# Live demo — OpenRouter
INFERENCE_BACKEND=openrouter
```

Or override at launch without editing the file:

```bash
INFERENCE_BACKEND=openrouter uvicorn app:main
```

### OpenRouter-specific headers (optional)

OpenRouter supports optional headers for leaderboard attribution. Not required, but nice for visibility:

```python
# Add to your OpenAI client for OpenRouter only
client = OpenAI(
    base_url=config["base_url"],
    api_key=config["api_key"],
    default_headers={
        "HTTP-Referer": "https://futureproof.app",  # Your deployed URL
        "X-Title": "FutureProof",
    }
)
```

---

## Model Options & Pricing

| Model | Input | Output | Context | Notes |
|---|---|---|---|---|
| `google/gemma-4-26b-a4b-it` | $0.12/M | $0.40/M | 256K | **Primary.** MoE, 3.8B active params. Fast. |
| `google/gemma-4-31b-it` | $0.14/M | $0.40/M | 256K | Dense. Slightly better quality, slightly slower. |
| `google/gemma-4-26b-a4b-it:free` | $0 | $0 | 256K | Rate limited. 32K max output. Dev/testing. |
| `google/gemma-4-31b-it:free` | $0 | $0 | 256K | Rate limited. 32K max output. Dev/testing. |

**Recommendation:** Use the free 26B MoE for all dev work. Switch to the paid 26B MoE for the live demo deployment. $5 in credits will last the entire hackathon.

---

## Cost Estimate

| Scenario | Est. tokens | Cost |
|---|---|---|
| One career guidance query (full loop: system prompt → tool calls → synthesis) | ~5K in + ~2K out | ~$0.0014 |
| Testing session (50 queries) | ~250K in + ~100K out | ~$0.07 |
| Live demo day (judges + testing, 200 queries) | ~1M in + ~400K out | ~$0.28 |
| **Entire hackathon lifecycle** | | **< $2** |

You will not run out of $5 in credits.

---

## Deployment Architecture

For the live demo URL that judges will hit:

```
┌──────────────────────────────────┐
│     Frontend (Vercel/Netlify)    │
│     React, dark-first, mobile   │
└──────────────┬───────────────────┘
               │
┌──────────────┴───────────────────┐
│     Backend API (FastAPI)        │
│     Deployed on Render / Fly.io  │
│     INFERENCE_BACKEND=openrouter │
│                                  │
│  ┌─────────────┐  ┌───────────┐ │
│  │ OpenRouter   │  │ Brightsmith│ │
│  │ Gemma 4 26B  │  │ Gold zone │ │
│  │ (inference)  │  │ (DuckDB)  │ │
│  └─────────────┘  └───────────┘ │
└──────────────────────────────────┘
```

For the Ollama track video:

```
┌──────────────────────────────────┐
│     Same frontend (localhost)    │
└──────────────┬───────────────────┘
               │
┌──────────────┴───────────────────┐
│     Same backend (localhost)     │
│     INFERENCE_BACKEND=ollama     │
│                                  │
│  ┌─────────────┐  ┌───────────┐ │
│  │ Ollama       │  │ Brightsmith│ │
│  │ Gemma 4 26B  │  │ Gold zone │ │
│  │ (local GPU)  │  │ (DuckDB)  │ │
│  └─────────────┘  └───────────┘ │
└──────────────────────────────────┘
```

Same codebase. One env var. The Tier 3 self-hosted story is real — it literally is the same app with a different inference backend.

---

## Kaggle Writeup Angle

Even though you're using OpenRouter for the hosted demo, the technical story is still strong:

> "FutureProof's inference layer is backend-agnostic. The same codebase runs against Ollama for local deployment or any OpenAI-compatible endpoint for cloud hosting. For our live demo, we use a cloud-hosted Gemma 4 instance. For the Ollama track submission, we demonstrate the identical application running entirely locally. The abstraction is a config switch, not a code change — proving that any school can deploy FutureProof on their own hardware by pointing the backend at a local Ollama instance."

This is technically accurate and doesn't overstate. Judges can verify by reading the config.

---

*— End of Spec —*
