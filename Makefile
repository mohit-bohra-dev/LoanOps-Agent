.PHONY: install lint test ingest eval ui-install fixtures demo down

install:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy --strict packages

test:
	uv run pytest

ingest:
	uv run python -m packages.rag.ingest data/sops

eval:
	uv run python -m packages.eval.run --golden data/golden.jsonl --report out/eval.json

ui-install:
	cd apps/web_ui && npm install

# Windows: cd scripts/fixtures; npm install; npm run generate
fixtures:
	cd scripts/fixtures && npm install && npm run generate

demo:
	uv run uvicorn apps.tools_api.main:app --port 5000 &
	uv run uvicorn apps.agent_api.main:app --port 5001 &
	cd apps/web_ui && npm run dev

down:
	pkill -f "uvicorn apps" || true
	pkill -f "vite" || true
