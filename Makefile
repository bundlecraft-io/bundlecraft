.PHONY: help install install-dev install-fetchers clean test test-cov lint format check build release-test release verify-package clean-build clean-pyc clean-test version

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

# Release targets (use with caution!)
release-test: build verify-package ## Build and upload to Test PyPI
	@echo "Uploading to Test PyPI..."
	$(TWINE) upload --repository testpypi $(DIST_DIR)/*

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
