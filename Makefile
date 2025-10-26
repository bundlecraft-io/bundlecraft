CONTAINER ?= podman
HATCH_BUILD_VERSION ?= 0.0.0+local
IMAGE_NAME ?= bundlecraft
IMAGE_TAG ?= local
IMAGE_REF ?= localhost/$(IMAGE_NAME):$(IMAGE_TAG)

# Optional: reference to the published test image on GHCR
GHCR_IMAGE ?= ghcr.io/bundlecraft-io/bundlecraft-test
GHCR_TAG ?= latest
GHCR_IMAGE_REF ?= $(GHCR_IMAGE):$(GHCR_TAG)

# Release helpers: derive version from latest git tag
# - GIT_TAG is used as the image tag (e.g. v1.2.3)
# - VERSION is HATCH_BUILD_VERSION (strips leading 'v' for PEP 440)
GIT_TAG ?= $(shell git describe --tags --abbrev=0 2>/dev/null)
VERSION ?= $(shell echo "$(GIT_TAG)" | sed 's/^v//')
RELEASE_IMAGE_REF ?= localhost/$(IMAGE_NAME):$(GIT_TAG)

.PHONY: test-image release-image test-image-run test-image-build-dev test-image-verify-dev \
	ghcr-test-image-run ghcr-test-image-build-dev ghcr-test-image-verify-dev help

help:
	@echo "Container targets:"
	@echo "  release-image           Build image using latest git tag (HATCH_BUILD_VERSION from tag)"
	@echo "  test-image              Build image tagged 'local' with HATCH_BUILD_VERSION=0.0.0+local"
	@echo "  test-image-run          Show bundlecraft --version using test image"
	@echo "  test-image-build-dev    Build dev bundles in container using test image"
	@echo "  test-image-verify-dev   Verify dev bundles in container using test image"
	@echo "  ghcr-test-image-run     Run GHCR test image (default: $(GHCR_IMAGE_REF)) --version"
	@echo "  ghcr-test-image-build-dev  Build dev bundles using GHCR test image (mounts PWD)"
	@echo "  ghcr-test-image-verify-dev Verify dev bundles using GHCR test image"

test-image:
	$(CONTAINER) build --build-arg HATCH_BUILD_VERSION=$(HATCH_BUILD_VERSION) -t $(IMAGE_REF) .

# Build a release image tagged with the latest git tag.
# - Uses $(GIT_TAG) for the image tag.
# - Uses $(VERSION) (without leading 'v') for HATCH_BUILD_VERSION inside the wheel.
release-image:
	@test -n "$(GIT_TAG)" || (echo "No git tag found. Create a tag (e.g. v1.2.3) or call: make release-image GIT_TAG=v1.2.3" >&2; exit 1)
	$(CONTAINER) build \
	  --build-arg HATCH_BUILD_VERSION=$(VERSION) \
	  -t $(RELEASE_IMAGE_REF) \
	  .

test-image-run: image
	$(CONTAINER) run --rm $(IMAGE_REF) --version

test-image-build-dev: image
	$(CONTAINER) run --rm \
	  --userns=keep-id \
	  -v "$(CURDIR):/workspace:Z" \
	  -w /workspace \
	  $(IMAGE_REF) \
	  build --env dev --verbose --force

test-image-verify-dev: image
	$(CONTAINER) run --rm \
	  --userns=keep-id \
	  -v "$(CURDIR):/workspace:Z" \
	  -w /workspace \
	  $(IMAGE_REF) \
	  verify --target dist/dev/custom/internal --verify-all

# --- GHCR test image helpers ---
ghcr-test-image-run:
	$(CONTAINER) run --rm $(GHCR_IMAGE_REF) --version

ghcr-test-image-build-dev:
	$(CONTAINER) run --rm \
	  --userns=keep-id \
	  -v "$(CURDIR):/workspace:Z" \
	  -w /workspace \
	  $(GHCR_IMAGE_REF) \
	  build --env dev --verbose --force

ghcr-test-image-verify-dev:
	$(CONTAINER) run --rm \
	  --userns=keep-id \
	  -v "$(CURDIR):/workspace:Z" \
	  -w /workspace \
	  $(GHCR_IMAGE_REF) \
	  verify --target dist/dev/custom/internal --verify-all
