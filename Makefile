.PHONY: install data index dev test lint format evaluate docker-build docker-run

install:
	uv sync --all-extras

data:
	uv run python scripts/download_dataset.py

index:
	RECIPE_DATA_PATH=data/recipes uv run python scripts/build_index.py

dev:
	uv run uvicorn recipe_search.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src

format:
	uv run ruff check --fix .
	uv run ruff format .

evaluate:
	uv run recipe-evaluate --data data/recipes --max-recipes 10000 --output evaluation/results/representative-10k.md

docker-build:
	docker build -t omai-recipe-search .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env omai-recipe-search
