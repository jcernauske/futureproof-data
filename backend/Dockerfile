FROM python:3.11-slim

# Iceberg metadata files store absolute paths from the host build machine
# (e.g. /Users/jcernauske/.../data/gold/iceberg_warehouse/...). Install the
# repo at that exact path in the container so the catalog resolves without
# any path rewrite.
ENV APP_DIR=/Users/jcernauske/code/bright/futureproof-data
WORKDIR ${APP_DIR}

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=${APP_DIR}/src

# git is required for the brightsmith VCS dependency
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Brightsmith is public at github.com/hyena-studios/brightsmith, so pip
# fetches it without authentication. The GITHUB_TOKEN arg is kept for
# Railway deployment compatibility — if the service variable is set, the
# git config rewrite below embeds it; if unset, the rewrite is a no-op
# and the public clone still works. Local builds can ignore it entirely.
ARG GITHUB_TOKEN

# Install backend deps first for cache reuse
COPY backend/pyproject.toml backend/pyproject.toml
RUN git config --global "url.https://${GITHUB_TOKEN}@github.com/.insteadOf" "https://github.com/" \
    && pip install --upgrade pip \
    && pip install fastapi 'uvicorn[standard]' pydantic duckdb \
       jinja2 openai python-dotenv pyyaml \
       'brightsmith @ git+https://github.com/hyena-studios/brightsmith.git'

# Copy the bits the backend actually needs at runtime
COPY backend/ backend/
COPY src/ src/
COPY data/catalog/ data/catalog/
COPY data/gold/ data/gold/
COPY data/silver/ data/silver/
COPY data/bronze/ data/bronze/
COPY data/reference/ data/reference/

# Install the backend package itself
RUN pip install -e ./backend

# Pre-create the writable build store dir
RUN mkdir -p ${APP_DIR}/backend/data

ENV INFERENCE_BACKEND=openrouter \
    FUTUREPROOF_CATALOG_PATH=${APP_DIR}/data/catalog/catalog.db \
    FUTUREPROOF_WAREHOUSE_PATH=${APP_DIR}/data/warehouse \
    GEMMA_LOG_STDOUT=1

# Railway injects $PORT
EXPOSE 8000
# --proxy-headers + --forwarded-allow-ips so uvicorn trusts X-Forwarded-Proto
# from Railway's edge. Without this, FastAPI's trailing-slash 307 redirects
# go to http:// and browsers refuse to follow https→http downgrades.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir backend --proxy-headers --forwarded-allow-ips='*'"]
