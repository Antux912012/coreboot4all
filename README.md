# Coreboot4All

Coreboot4All turns coreboot firmware knowledge into a repeatable, testable workflow.

## What it provides

1. **Device Catalog (`devices/`)**: Versioned YAML records with deterministic portability scores (`0`–`100`), tiers (`A`–`D`), and dated hardware blocker evidence.
2. **Build Orchestrator (`cb4a`)**: Reproducible containerized coreboot ROM builds with `BUILD_TIMELESS=1`, `SOURCE_DATE_EPOCH`, offline verification, and provenance manifests.
3. **Flash & Recovery Kit Generator**: Device-specific Markdown procedures with 3-read SHA-256 backups, dual-chip splitting, and recovery instructions.
4. **Static Catalog Site (`site/`)**: Zero-JavaScript, offline-capable HTML catalog including a dedicated Tier D (blocked) page.

## Quick Start

```bash
make doctor
make validate
make test
make image
make fetch
make build ID=emulation_qemu_q35
make offline ID=emulation_qemu_q35
make catalog
```

See [the build plan](https://github.com/Antux912012/coreboot4all) and `docs/` for details.
