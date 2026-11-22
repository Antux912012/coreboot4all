# syntax=docker/dockerfile:1.7
# Coreboot4All hardware tool image (multi-stage).
# Stage 1 compiles coreboot utilities. Stage 2 contains no compiler.

ARG COREBOOT_TAG=26.09
ARG FLASHPROG_TAG=v1.4

FROM docker.io/library/debian:trixie-slim AS util-builder

ARG COREBOOT_TAG
ARG FLASHPROG_TAG
ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        git \
        libfdt-dev \
        libftdi1-dev \
        libpci-dev \
        libusb-1.0-0-dev \
        pkg-config \
        zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

# Build coreboot inspection and porting utilities from the pinned tag.
RUN git clone --depth 1 --branch "${COREBOOT_TAG}" \
        https://review.coreboot.org/coreboot.git /src/coreboot \
 && git -C /src/coreboot submodule update --init --checkout --depth 1 3rdparty/vboot \
 && make -C /src/coreboot/util/cbfstool -j"$(nproc)" cbfstool fmaptool rmodtool \
 && make -C /src/coreboot/util/ifdtool -j"$(nproc)" \
 && make -C /src/coreboot/util/intelmetool -j"$(nproc)" \
 && make -C /src/coreboot/util/inteltool -j"$(nproc)" \
 && make -C /src/coreboot/util/amdtool -j"$(nproc)" \
 && make -C /src/coreboot/util/superiotool -j"$(nproc)" \
 && make -C /src/coreboot/util/ectool -j"$(nproc)" \
 && make -C /src/coreboot/util/cbmem -j"$(nproc)" \
 && mkdir -p /out/bin \
 && cp /src/coreboot/util/cbfstool/cbfstool \
       /src/coreboot/util/cbfstool/fmaptool \
       /src/coreboot/util/ifdtool/ifdtool \
       /src/coreboot/util/intelmetool/build/intelmetool \
       /src/coreboot/util/inteltool/inteltool \
       /src/coreboot/util/amdtool/amdtool \
       /src/coreboot/util/superiotool/superiotool \
       /src/coreboot/util/ectool/ectool \
       /src/coreboot/util/cbmem/cbmem \
       /src/coreboot/util/me_cleaner/me_cleaner.py \
       /out/bin/ \
 && chmod 0755 /out/bin/*

# Build flashprog from its pinned release tag as an alternative to flashrom.
RUN git clone --depth 1 --branch "${FLASHPROG_TAG}" \
        https://review.sourcearcade.org/flashprog.git /src/flashprog \
 && make -C /src/flashprog -j"$(nproc)" CONFIG_ENABLE_LIBPCI_PROGRAMMERS=yes CONFIG_LINUX_GPIO_SPI=no CONFIG_JLINK_SPI=no \
 && cp /src/flashprog/flashprog /out/bin/flashprog \
 && chmod 0755 /out/bin/flashprog

FROM docker.io/library/debian:trixie-slim

LABEL org.opencontainers.image.title="cb4a-tools"
LABEL org.opencontainers.image.description="Flash and inspect tools for Coreboot4All"
LABEL org.opencontainers.image.licenses="GPL-2.0-or-later"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        acpica-tools \
        ca-certificates \
        dmidecode \
        flashrom \
        git \
        jq \
        libftdi1-2 \
        libpci3 \
        libusb-1.0-0 \
        minisign \
        pciutils \
        python3 \
        usbutils \
        zlib1g \
 && rm -rf /var/lib/apt/lists/*

COPY --from=util-builder /out/bin/ /usr/local/bin/

RUN useradd -m -u 1000 cb4a
USER cb4a
WORKDIR /work
CMD ["bash"]
