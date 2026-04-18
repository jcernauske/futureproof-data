# Railway deployment

One Railway project, two services (backend + frontend), both built from
Dockerfiles in this monorepo.

## Prerequisites

- Railway account, project created
- Railway CLI optional but useful: `npm i -g @railway/cli && railway login`
- An OpenRouter API key (`sk-or-v1-...`)

## One-time data commit

The deployed backend reads from a 103 MB Iceberg slice that was previously
gitignored. We force-include just the consumable zone + catalog + reference:

```bash
git add data/catalog/ data/gold/iceberg_warehouse/ data/reference/
git commit -m "chore: ship gold-zone data slice for railway deploy"
```

If the warehouse grows beyond a few hundred MB, switch to Git LFS or
external object storage (S3/R2) and pull at container start.

## Backend service

1. Railway dashboard → **+ New** → **GitHub Repo** → pick `futureproof-data`.
2. Service settings:
   - **Service name:** `backend`
   - **Root Directory:** *(leave empty — repo root, the Dockerfile needs `src/` and `data/`)*
   - **Build:** Dockerfile, path `backend/Dockerfile` (already wired via `backend/railway.json`)
   - **Start command:** *(leave empty — Dockerfile `CMD` handles it)*
   - **Healthcheck path:** `/health`
3. Variables:
   ```
   INFERENCE_BACKEND=openrouter
   OPENROUTER_API_KEY=sk-or-v1-...
   FUTUREPROOF_CATALOG_PATH=/Users/jcernauske/code/bright/futureproof-data/data/catalog/catalog.db
   FUTUREPROOF_WAREHOUSE_PATH=/Users/jcernauske/code/bright/futureproof-data/data/warehouse
   ```
   (Yes, the host-style absolute path. The Iceberg catalog stores absolute
   metadata paths from the build machine; the Dockerfile installs the repo
   at that exact path inside the container so the catalog resolves.)
4. Networking → **Generate Domain**. Note the URL — you need it for the
   frontend build arg.

## Frontend service

1. Railway dashboard → **+ New** → **GitHub Repo** → same repo.
2. Service settings:
   - **Service name:** `frontend`
   - **Root Directory:** `frontend`
   - **Build:** Dockerfile, path `frontend/Dockerfile`
3. Variables (build-time):
   ```
   VITE_API_BASE_URL=https://<backend-domain-from-step-1.4>
   ```
   Vite inlines this at build time — changing it requires a redeploy.
4. Networking → **Generate Domain**.

## CORS

`backend/app/main.py` currently allows `*` origins. For production tighten
to the frontend domain.

## Verifying the deploy

```bash
curl https://<backend-domain>/health
# {"status":"ok"}

# Sanity-check a real query path
curl -X POST https://<backend-domain>/schools/search \
  -H 'content-type: application/json' \
  -d '{"query":"indiana"}'
```

Then load the frontend domain in a browser and walk a build through to
gauntlet — that exercises MCP tools, Gemma narratives, and the build
store.

## Limitations / follow-ups

- **Wrapped frame rendering** uses Playwright Chromium (already in the
  base image) and writes 1080×1920 PNGs to the build store DB. On
  Railway the build store lives in the container filesystem, so it
  resets on redeploy. Add a Railway volume mounted at
  `/Users/jcernauske/code/bright/futureproof-data/backend/data` to
  persist across deploys.
- **No Ollama in cloud.** `INFERENCE_BACKEND=openrouter` is the only
  supported value on Railway.
