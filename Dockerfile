# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    RECIPE_DATA_PATH=/app/data/recipes \
    INDEX_CACHE_DIR=/app/data/cache \
    EMBEDDING_CACHE_DIR=/app/data/models \
    SEMANTIC_ENABLED=true \
    PORT=8000

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN python -m pip install "uv==0.11.23" && uv sync --frozen --no-dev --extra all
ENV PATH="/app/.venv/bin:$PATH"

COPY scripts ./scripts
COPY evaluation ./evaluation
COPY data/sample_recipes.json data/README.md ./data/

ARG INCLUDE_FULL_DATASET=1
ARG PREBUILD_INDEX=1
ARG MAX_RECIPES=10000
ARG EMBEDDING_PARALLEL_WORKERS=1
ENV MAX_RECIPES=$MAX_RECIPES
RUN if [ "$INCLUDE_FULL_DATASET" = "1" ]; then \
      python scripts/download_dataset.py --output data/recipes; \
    else \
      mkdir -p data/recipes && cp data/sample_recipes.json data/recipes/sample_recipes.json; \
    fi && \
    if [ "$PREBUILD_INDEX" = "1" ]; then \
      if [ -n "$MAX_RECIPES" ]; then \
        MAX_RECIPES="$MAX_RECIPES" EMBEDDING_PARALLEL_WORKERS="$EMBEDDING_PARALLEL_WORKERS" python scripts/build_index.py; \
      else \
        EMBEDDING_PARALLEL_WORKERS="$EMBEDDING_PARALLEL_WORKERS" python scripts/build_index.py; \
      fi; \
    fi && \
    chown -R app:app /app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=90s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/healthz', timeout=2)" || exit 1

CMD ["sh", "-c", "exec uvicorn recipe_search.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
