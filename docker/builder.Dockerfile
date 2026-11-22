# syntax=docker/dockerfile:1.7
# Coreboot4All build image.
# Pin the base image by tag. The digest goes into env/digests.env.

ARG COREBOOT_SDK=docker.io/coreboot/coreboot-sdk:2026-09-27_97eb3c4d52
FROM ${COREBOOT_SDK}

LABEL org.opencontainers.image.title="cb4a-builder"
LABEL org.opencontainers.image.description="Reproducible coreboot build environment for Coreboot4All"
LABEL org.opencontainers.image.licenses="GPL-2.0-or-later"
LABEL org.opencontainers.image.source="https://github.com/Antux912012/coreboot4all"

USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# The SDK image has the cross toolchain in /opt/xgcc.
# Add only the packages that the orchestrator needs.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        jq \
        python3 \
        python3-venv \
        python3-pip \
        unzip \
        xz-utils \
        zstd \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=C \
    LC_ALL=C \
    TZ=UTC0 \
    CCACHE_DIR=/cache/ccache \
    CCACHE_MAXSIZE=10G \
    XDG_CACHE_HOME=/cache/xdg \
    CB4A_CACHE_DIR=/cache \
    PYTHONPATH=/work/src \
    PATH=/opt/cb4a-venv/bin:/opt/xgcc/bin:${PATH}

# Install the orchestrator dependencies in an isolated environment.
# The versions must match pyproject.toml exactly.
RUN python3 -m venv /opt/cb4a-venv \
 && /opt/cb4a-venv/bin/pip install --no-cache-dir --upgrade pip==24.3.1 \
 && /opt/cb4a-venv/bin/pip install --no-cache-dir \
        "typer==0.15.1" \
        "pydantic==2.10.4" \
        "PyYAML==6.0.2" \
        "Jinja2==3.1.5" \
        "rich==13.9.4" \
        "pytest==8.3.4" \
        "pytest-cov==6.0.0" \
        "ruff==0.8.4"

# Provide the cb4a CLI entry point that loads the bind-mounted /work/src tree.
RUN printf '%s\n' \
        '#!/usr/bin/env bash' \
        'exec /opt/cb4a-venv/bin/python -m cb4a "$@"' \
        > /opt/cb4a-venv/bin/cb4a \
 && chmod 0755 /opt/cb4a-venv/bin/cb4a

# Create cache mount points with permissions for mapped host uid/gid.
RUN mkdir -p /cache/ccache /cache/sources /cache/xdg \
 && chmod 0777 /cache /cache/ccache /cache/sources /cache/xdg

COPY docker/entrypoint.sh /usr/local/bin/cb4a-entrypoint
RUN chmod 0755 /usr/local/bin/cb4a-entrypoint

WORKDIR /work
# The SDK image creates the user "coreboot" (uid 1000).
# Compose overrides the uid and gid at run time to match the host user.
USER coreboot

ENTRYPOINT ["/usr/local/bin/cb4a-entrypoint"]
CMD ["cb4a", "--help"]
