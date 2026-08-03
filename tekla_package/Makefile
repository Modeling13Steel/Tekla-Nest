# ─────────────────────────────────────────────────────────────
#  Tekla Package — top-level orchestration
#  Run `make help` to see available commands.
# ─────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help
.PHONY: help bootstrap run run-admin lint format test docs-serve docs-build clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

bootstrap:  ## Install all workspace packages + dev tools (uv)
	uv sync

run:  ## Launch the Nesting desktop app
	uv run tekla-nest

run-admin:  ## Launch the Admin Console
	uv run tekla-nest-admin

lint:  ## Lint all Python with ruff
	uv run ruff check .

format:  ## Auto-format all Python with ruff
	uv run ruff format .

test:  ## Run the test suite (offscreen Qt)
	QT_QPA_PLATFORM=offscreen uv run pytest

docs-serve:  ## Preview the documentation site locally
	uv run --with mkdocs-material mkdocs serve

docs-build:  ## Build the static documentation site
	uv run --with mkdocs-material mkdocs build --strict

clean:  ## Remove caches and build artifacts
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache site dist build
