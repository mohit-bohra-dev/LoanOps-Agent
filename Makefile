.PHONY: install lint test ingest eval eval-mcp-l1 eval-l2 eval-l3 eval-l4 eval-l5 eval-l7 eval-l8 eval-l9 ui-install fixtures demo down

install:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy --strict packages

test:
	uv run pytest

ingest:
	uv run python -m packages.rag.ingest data/sops/_confluence

eval:
	uv run python -m packages.eval.run --golden data/golden.jsonl --report out/eval.json

eval-mcp-l1:
	uv run python -m packages.eval.mcp --report out/eval-mcp-l1.json

eval-l2:
	uv run python -m packages.eval.selection --report out/eval-l2.json

eval-l3:
	uv run python -m packages.eval.arguments --report out/eval-l3.json

eval-l4:
	uv run python -m packages.eval.trajectory --report out/eval-l4.json

eval-l5:
	uv run python -m packages.eval.outcomes --report out/eval-l5.json

eval-l7:
	uv run python -m packages.eval.robustness --report out/eval-l7.json

eval-l8:
	uv run python -m packages.eval.operations --report out/eval-l8.json

eval-l9:
	uv run python -m packages.eval.governance validate

ui-install:
	cd apps/web_ui && npm install

# Windows: cd scripts/fixtures; npm install; npm run generate
fixtures:
	cd scripts/fixtures && npm install && npm run generate

demo:
	uv run uvicorn apps.agent_api.main:app --host 127.0.0.1 --port 8000 &
	cd apps/web_ui && npm run dev

down:
	pkill -f "uvicorn apps" || true
	pkill -f "vite" || true
