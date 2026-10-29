# EATGOOD developer commands. Requires Python 3.12+, Node 22+ and uv (https://docs.astral.sh/uv/).
.PHONY: setup dev api web build test lint typecheck security e2e smoke check lock data clean

VENV := .venv
PY := $(VENV)/bin/python

setup: ## Install backend and frontend dependencies
	uv venv --python 3.12 $(VENV)
	VIRTUAL_ENV=$(VENV) uv pip install -r requirements-dev.txt
	cd frontend && npm ci

api: ## Run the API with auto-reload on http://127.0.0.1:8000
	$(VENV)/bin/uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

web: ## Run the Vite dev server on http://127.0.0.1:5173 (proxies /api to :8000)
	cd frontend && npm run dev

dev: ## Run API and frontend dev servers together
	$(MAKE) -j2 api web

build: ## Build the frontend into frontend/dist (served by the API when run locally)
	cd frontend && npm run build

test: ## Backend tests with coverage
	$(VENV)/bin/pytest --cov --cov-report=term-missing

lint: ## Lint backend and frontend
	$(VENV)/bin/ruff check .
	cd frontend && npm run lint

typecheck: ## Static type check of the backend
	$(VENV)/bin/mypy

security: ## Dependency and code security scans
	$(VENV)/bin/bandit -q -r backend api -x backend/tests
	$(VENV)/bin/pip-audit -r requirements.txt
	cd frontend && npm audit --audit-level=high

e2e: build ## End-to-end browser tests against a local server
	cd frontend && npx playwright install chromium
	EATGOOD_RATE_LIMIT=false $(VENV)/bin/uvicorn backend.main:app --port 8000 & echo $$! > .e2e.pid; \
	sleep 3; cd frontend && npm run e2e; status=$$?; kill `cat ../.e2e.pid`; rm -f ../.e2e.pid; exit $$status

smoke: ## Post-deploy smoke test: make smoke URL=https://eatgood26.vercel.app
	cd frontend && BASE_URL=$(URL) npm run smoke

check: lint typecheck test security build ## Everything CI runs, except e2e

lock: ## Re-pin Python dependencies after editing pyproject.toml (uv.lock is what Vercel installs)
	uv lock
	uv pip compile pyproject.toml --python-version 3.12 -o requirements.txt
	uv pip compile pyproject.toml --group dev --python-version 3.12 -o requirements-dev.txt

data: ## Regenerate the synthetic demo catalogue (reproducible, seed 42)
	$(PY) scripts/generate_initial_data.py

clean:
	rm -rf frontend/dist frontend/public/ocr .pytest_cache .mypy_cache .ruff_cache .coverage data/eatgood_app.db
