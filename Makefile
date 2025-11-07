# Auto-detect container runtime and set appropriate flags
CONTAINER_CMD := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
CONTAINER ?= $(notdir $(CONTAINER_CMD))

# Container-specific flags for better compatibility
ifeq ($(CONTAINER),podman)
    CONTAINER_BUILD_FLAGS := --cgroup-manager=cgroupfs
    CONTAINER_RUN_FLAGS := --userns=keep-id
    VOLUME_SUFFIX := :Z
else
    CONTAINER_BUILD_FLAGS :=
    CONTAINER_RUN_FLAGS :=
    VOLUME_SUFFIX :=
endif

HATCH_BUILD_VERSION ?= 0.0.0+local
IMAGE_NAME ?= bundlecraft
IMAGE_TAG ?= local
IMAGE_REF ?= localhost/$(IMAGE_NAME):$(IMAGE_TAG)

# Workspace and quick-test credentials
BUNDLECRAFT_WORKSPACE ?= $(CURDIR)
TRUST_JKS_PASSWORD ?= changeit
TRUST_P12_PASSWORD ?= changeit

# Temp venv for testing built wheels
TMP_VENV ?= .tmp/pypi-test-venv

# Release helpers: derive version from latest git tag
# - GIT_TAG is used as the image tag (e.g. v1.2.3)
# - VERSION is HATCH_BUILD_VERSION (strips leading 'v' for PEP 440)
GIT_TAG ?= $(shell git describe --tags --abbrev=0 2>/dev/null)
VERSION ?= $(shell echo "$(GIT_TAG)" | sed 's/^v//')
RELEASE_IMAGE_REF ?= localhost/$(IMAGE_NAME):$(GIT_TAG)

.PHONY: \
	build-image build-test-image build-pypi build-test-pypi \
	test-image-version test-image-build test-image-run \
	test-pypi-version test-pypi-build test-pypi-run \
	setup-dev ci-install-dev ci-test ci-lint \
	deploy-pre-release deploy-main-release \
	lock-requirements validate-lock update-lock \
	deploy-pre-release deploy-main-release verify-signatures \
	help

help:
	@echo "Development setup:"
	@echo "  setup-dev               Complete development environment setup (dependencies + git hooks)"
	@echo "Container targets:"
	@echo "  build-image             Build image using latest git tag (HATCH_BUILD_VERSION from tag)"
	@echo "  build-test-image        Build image tagged 'local' with HATCH_BUILD_VERSION=0.0.0+local"
	@echo "  test-image-version      Run 'bundlecraft --version' using built image"
	@echo "  test-image-build        Prepare configs, build + verify in container, cleanup"
	@echo "  test-image-run          Same setup, but runs your args: make test-image-run BUNDLECRAFT_ARGS='build --env dev'"
	@echo "PyPI targets:"
	@echo "  build-pypi              Build wheel + sdist using latest git tag"
	@echo "  build-test-pypi         Build wheel + sdist with version 0.0.0+local"
	@echo "  test-pypi-version       Create temp venv, install built wheel, print version"
	@echo "  test-pypi-build         Prepare configs, install built wheel, build + verify, cleanup"
	@echo "  test-pypi-run           Same setup, but runs your args: make test-pypi-run BUNDLECRAFT_ARGS='build --env dev'"
	@echo "Git Tag Deployment helpers:"
	@echo "  deploy-pre-release      Create and push a tag to Github based on the latest changelog entry in the pre-release section"
	@echo "  deploy-main-release     Create and push a tag to Github based on the latest changelog entry in the stable releases section"
	@echo "Sigstore verification:"
	@echo "  verify-signatures       Verify Sigstore signatures for the latest release (requires cosign)"
	@echo "CI helpers:"
	@echo "  ci-install-dev          Install dev dependencies for CI"
	@echo "  ci-test                 Run pytest with coverage for CI"
	@echo "  ci-lint                 Run ruff linting for CI"
	@echo "Dependency lock file:"
	@echo "  lock-requirements       Generate requirements-lock.txt from pyproject.toml"
	@echo "  validate-lock           Validate lock file is up-to-date"
	@echo "  update-lock             Update all dependencies in lock file"

build-test-image:
	$(CONTAINER) build $(CONTAINER_BUILD_FLAGS) --build-arg HATCH_BUILD_VERSION=$(HATCH_BUILD_VERSION) -t $(IMAGE_REF) .

# Build a release image tagged with the latest git tag.
# - Uses $(GIT_TAG) for the image tag.
# - Uses $(VERSION) (without leading 'v') for HATCH_BUILD_VERSION inside the wheel.
build-image:
	@test -n "$(GIT_TAG)" || (echo "No git tag found. Create a tag (e.g. v1.2.3) or call: make release-image GIT_TAG=v1.2.3" >&2; exit 1)
	$(CONTAINER) build $(CONTAINER_BUILD_FLAGS) \
	  --build-arg HATCH_BUILD_VERSION=$(VERSION) \
	  -t $(RELEASE_IMAGE_REF) \
	  .

test-image-version: build-test-image
	$(CONTAINER) run --rm $(IMAGE_REF) --version

test-image-build: build-test-image
	@set -e; \
	BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" scripts/prepare_test_configs.sh; \
	trap 'BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" scripts/prepare_test_configs.sh --cleanup' EXIT; \
	$(CONTAINER) run --rm \
	  $(CONTAINER_RUN_FLAGS) \
	  -e BUNDLECRAFT_WORKSPACE=/workspace \
	  -e TRUST_JKS_PASSWORD="$(TRUST_JKS_PASSWORD)" \
	  -e TRUST_P12_PASSWORD="$(TRUST_P12_PASSWORD)" \
	  -v "$(BUNDLECRAFT_WORKSPACE):/workspace$(VOLUME_SUFFIX)" \
	  -w /workspace \
	  $(IMAGE_REF) \
	  build --env test-example-envconfig --verbose --force; \
	$(CONTAINER) run --rm \
	  $(CONTAINER_RUN_FLAGS) \
	  -v "$(BUNDLECRAFT_WORKSPACE):/workspace$(VOLUME_SUFFIX)" \
	  -w /workspace \
	  $(IMAGE_REF) \
	  verify --target dist/.test-inline --verify-all

test-image-run: build-test-image
	@set -e; \
	BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" scripts/prepare_test_configs.sh; \
	trap 'BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" scripts/prepare_test_configs.sh --cleanup' EXIT; \
	if [ -z "$(BUNDLECRAFT_ARGS)" ]; then \
	  echo "Usage: make test-image-run BUNDLECRAFT_ARGS='build --env dev --verbose'" >&2; \
	  exit 2; \
	fi; \
	$(CONTAINER) run --rm \
	  $(CONTAINER_RUN_FLAGS) \
	  -e BUNDLECRAFT_WORKSPACE=/workspace \
	  -e TRUST_JKS_PASSWORD="$(TRUST_JKS_PASSWORD)" \
	  -e TRUST_P12_PASSWORD="$(TRUST_P12_PASSWORD)" \
	  -v "$(BUNDLECRAFT_WORKSPACE):/workspace$(VOLUME_SUFFIX)" \
	  -w /workspace \
	  $(IMAGE_REF) \
	  $(BUNDLECRAFT_ARGS)

# ---- PyPI build/test helpers ----
build-pypi:
	rm -rf dist && mkdir -p dist
	@test -n "$(GIT_TAG)" || (echo "No git tag found. Create a tag (e.g. v1.2.3) or call: make build-pypi GIT_TAG=v1.2.3" >&2; exit 1)
	HATCH_BUILD_VERSION=$(VERSION) \
	SETUPTOOLS_SCM_PRETEND_VERSION=$(VERSION) \
	SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BUNDLECRAFT=$(VERSION) \
	  python -m build
	python -m pip install --no-input --quiet --upgrade twine
	twine check dist/*

build-test-pypi:
	rm -rf dist && mkdir -p dist
	HATCH_BUILD_VERSION=0.0.0+local \
	SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0+local \
	SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BUNDLECRAFT=0.0.0+local \
	  python -m build
	python -m pip install --no-input --quiet --upgrade twine
	twine check dist/*

test-pypi-version: build-test-pypi
	@set -e; \
	rm -rf "$(TMP_VENV)"; python -m venv "$(TMP_VENV)"; \
	. "$(TMP_VENV)/bin/activate"; pip install -U pip; pip install dist/*.whl; \
	bundlecraft --version; \
	deactivate; rm -rf "$(TMP_VENV)"

test-pypi-build: build-test-pypi
	@set -e; \
	BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" scripts/prepare_test_configs.sh; \
	trap 'BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" scripts/prepare_test_configs.sh --cleanup; rm -rf "$(TMP_VENV)"' EXIT; \
	rm -rf "$(TMP_VENV)"; python -m venv "$(TMP_VENV)"; \
	. "$(TMP_VENV)/bin/activate"; pip install -U pip; pip install dist/*.whl; \
	BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" \
	TRUST_JKS_PASSWORD="$(TRUST_JKS_PASSWORD)" TRUST_P12_PASSWORD="$(TRUST_P12_PASSWORD)" \
	  bundlecraft build --env test-example-envconfig --verbose --force; \
	bundlecraft verify --target dist/.test-inline --verify-all; \
	deactivate

test-pypi-run: build-test-pypi
	@set -e; \
	BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" scripts/prepare_test_configs.sh; \
	trap 'BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" scripts/prepare_test_configs.sh --cleanup; rm -rf "$(TMP_VENV)"' EXIT; \
	if [ -z "$(BUNDLECRAFT_ARGS)" ]; then \
	  echo "Usage: make test-pypi-run BUNDLECRAFT_ARGS='build --env dev --verbose'" >&2; \
	  exit 2; \
	fi; \
	rm -rf "$(TMP_VENV)"; python -m venv "$(TMP_VENV)"; \
	. "$(TMP_VENV)/bin/activate"; pip install -U pip; pip install dist/*.whl; \
	BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" \
	TRUST_JKS_PASSWORD="$(TRUST_JKS_PASSWORD)" TRUST_P12_PASSWORD="$(TRUST_P12_PASSWORD)" \
	  bundlecraft $(BUNDLECRAFT_ARGS); \
	deactivate

# ---- Development setup ----
setup-dev:
	@echo "Setting up development environment..."
	@echo ""
	@# Check if we're in a virtual environment
	@if [ -z "$$VIRTUAL_ENV" ] && [ -z "$$CONDA_DEFAULT_ENV" ]; then \
		echo "🔍 No virtual environment detected."; \
		if [ ! -d "venv" ]; then \
			echo "📦 Creating virtual environment..."; \
			python3 -m venv venv; \
		else \
			echo "📦 Found existing virtual environment."; \
		fi; \
		echo ""; \
		echo "⚠️  Please activate the virtual environment and run setup again:"; \
		echo "   source venv/bin/activate  # Linux/Mac"; \
		echo "   venv\\Scripts\\activate.bat  # Windows"; \
		echo "   make setup-dev"; \
		echo ""; \
		exit 1; \
	else \
		echo "✅ Virtual environment active: $$VIRTUAL_ENV$$CONDA_DEFAULT_ENV"; \
	fi
	@echo ""
	python -m pip install --upgrade pip
	pip install -e ".[dev]"
	@echo ""
	@echo "🪝 Setting up git hooks..."
	@if git config --get core.hooksPath >/dev/null 2>&1; then \
		echo "   • Custom hooks already configured, installing pre-commit alongside..."; \
		pre-commit install --allow-missing-config || echo "   • Pre-commit installation skipped (custom hooks take precedence)"; \
	elif [ -f .git/hooks/pre-commit ] && grep -q "pre-commit" .git/hooks/pre-commit 2>/dev/null; then \
		echo "   • Pre-commit hooks already installed, adding custom hooks..."; \
		git config core.hooksPath .githooks; \
	else \
		echo "   • Installing both pre-commit and custom hooks..."; \
		git config --unset-all core.hooksPath || true; \
		pre-commit install; \
		git config core.hooksPath .githooks; \
	fi
	@echo ""
	@echo "✅ Development environment ready!"
	@echo ""
	@echo "Git hooks status:"
	@if git config --get core.hooksPath >/dev/null 2>&1; then \
		echo "  � Custom hooks: ACTIVE (changelog validation on push)"; \
	else \
		echo "  📋 Custom hooks: disabled"; \
	fi
	@if [ -f .git/hooks/pre-commit ]; then \
		echo "  🔍 Pre-commit: ACTIVE (code formatting & linting on commit)"; \
	else \
		echo "  🔍 Pre-commit: disabled"; \
	fi
	@echo ""
	@echo "To change hook configuration:"
	@echo "  - Pre-commit only: git config --unset-all core.hooksPath && pre-commit install"
	@echo "  - Custom hooks only: pre-commit uninstall && git config core.hooksPath .githooks"
	@echo "  - Both (recommended): git config core.hooksPath .githooks && pre-commit install --allow-missing-config"

# ---- Git Tag helpers ----
deploy-pre-release:
	@echo "Deploying pre-release tag..."
	@scripts/deploy_tag.sh pre-release

deploy-main-release:
	@echo "Deploying main release tag..."
	@scripts/deploy_tag.sh main-release

# ---- Sigstore signature verification ----
verify-signatures:
	@echo "Verifying Sigstore signatures for BundleCraft releases..."
	@echo ""
	@if ! command -v cosign &> /dev/null; then \
		echo "❌ cosign not found. Please install it:"; \
		echo "   macOS: brew install cosign"; \
		echo "   Linux: https://docs.sigstore.dev/cosign/installation/"; \
		exit 1; \
	fi
	@echo "✅ cosign is installed"
	@echo ""
	@echo "Fetching latest release tag..."
	@LATEST_TAG=$$(git describe --tags --abbrev=0 2>/dev/null || echo ""); \
	if [ -z "$$LATEST_TAG" ]; then \
		echo "❌ No git tags found. Please create a release first."; \
		exit 1; \
	fi; \
	echo "Latest release: $$LATEST_TAG"; \
	echo ""; \
	echo "Verifying container image signature..."; \
	IMAGE="ghcr.io/bundlecraft-io/bundlecraft:$${LATEST_TAG#v}"; \
	echo "Image: $$IMAGE"; \
	cosign verify "$$IMAGE" \
		--certificate-identity-regexp="https://github.com/bundlecraft-io/bundlecraft" \
		--certificate-oidc-issuer=https://token.actions.githubusercontent.com \
		|| { echo "❌ Signature verification failed"; exit 1; }; \
	echo ""; \
	echo "✅ All signatures verified successfully!"

# ---- CI helpers ----
ci-install-dev:
	python -m pip install --upgrade pip
	pip install -e ".[dev]"

ci-test:
	pytest -v --cov=bundlecraft --cov-report=term

ci-lint:
	ruff check bundlecraft tests

# ---- Dependency lock file management ----
lock-requirements:
	@echo "📦 Generating requirements lock file..."
	@if ! command -v pip-compile >/dev/null 2>&1; then \
		echo "❌ pip-tools not found."; \
		echo "Run: pip install -e \".[dev]\" (or: make setup-dev)"; \
		exit 1; \
	fi
	pip-compile pyproject.toml --output-file=requirements-lock.txt --resolver=backtracking --strip-extras
	@echo "✅ requirements-lock.txt generated successfully"
	@echo "📝 Review the changes and commit the updated file"

sync-requirements:
	@echo "🔄 Syncing environment with lock file..."
	@if ! command -v pip-sync >/dev/null 2>&1; then \
		echo "❌ pip-tools not found."; \
		echo "Run: pip install -e \".[dev]\" (or: make setup-dev)"; \
		exit 1; \
	fi
	@if [ ! -f requirements-lock.txt ]; then \
		echo "❌ requirements-lock.txt not found. Run 'make lock-requirements' first."; \
		exit 1; \
	fi
	pip-sync requirements-lock.txt
	pip install -e ".[dev]"
	@echo "✅ Environment synced with lock file"

validate-lock:
	@echo "🔍 Validating requirements lock file..."
	@if [ ! -f requirements-lock.txt ]; then \
		echo "❌ requirements-lock.txt not found. Run 'make lock-requirements' first."; \
		exit 1; \
	fi
	@if ! command -v pip-compile >/dev/null 2>&1; then \
		echo "❌ pip-tools not found."; \
		echo "Run: pip install -e \".[dev]\" (or: make setup-dev)"; \
		exit 1; \
	fi
	@# Check if lock file is a placeholder
	@if grep -q "IMPORTANT: This file must be properly generated" requirements-lock.txt; then \
		echo "⚠️  Lock file is a placeholder - skipping validation"; \
		echo "Run 'make lock-requirements' to generate the actual lock file"; \
		exit 0; \
	fi
	@# Check if lock file is up to date by generating and comparing
	@echo "Generating temporary lock file for comparison..."
	@pip-compile --quiet pyproject.toml --output-file=requirements-lock-check.txt --resolver=backtracking --strip-extras 2>&1 | grep -v "^#" || true
	@grep -v '^#' requirements-lock.txt | grep -v '^$$' | sort > requirements-lock-current.tmp
	@grep -v '^#' requirements-lock-check.txt | grep -v '^$$' | sort > requirements-lock-new.tmp
	@if diff -u requirements-lock-current.tmp requirements-lock-new.tmp > /dev/null 2>&1; then \
		echo "✅ Lock file is up-to-date"; \
		rm -f requirements-lock-check.txt requirements-lock-current.tmp requirements-lock-new.tmp; \
	else \
		echo "❌ Lock file is out of date!"; \
		echo ""; \
		echo "To fix this, run:"; \
		echo "  make lock-requirements"; \
		rm -f requirements-lock-check.txt requirements-lock-current.tmp requirements-lock-new.tmp; \
		exit 1; \
	fi

update-lock:
	@echo "🔄 Updating all dependencies in lock file..."
	@if ! command -v pip-compile >/dev/null 2>&1; then \
		echo "❌ pip-tools not found."; \
		echo "Run: pip install -e \".[dev]\" (or: make setup-dev)"; \
		exit 1; \
	fi
	pip-compile --upgrade pyproject.toml --output-file=requirements-lock.txt --resolver=backtracking --strip-extras
	@echo "✅ requirements-lock.txt updated with latest versions"
	@echo "📝 Review the changes and test thoroughly before committing"

# Regenerate lock file from scratch (useful when resolver gets confused)
regenerate-lock:
	@echo "♻️  Regenerating lock file from scratch..."
	@if ! command -v pip-compile >/dev/null 2>&1; then \
		echo "❌ pip-tools not found."; \
		echo "Run: pip install -e \".[dev]\" (or: make setup-dev)"; \
		exit 1; \
	fi
	rm -f requirements-lock.txt
	pip-compile pyproject.toml --output-file=requirements-lock.txt --resolver=backtracking --strip-extras
	@echo "✅ Lock file regenerated from scratch"
