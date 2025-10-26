.PHONY: help install install-dev install-fetchers clean test test-cov lint format check build release-test release verify-package clean-build clean-pyc clean-test version image image-nocache image-run image-shell image-ensure

# Default Python interpreter
PYTHON := python3
PIP := $(PYTHON) -m pip
BUILD := $(PYTHON) -m build
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
RUFF := $(PYTHON) -m ruff
TWINE := $(PYTHON) -m twine

# Directories
SRC_DIR := bundlecraft
TEST_DIR := tests
DIST_DIR := dist
BUILD_DIR := build

# Help target
help: ## Show this help message
	@echo "BundleCraft - Development Makefile"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "For detailed documentation, see CONTRIBUTING.md"
	@echo ""
	@echo "Container targets:"
	@echo "  image              Build container image with version fallback"
	@echo "  image-nocache      Build container image without cache"
	@echo "  image-run          Run container to show bundlecraft --version"
	@echo "  image-shell        Start an interactive shell in the image"

# Installation targets
install: ## Install package in editable mode (development)
	$(PIP) install -e .

install-dev: ## Install package with dev dependencies
	$(PIP) install -e ".[dev]"

install-fetchers: ## Install package with fetcher dependencies
	$(PIP) install -e ".[fetchers]"

install-all: ## Install package with all dependencies
	$(PIP) install -e ".[dev,fetchers]"

# Cleaning targets
clean: clean-build clean-pyc clean-test ## Remove all build, test, coverage and Python artifacts

clean-build: ## Remove build artifacts
	rm -rf $(BUILD_DIR)/ $(DIST_DIR)/ *.egg-info
	rm -f bundlecraft/_version.py
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## Remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '.pytest_cache' -exec rm -rf {} +

clean-test: ## Remove test and coverage artifacts
	rm -rf .pytest_cache/ .coverage htmlcov/ .tox/

# Code quality targets
format: ## Format code with black
	$(BLACK) $(SRC_DIR) $(TEST_DIR) scripts/

lint: ## Lint code with ruff
	$(RUFF) check $(SRC_DIR) $(TEST_DIR) scripts/

lint-fix: ## Lint and auto-fix with ruff
	$(RUFF) check --fix $(SRC_DIR) $(TEST_DIR) scripts/

check: lint ## Run all code quality checks (alias for lint)

# Testing targets
test: ## Run tests quickly with pytest
	$(PYTEST) -v

test-cov: ## Run tests with coverage report
	$(PYTEST) --cov=$(SRC_DIR) --cov-report=html --cov-report=term -v

test-verbose: ## Run tests with verbose output
	$(PYTEST) -vv --showlocals

# Build targets
build: clean-build ## Build source and wheel distributions
	$(BUILD)

build-wheel: clean-build ## Build wheel distribution only
	$(BUILD) --wheel

build-sdist: clean-build ## Build source distribution only
	$(BUILD) --sdist

# Package verification
verify-package: ## Verify built package with twine
	$(TWINE) check $(DIST_DIR)/*

# Local testing targets
test-install: build ## Test installation from built wheel in isolated venv
	@echo "Creating test environment..."
	@rm -rf /tmp/test-bundlecraft-install
	@$(PYTHON) -m venv /tmp/test-bundlecraft-install
	@echo "Installing from wheel..."
	@/tmp/test-bundlecraft-install/bin/pip install --quiet dist/*.whl
	@echo "Testing installation..."
	@/tmp/test-bundlecraft-install/bin/bundlecraft --version
	@/tmp/test-bundlecraft-install/bin/python -c "import bundlecraft; print(f'✅ Successfully installed: {bundlecraft.__version__}')"
	@echo "Cleaning up..."
	@rm -rf /tmp/test-bundlecraft-install
	@echo "✅ Package installs and imports correctly!"

test-install-interactive: build ## Test installation interactively (venv stays open)
	@echo "Creating test environment at /tmp/test-bundlecraft..."
	@rm -rf /tmp/test-bundlecraft
	@$(PYTHON) -m venv /tmp/test-bundlecraft
	@/tmp/test-bundlecraft/bin/pip install --quiet dist/*.whl
	@echo ""
	@echo "✅ Test environment ready at: /tmp/test-bundlecraft"
	@echo "To use it:"
	@echo "  source /tmp/test-bundlecraft/bin/activate"
	@echo "  bundlecraft --version"
	@echo "  deactivate"
	@echo ""
	@echo "Clean up with: rm -rf /tmp/test-bundlecraft"

# Release targets (use with caution!)
release-test: build verify-package ## Build and upload to Test PyPI
	@echo "📦 Uploading to Test PyPI..."
	@echo "Install with: pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ bundlecraft"
	$(TWINE) upload --repository testpypi $(DIST_DIR)/*

release-test-install: ## Install latest version from Test PyPI
	@echo "Installing from Test PyPI..."
	pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ bundlecraft

release: build verify-package ## Build and upload to PyPI (PRODUCTION!)
	@echo "⚠️  WARNING: This will upload to PRODUCTION PyPI!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read
	$(TWINE) upload $(DIST_DIR)/*

# Version information
version: ## Show current package version
	@$(PYTHON) -c "import bundlecraft; print(f'Version: {bundlecraft.__version__}')" 2>/dev/null || echo "Package not installed. Run 'make install' first."

# Git tag helpers
tag: ## Show current git tags
	@git tag -l -n1

tag-version: ## Create a new version tag (use: make tag-version VERSION=0.2.0)
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION not specified. Usage: make tag-version VERSION=0.2.0"; \
		exit 1; \
	fi
	@echo "Creating tag v$(VERSION)..."
	git tag -a "v$(VERSION)" -m "Release v$(VERSION)"
	@echo "Tag created. Push with: git push origin v$(VERSION)"

# Development workflow
dev-setup: install-all ## Complete development setup (install all dependencies)
	@echo "Development environment ready!"
	@echo "Run 'make test' to verify everything works."

qa: clean format lint test ## Run full QA pipeline (format, lint, test)

# BundleCraft-specific targets
bundlecraft-build: ## Build trust bundles for dev environment
	bundlecraft build --env dev --verbose

bundlecraft-verify: ## Verify trust bundles
	bundlecraft verify --target dist/dev --verify-all

bundlecraft-test: bundlecraft-build bundlecraft-verify ## Build and verify trust bundles

# -----------------------------------------------------------------------------
# Container image builds (Docker or Podman)
# -----------------------------------------------------------------------------

# Choose container engine: prefer podman if available, otherwise docker
CONTAINER ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

# Derive a PEP 440-ish version from git describe for hatch-vcs override
RAW_DESCR := $(shell git describe --tags --abbrev=7 --dirty --always 2>/dev/null || echo "0.0.0")
HATCH_BUILD_VERSION ?= $(shell echo "$(RAW_DESCR)" | sed -E 's/^v([0-9]+\.[0-9]+\.[0-9]+)$$/\1/; t; s/^v([0-9]+\.[0-9]+\.[0-9]+)-([0-9]+)-g([0-9a-f]+)(-dirty)?$$/\1.dev\2+g\3\4/; t; s/^([0-9a-f]+)(-dirty)?$$/0.0.0.dev0+g\1\2/; t; s/.*/0.0.0+local/')

# Image naming
IMAGE_NAME ?= bundlecraft
# Container tags cannot include '+'; normalize to a safe tag
IMAGE_TAG ?= $(shell echo "$(HATCH_BUILD_VERSION)" | tr '+' '-' )
# Podman requires fully qualified local reference; use localhost/ prefix for podman
IS_PODMAN := $(findstring podman,$(CONTAINER))
IMAGE_REF ?= $(if $(IS_PODMAN),localhost/$(IMAGE_NAME):$(IMAGE_TAG),$(IMAGE_NAME):$(IMAGE_TAG))

image: ## Build container image (auto-passes HATCH_BUILD_VERSION for hatch-vcs)
	@echo "Building image with $(CONTAINER) as $(IMAGE_REF) (HATCH_BUILD_VERSION=$(HATCH_BUILD_VERSION))"
	$(CONTAINER) build \
		--build-arg HATCH_BUILD_VERSION=$(HATCH_BUILD_VERSION) \
		-t $(IMAGE_REF) .

image-nocache: ## Build container image without cache
	$(CONTAINER) build \
		--no-cache \
		--build-arg HATCH_BUILD_VERSION=$(HATCH_BUILD_VERSION) \
		-t $(IMAGE_REF) .

image-ensure: ## Build image if missing
	@if ! $(CONTAINER) image inspect $(IMAGE_REF) >/dev/null 2>&1; then \
		echo "Image $(IMAGE_REF) not found; building..."; \
		$(CONTAINER) build --build-arg HATCH_BUILD_VERSION=$(HATCH_BUILD_VERSION) -t $(IMAGE_REF) .; \
	fi

image-run: image-ensure ## Run container image to print version
	$(CONTAINER) run --rm $(IMAGE_REF) --version

image-shell: image-ensure ## Start an interactive shell in the image
	$(CONTAINER) run --rm -it $(IMAGE_REF) /bin/bash
