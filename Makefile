SHELL := /bin/bash
export CB4A_UID := $(shell id -u)
export CB4A_GID := $(shell id -g)
ID ?= emulation_qemu_q35
CB4A_JOBS ?= 4

HAS_COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo yes || echo no)
IS_PODMAN := $(shell docker info 2>/dev/null | grep -qi podman && echo yes || echo no)
RUN_USER_FLAGS := $(if $(filter yes,$(IS_PODMAN)),--userns=keep-id,--user $(CB4A_UID):$(CB4A_GID))
PODMAN_NET_FLAGS := $(if $(filter yes,$(IS_PODMAN)),--network=host,)

define RUN_BUILDER
$(if $(filter yes,$(HAS_COMPOSE)),\
	docker compose run --rm builder $(1),\
	docker volume inspect cb4a_ccache >/dev/null 2>&1 || docker volume create cb4a_ccache >/dev/null; \
	docker volume inspect cb4a_sources >/dev/null 2>&1 || docker volume create cb4a_sources >/dev/null; \
	docker run --rm $(RUN_USER_FLAGS) $(PODMAN_NET_FLAGS) -w /work \
		-v "$(CURDIR)":/work \
		-v cb4a_ccache:/cache/ccache \
		-v cb4a_sources:/cache/sources \
		-e SOURCE_DATE_EPOCH=1700000000 \
		-e CB4A_CACHE_DIR=/cache \
		-e CB4A_JOBS="$(CB4A_JOBS)" \
		cb4a/builder:26.09 $(1))
endef

define RUN_BUILDER_OFFLINE
$(if $(filter yes,$(HAS_COMPOSE)),\
	docker compose --profile offline run --rm builder-offline $(1),\
	docker volume inspect cb4a_ccache >/dev/null 2>&1 || docker volume create cb4a_ccache >/dev/null; \
	docker volume inspect cb4a_sources >/dev/null 2>&1 || docker volume create cb4a_sources >/dev/null; \
	docker run --rm $(RUN_USER_FLAGS) --network none -w /work \
		-v "$(CURDIR)":/work \
		-v cb4a_ccache:/cache/ccache \
		-v cb4a_sources:/cache/sources \
		-e SOURCE_DATE_EPOCH=1700000000 \
		-e CB4A_CACHE_DIR=/cache \
		-e CB4A_JOBS="$(CB4A_JOBS)" \
		cb4a/builder:26.09 $(1))
endef

.PHONY: help image image-tools fetch validate test build offline kit catalog qemu-test clean doctor

help:
	@echo "make image        Build the builder image"
	@echo "make image-tools  Build the tools image"
	@echo "make fetch        Fetch pinned coreboot and payload sources"
	@echo "make validate     Validate all device records"
	@echo "make test         Run the Python tests"
	@echo "make build ID=lenovo_x230   Build one device"
	@echo "make offline ID=lenovo_x230 Build without a network"
	@echo "make kit ID=lenovo_x230     Generate the flash kit"
	@echo "make catalog      Generate the static site"
	@echo "make qemu-test    Boot-test the emulation_qemu_q35 ROM"
	@echo "make doctor       Check the environment"

image:
ifeq ($(HAS_COMPOSE),yes)
	docker compose build builder
else
	docker build $(PODMAN_NET_FLAGS) -f docker/builder.Dockerfile -t cb4a/builder:26.09 .
endif

image-tools:
ifeq ($(HAS_COMPOSE),yes)
	docker compose build tools
else
	docker build $(PODMAN_NET_FLAGS) -f docker/tools.Dockerfile -t cb4a/tools:1.0 .
endif

fetch:
	$(call RUN_BUILDER,bash scripts/fetch-sources.sh)

validate:
	$(call RUN_BUILDER,cb4a validate)

test:
	$(call RUN_BUILDER,pytest -q)

build:
	$(call RUN_BUILDER,cb4a build --id "$(ID)")

offline:
	$(call RUN_BUILDER_OFFLINE,cb4a build --id "$(ID)" --offline)

kit:
	$(call RUN_BUILDER,cb4a flashkit --id "$(ID)")

catalog:
	$(call RUN_BUILDER,cb4a catalog --out site)

qemu-test:
	bash scripts/verify-rom.sh emulation_qemu_q35

doctor:
	$(call RUN_BUILDER,cb4a doctor)

clean:
	rm -rf out site
