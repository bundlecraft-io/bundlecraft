FROM python:3.12-slim AS builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3-dev libc6-dev && \
    rm -rf /var/lib/apt/lists/*

# Set up virtual environment in builder
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Build arguments and environment
ARG HATCH_BUILD_VERSION=0.0.0+docker
ENV HATCH_BUILD_VERSION=${HATCH_BUILD_VERSION}
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${HATCH_BUILD_VERSION}
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BUNDLECRAFT=${HATCH_BUILD_VERSION}

# Copy dependency files for better layer caching
COPY requirements-lock.txt ./

# Install dependencies in builder stage (with compilation)
RUN pip install --no-cache-dir -r requirements-lock.txt

# Copy source and build wheel
COPY pyproject.toml README.md ./
COPY bundlecraft/ ./bundlecraft/
RUN pip install --no-cache-dir build && python -m build --wheel

# Install the built wheel (dependencies already installed)
RUN pip install --no-cache-dir dist/*.whl

# Final stage - copy the complete virtual environment
FROM python:3.12-slim
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy the entire virtual environment from builder (includes all dependencies + bundlecraft)
COPY --from=builder /opt/venv /opt/venv

# Create user
RUN useradd -m -u 1000 bundlecraft
USER bundlecraft
ENTRYPOINT ["bundlecraft"]
