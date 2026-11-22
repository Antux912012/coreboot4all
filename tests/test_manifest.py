"""Unit tests for manifest writing, scrubbing, and ROM verification."""

from pathlib import Path

import pytest

from cb4a.manifest import scrub_check, verify_rom_against_manifest, write_manifest, write_sha256sums
from cb4a.model import (
    BuildManifest,
    ManifestBuildInfo,
    ManifestOutputInfo,
    ManifestReproducibleInfo,
    ManifestSourceInfo,
    ManifestToolchainInfo,
    ManifestVerificationInfo,
)


def test_scrub_check_rejects_email_and_mac() -> None:
    with pytest.raises(ValueError, match="email"):
        scrub_check('{"note": "owner@example.com"}')
    with pytest.raises(ValueError, match="MAC"):
        scrub_check('{"note": "00:11:22:33:44:55"}')


def test_write_and_verify_manifest(tmp_path: Path) -> None:
    rom = tmp_path / "coreboot.rom"
    rom.write_bytes(b"coreboot-test-rom")
    digest = write_sha256sums(rom, tmp_path / "SHA256SUMS")

    manifest = BuildManifest(
        schema_version=1,
        device_id="emulation_qemu_q35",
        build=ManifestBuildInfo(
            started_utc="2026-11-22T10:00:00Z",
            finished_utc="2026-11-22T10:01:00Z",
            host_arch="x86_64",
            container_image="cb4a/builder:26.09",
            container_digest="sha256:" + ("a" * 64),
        ),
        source=ManifestSourceInfo(
            coreboot_tag="26.09",
            coreboot_commit="b" * 40,
            blobs_commit="c" * 40,
            payload="seabios",
            payload_commit="d" * 40,
            config_sha256="e" * 64,
        ),
        toolchain=ManifestToolchainInfo(
            sdk_image="coreboot/coreboot-sdk:2026-09-27_97eb3c4d52",
            sdk_digest="sha256:" + ("f" * 64),
            gcc_version="i386-elf-gcc (GCC) 14.2.0",
        ),
        output=ManifestOutputInfo(
            rom="out/builds/emulation_qemu_q35/coreboot.rom",
            size_bytes=len(b"coreboot-test-rom"),
            sha256=digest,
            cbfs_entries=["fallback/romstage", "fallback/ramstage"],
        ),
        reproducible=ManifestReproducibleInfo(
            build_timeless=True,
            second_build_sha256=digest,
            match=True,
        ),
        verification=ManifestVerificationInfo(
            qemu_boot="pass",
            hardware_tested=False,
        ),
    )

    manifest_path = tmp_path / "manifest.json"
    write_manifest(manifest, manifest_path)
    ok, actual, expected = verify_rom_against_manifest(rom, manifest_path)
    assert ok is True
    assert actual == expected
