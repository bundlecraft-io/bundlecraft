CONTAINER ?= podman
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
	help

help:
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

build-test-image:
	$(CONTAINER) build --build-arg HATCH_BUILD_VERSION=$(HATCH_BUILD_VERSION) -t $(IMAGE_REF) .

# Build a release image tagged with the latest git tag.
# - Uses $(GIT_TAG) for the image tag.
# - Uses $(VERSION) (without leading 'v') for HATCH_BUILD_VERSION inside the wheel.
build-image:
	@test -n "$(GIT_TAG)" || (echo "No git tag found. Create a tag (e.g. v1.2.3) or call: make release-image GIT_TAG=v1.2.3" >&2; exit 1)
	$(CONTAINER) build \
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
	  --userns=keep-id \
	  -e BUNDLECRAFT_WORKSPACE=/workspace \
	  -e TRUST_JKS_PASSWORD="$(TRUST_JKS_PASSWORD)" \
	  -e TRUST_P12_PASSWORD="$(TRUST_P12_PASSWORD)" \
	  -v "$(BUNDLECRAFT_WORKSPACE):/workspace:Z" \
	  -w /workspace \
	  $(IMAGE_REF) \
	  build --env test-example-envconfig --verbose --force; \
	$(CONTAINER) run --rm \
	  --userns=keep-id \
	  -v "$(BUNDLECRAFT_WORKSPACE):/workspace:Z" \
	  -w /workspace \
	  $(IMAGE_REF) \
	  verify --target dist/.test-inline/test-inline --verify-all

test-image-run: build-test-image
	@set -e; \
	BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" scripts/prepare_test_configs.sh; \
	trap 'BUNDLECRAFT_WORKSPACE="$(BUNDLECRAFT_WORKSPACE)" scripts/prepare_test_configs.sh --cleanup' EXIT; \
	if [ -z "$(BUNDLECRAFT_ARGS)" ]; then \
	  echo "Usage: make test-image-run BUNDLECRAFT_ARGS='build --env dev --verbose'" >&2; \
	  exit 2; \
	fi; \
	$(CONTAINER) run --rm \
	  --userns=keep-id \
	  -e BUNDLECRAFT_WORKSPACE=/workspace \
	  -e TRUST_JKS_PASSWORD="$(TRUST_JKS_PASSWORD)" \
	  -e TRUST_P12_PASSWORD="$(TRUST_P12_PASSWORD)" \
	  -v "$(BUNDLECRAFT_WORKSPACE):/workspace:Z" \
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
	bundlecraft verify --target dist/.test-inline/test-inline --verify-all; \
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
