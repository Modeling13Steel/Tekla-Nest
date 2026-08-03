.DEFAULT_GOAL := help
PYTHON      := uv run python
APP_NAME    := tekla-nest
ADMIN_APP_NAME := tekla-nest-admin
VERSION     := $(shell $(PYTHON) -c "import importlib.metadata; print(importlib.metadata.version('tekla-nest'))" 2>/dev/null || echo "dev")
DIST_DIR    := dist

# ── Setup ────────────────────────────────────────────────────

.PHONY: install
install: ## Install project + runtime dependencies
	uv sync

.PHONY: install-dev
install-dev: ## Install project + dev dependencies (pytest, pytest-qt)
	uv pip install -e ".[dev]"

.PHONY: install-all
install-all: ## Install everything (dev + pdf + tekla on Windows)
	uv pip install -e ".[dev,pdf]"

# ── Run ──────────────────────────────────────────────────────

.PHONY: run
run: ## Launch the application
	uv run tekla-nest

.PHONY: run-admin
run-admin: ## Launch the license admin application
	uv run tekla-nest-admin

.PHONY: demo
demo: ## Run CLI demo with sample data (or: make demo CSV=myfile.csv)
	uv run python -m tekla_nest.demo $(CSV)

# ── Quality ──────────────────────────────────────────────────

.PHONY: test
test: ## Run all tests
	uv run pytest -v

.PHONY: test-fast
test-fast: ## Run tests without verbose output
	uv run pytest -q

.PHONY: test-cov
test-cov: ## Run tests with coverage report (install pytest-cov first)
	uv run pytest --cov=tekla_nest --cov-report=term-missing

.PHONY: lint
lint: ## Run ruff linter (install ruff first)
	uvx ruff check src/ tests/

.PHONY: format
format: ## Auto-format code with ruff
	uvx ruff format src/ tests/

.PHONY: check
check: lint test ## Lint + test in one shot

# ── Build / Package ─────────────────────────────────────────

.PHONY: build
build: ## Build wheel + sdist
	uv build

# PyInstaller --add-data separator: ":" on macOS/Linux, ";" on Windows
ifeq ($(OS),Windows_NT)
  DATA_SEP := ;
  VERSION_INFO := --version-file "resources/version_info.txt"
else
  DATA_SEP := :
  VERSION_INFO :=
endif
LICENSE_PUBLIC_KEY := $(wildcard src/tekla_nest/licensing/public_key.pem)
ifneq ($(LICENSE_PUBLIC_KEY),)
  LICENSE_DATA := --add-data "$(LICENSE_PUBLIC_KEY)$(DATA_SEP)tekla_nest/licensing"
else
  LICENSE_DATA :=
endif

.PHONY: binary
binary: ## Build standalone binary with PyInstaller (single .exe)
	uv run pyinstaller \
		--name $(APP_NAME) \
		--onefile \
		--windowed \
		--icon "resources/logo_cut_bar_mark.ico" \
		$(VERSION_INFO) \
		--add-data "config.yaml$(DATA_SEP)." \
		--add-data "resources$(DATA_SEP)resources" \
		$(LICENSE_DATA) \
		--distpath $(DIST_DIR) \
		src/tekla_nest/__main__.py
	@echo ""
	@echo "✔ Binary ready: $(DIST_DIR)/$(APP_NAME)"

.PHONY: binary-admin
binary-admin: ## Build standalone admin binary with PyInstaller (single .exe)
	uv run pyinstaller \
		--name $(ADMIN_APP_NAME) \
		--onefile \
		--windowed \
		--icon "resources/logo_cut_bar_mark.ico" \
		$(VERSION_INFO) \
		--add-data "config.yaml$(DATA_SEP)." \
		--add-data "resources$(DATA_SEP)resources" \
		--distpath $(DIST_DIR) \
		src/tekla_nest/admin/__main__.py
	@echo ""
	@echo "✔ Admin binary ready: $(DIST_DIR)/$(ADMIN_APP_NAME)"

.PHONY: binary-dir
binary-dir: ## Build as a directory bundle (for installer)
	uv run pyinstaller \
		--name $(APP_NAME) \
		--onedir \
		--windowed \
		--icon "resources/logo_cut_bar_mark.ico" \
		$(VERSION_INFO) \
		--add-data "config.yaml$(DATA_SEP)." \
		--add-data "resources$(DATA_SEP)resources" \
		$(LICENSE_DATA) \
		--distpath $(DIST_DIR) \
		src/tekla_nest/__main__.py
	@echo ""
	@echo "✔ Bundle ready: $(DIST_DIR)/$(APP_NAME)/"

.PHONY: binary-admin-dir
binary-admin-dir: ## Build admin app as a directory bundle (for installer)
	uv run pyinstaller \
		--name $(ADMIN_APP_NAME) \
		--onedir \
		--windowed \
		--icon "resources/logo_cut_bar_mark.ico" \
		$(VERSION_INFO) \
		--add-data "config.yaml$(DATA_SEP)." \
		--add-data "resources$(DATA_SEP)resources" \
		--distpath $(DIST_DIR) \
		src/tekla_nest/admin/__main__.py
	@echo ""
	@echo "✔ Admin bundle ready: $(DIST_DIR)/$(ADMIN_APP_NAME)/"

.PHONY: binaries
binaries: binary-dir binary-admin-dir ## Build separated app + admin directory bundles

.PHONY: installer
installer: binary-dir ## Build Windows installer (requires Inno Setup: iscc on PATH)
ifeq ($(OS),Windows_NT)
	@if not exist "build\\python-embed\\python.exe" ( \
		echo "Preparing bundled Python..." && \
		powershell -ExecutionPolicy Bypass -File scripts/prepare-python-embed.ps1 \
	)
endif
	iscc installer.iss
	@echo ""
	@echo "✔ Installer ready: $(DIST_DIR)/tekla-nest-setup.exe"

.PHONY: installer-admin
installer-admin: binary-admin-dir ## Build Windows admin installer (requires Inno Setup: iscc on PATH)
	iscc installer-admin.iss
	@echo ""
	@echo "✔ Admin installer ready: $(DIST_DIR)/tekla-nest-admin-setup.exe"

.PHONY: installers
installers: installer installer-admin ## Build separated customer + admin installers

.PHONY: infrastructure-package
infrastructure-package: ## Package license-server infrastructure separately from desktop binaries
	mkdir -p $(DIST_DIR)
	cd license-server && zip -r "../$(DIST_DIR)/tekla-nest-license-server-infrastructure.zip" . \
		-x "functions/venv/*" "keys/*" ".firebase/*" "__pycache__/*" "*.pyc"
	@echo ""
	@echo "✔ Infrastructure package ready: $(DIST_DIR)/tekla-nest-license-server-infrastructure.zip"

.PHONY: package-all
package-all: installers infrastructure-package ## Build separated desktop installers + infrastructure package

.PHONY: python-embed
python-embed: ## Prepare portable Python with pythonnet (Windows only)
	powershell -ExecutionPolicy Bypass -File scripts/prepare-python-embed.ps1

.PHONY: install-pyinstaller
install-pyinstaller: ## Install PyInstaller into the venv
	uv pip install pyinstaller

# ── Clean ────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove build artifacts, caches, .pyc files
	rm -rf $(DIST_DIR) build *.spec
	rm -rf .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

.PHONY: clean-all
clean-all: clean ## clean + remove .venv
	rm -rf .venv

# ── Info ─────────────────────────────────────────────────────

.PHONY: version
version: ## Print current version
	@echo $(VERSION)

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
