"""Pydantic v2 data models for Coreboot4All device records and build manifests."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FlashChip(BaseModel):
    """Physical SPI flash chip description."""

    model_config = ConfigDict(extra="forbid")

    position: str = Field(..., min_length=1)
    size_mib: int = Field(..., gt=0)
    package: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    regions: list[str] = Field(..., min_length=1)


class PlatformInfo(BaseModel):
    """Hardware platform properties for a device."""

    model_config = ConfigDict(extra="forbid")

    cpu_vendor: Literal["intel", "amd", "arm", "riscv", "qemu"]
    cpu_family: str = Field(..., min_length=1)
    chipset: str = Field(..., min_length=1)
    superio: str | None = None
    ec: str | None = None
    flash_chips: list[FlashChip] = Field(default_factory=list)
    flash_size_mib: int = Field(..., gt=0)
    flash_package: str = Field(..., min_length=1)
    regions: list[str] = Field(..., min_length=1)


class CorebootInfo(BaseModel):
    """coreboot build configuration metadata for a device."""

    model_config = ConfigDict(extra="forbid")

    mainboard_path: str | None = None
    in_tree: bool
    chipset_supported: bool = True
    sibling_mainboard: str | None = None
    public_datasheet: bool = True
    coreboot_tag: str = Field(..., min_length=1)
    payload: Literal["seabios", "edk2", "linuxboot", "none"]
    payload_complete: bool = True
    ram_init: str = Field(..., min_length=1)
    graphics_init: str = Field(..., min_length=1)
    blobs_required: list[str] = Field(default_factory=list)
    defconfig: str | None = None


class BootGuardBlocker(BaseModel):
    """Intel Boot Guard status and dated evidence."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["disabled", "measured", "verified", "unknown"]
    source: str = Field(..., min_length=1)


class PsbBlocker(BaseModel):
    """AMD Platform Secure Boot fuse status and dated evidence."""

    model_config = ConfigDict(extra="forbid")

    fused: bool
    source: str = Field(..., min_length=1)


class RecoveryInfo(BaseModel):
    """Flashing and recovery capabilities."""

    model_config = ConfigDict(extra="forbid")

    external_programmer: bool
    internal_flash: bool
    write_protect_screw: bool = False
    tested: bool = False
    tested_date: str | None = None
    notes: str = Field(..., min_length=1)


class BlockersInfo(BaseModel):
    """Hardware and firmware blockers."""

    model_config = ConfigDict(extra="forbid")

    boot_guard: BootGuardBlocker
    psb: PsbBlocker
    arm_signed_bootrom: bool = False
    recovery: RecoveryInfo


class StatusInfo(BaseModel):
    """Computed tier, score, and verification state."""

    model_config = ConfigDict(extra="forbid")

    tier: Literal["A", "B", "C", "D"]
    score: int = Field(..., ge=0, le=100)
    score_flags: list[str] = Field(default_factory=list)
    build_verified: bool
    hardware_tested: bool
    last_build: str | None = None
    last_test: str | None = None


class ArtifactsInfo(BaseModel):
    """Build and raw data artifact references."""

    model_config = ConfigDict(extra="forbid")

    manifest: str | None = None
    rom_sha256: str | None = None
    raw_files: list[str] = Field(default_factory=list)

    @field_validator("rom_sha256")
    @classmethod
    def check_sha256(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("rom_sha256 must be 64 lowercase hex characters")
        return value


class SourceLink(BaseModel):
    """External documentation or commit reference."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(..., min_length=1)
    note: str = Field(..., min_length=1)


class MaintainerInfo(BaseModel):
    """Device record maintainer."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    contact: str = Field(..., min_length=1)


class DeviceRecord(BaseModel):
    """Top-level Coreboot4All device record schema (version 1)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    id: str = Field(..., pattern=r"^[a-z0-9_]+$")
    vendor: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    year: int = Field(..., ge=2000, le=2035)
    category: Literal["laptop", "desktop", "server", "sbc", "chromebook", "emulation"]
    platform: PlatformInfo
    coreboot: CorebootInfo
    blockers: BlockersInfo
    status: StatusInfo
    artifacts: ArtifactsInfo
    sources: list[SourceLink] = Field(..., min_length=1)
    maintainer: MaintainerInfo


class ManifestBuildInfo(BaseModel):
    """Build execution metadata."""

    model_config = ConfigDict(extra="forbid")

    started_utc: str
    finished_utc: str
    host_arch: str
    container_image: str
    container_digest: str


class ManifestSourceInfo(BaseModel):
    """Source provenance metadata."""

    model_config = ConfigDict(extra="forbid")

    coreboot_tag: str
    coreboot_commit: str
    blobs_commit: str
    payload: str
    payload_commit: str
    config_sha256: str


class ManifestToolchainInfo(BaseModel):
    """Toolchain provenance metadata."""

    model_config = ConfigDict(extra="forbid")

    sdk_image: str
    sdk_digest: str
    gcc_version: str


class ManifestOutputInfo(BaseModel):
    """ROM output metadata."""

    model_config = ConfigDict(extra="forbid")

    rom: str
    size_bytes: int = Field(..., gt=0)
    sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    cbfs_entries: list[str]


class ManifestReproducibleInfo(BaseModel):
    """Reproducibility check metadata."""

    model_config = ConfigDict(extra="forbid")

    build_timeless: bool
    second_build_sha256: str | None = None
    match: bool


class ManifestVerificationInfo(BaseModel):
    """Boot and hardware verification metadata."""

    model_config = ConfigDict(extra="forbid")

    qemu_boot: Literal["pass", "fail", "not_applicable"]
    hardware_tested: bool


class BuildManifest(BaseModel):
    """Top-level build manifest schema (version 1)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    device_id: str = Field(..., pattern=r"^[a-z0-9_]+$")
    build: ManifestBuildInfo
    source: ManifestSourceInfo
    toolchain: ManifestToolchainInfo
    output: ManifestOutputInfo
    reproducible: ManifestReproducibleInfo
    verification: ManifestVerificationInfo
