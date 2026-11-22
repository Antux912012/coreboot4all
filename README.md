# Coreboot4All

Coreboot4All turns coreboot firmware knowledge into a repeatable, testable workflow: a versioned device catalog, a reproducible containerized build orchestrator (`cb4a`), flash/recovery kit generation, and an offline static catalog site.

> [!CAUTION]
> **FIRMWARE FLASHING CAN PERMANENTLY BRICK YOUR DEVICE.**
> - **Never flash a physical device without a 3-read SHA-256-verified backup** of your original SPI flash chip(s) and a **verified 3.3 V (or 1.8 V with level shifter) external SPI programmer** (e.g., Raspberry Pi, Pico `serprog`, FT2232H, or 3.3 V-modified CH341A). **Never connect an unmodified 5 V CH341A programmer to a 3.3 V or 1.8 V SPI flash chip.**
> - **Never write a BIOS-only `coreboot.rom` over the entire flash chip.** Unless your `defconfig` includes a valid Intel Flash Descriptor (`ifd.bin`), `me.bin`, and `gbe.bin`, you **must** flash only the BIOS region (`--ifd -i bios`) or preserve the lower regions so you do not brick the board or erase your Ethernet MAC address (`GbE`).
> - **Tier B / Experimental Ports (e.g., `ports/lenovo_thinkpad_13_gen2`):** Community/experimental Tier B ports have **not** been hardware-booted unless explicitly marked `hardware_tested: true` in their device record. Expect bring-up iterations and keep your external programmer ready before testing.
> - **Hardware Root of Trust (Tier D):** Devices with **Intel Boot Guard** (Verified mode), **AMD Platform Secure Boot (PSB)**, or fused ARM boot ROMs **cannot** run unsigned coreboot. Coreboot4All does not include or support hardware signature bypasses.
> - **No Proprietary Blobs in Git:** Never commit owner flash dumps, `.rom`, `.bin`, `.fd`, Intel ME/FSP, or AMD PSP/AGESA binaries to this repository.

## What It Provides

1. **Device Catalog (`devices/`)**: Versioned YAML records with deterministic portability scores (`0`–`100`), tiers (`A`–`D`), and dated hardware blocker evidence.
2. **Build Orchestrator (`cb4a`)**: Reproducible containerized coreboot `26.09` ROM builds (`BUILD_TIMELESS=1`, `SOURCE_DATE_EPOCH`, offline `network_mode: none` verification, and provenance manifests).
3. **Flash, Recovery & Revert Kits (`cb4a flashkit`, `cb4a revert`)**: Device-specific Markdown procedures with 3-read SHA-256 backups, dual-chip splitting, and SHA-256-verified official BIOS revert plans (dry-run by default).
4. **Experimental Port & Graphical Setup UI (`ports/`)**:
   - `ports/lenovo_thinkpad_13_gen2/`: Tier B coreboot `26.09` port for Lenovo ThinkPad 13 2nd Gen (`20J1003WGM`, Kaby Lake-U, Boot Guard disabled).
   - `ports/uefi_gui/AdwaitaSetupApp/`: EDK2 GOP graphical UEFI setup application styled after modern ThinkPad BIOS + GNOME Libadwaita / Pantheon HIG.
5. **Static Catalog Site (`site/`)**: Zero-JavaScript, offline-capable HTML catalog published at `https://antux912012.github.io/coreboot4all/`.

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

## Safe Revert Usage

```bash
# Dry-run (verifies 16 MiB size and SHA-256 without touching hardware):
cb4a revert --id lenovo_thinkpad_13_gen2 --backup /path/to/official_R0JET48W.rom --method external

# Only pass --execute after verifying programmer voltage (3.3 V) and backup checksum:
cb4a revert --id lenovo_thinkpad_13_gen2 --backup /path/to/official_R0JET48W.rom --method external --execute
```

## Licenses

- `cb4a` tooling and templates: `GPL-2.0-or-later` (see [LICENSE](LICENSE) and [LICENSES/](LICENSES/))
- Device catalog data (`devices/`) and docs (`docs/`): `CC-BY-4.0`
- Upstream coreboot: `GPL-2.0-only` (see upstream `COPYING`)
