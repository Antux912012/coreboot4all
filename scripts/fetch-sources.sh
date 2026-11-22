#!/usr/bin/env bash
# Fetch the coreboot source at the pinned tag, real submodules, and external payloads.
set -euo pipefail

: "${CB4A_CACHE_DIR:=/cache}"
COREBOOT_TAG="${COREBOOT_TAG:-26.09}"
SRC="${CB4A_CACHE_DIR}/sources"
DEST="${SRC}/coreboot"

mkdir -p "${SRC}"

if [ ! -d "${DEST}/.git" ]; then
  git clone --depth 1 --branch "${COREBOOT_TAG}" https://review.coreboot.org/coreboot.git "${DEST}"
fi

cd "${DEST}"
git fetch --tags --depth 1 origin "refs/tags/${COREBOOT_TAG}:refs/tags/${COREBOOT_TAG}"
git checkout --detach "${COREBOOT_TAG}"

# Initialize real coreboot Git submodules (3rdparty/blobs has update=none in .gitmodules).
git submodule update --init --checkout --depth 1 \
  3rdparty/blobs \
  3rdparty/libgfxinit \
  3rdparty/vboot \
  3rdparty/intel-microcode

# SeaBIOS is an external payload Makefile, not a Git submodule.
# Pre-fetch SeaBIOS into payloads/external/SeaBIOS/seabios for offline builds.
SEABIOS_DIR="${DEST}/payloads/external/SeaBIOS/seabios"
SEABIOS_REV="$(grep -E '^TAG-\$\(CONFIG_SEABIOS_STABLE\)=' payloads/external/SeaBIOS/Makefile | head -n 1 | cut -d= -f2 || true)"
if [ ! -d "${SEABIOS_DIR}/.git" ]; then
  git clone https://review.coreboot.org/seabios.git "${SEABIOS_DIR}"
fi
git -C "${SEABIOS_DIR}" fetch --all --tags
if [ -n "${SEABIOS_REV}" ]; then
  git -C "${SEABIOS_DIR}" checkout --detach "${SEABIOS_REV}"
fi

git rev-parse HEAD > "${SRC}/coreboot.commit"
git -C 3rdparty/blobs rev-parse HEAD > "${SRC}/blobs.commit"
git -C 3rdparty/libgfxinit rev-parse HEAD > "${SRC}/libgfxinit.commit"
git -C "${SEABIOS_DIR}" rev-parse HEAD > "${SRC}/seabios.commit"

echo "Sources are in ${DEST}"
