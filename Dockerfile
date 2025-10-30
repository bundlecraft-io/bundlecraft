FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc && rm -rf /var/lib/apt/lists/*
ARG HATCH_BUILD_VERSION=0.0.0+docker
ENV HATCH_BUILD_VERSION=${HATCH_BUILD_VERSION}
# Fallbacks for setuptools-scm/hatch-vcs when .git is not available
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${HATCH_BUILD_VERSION}
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BUNDLECRAFT=${HATCH_BUILD_VERSION}
COPY pyproject.toml README.md ./
COPY bundlecraft/ ./bundlecraft/
RUN pip install --no-cache-dir build && python -m build --wheel

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl && rm -rf /var/lib/apt/lists/*
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
RUN useradd -m -u 1000 bundlecraft
USER bundlecraft
ENTRYPOINT ["bundlecraft"]
