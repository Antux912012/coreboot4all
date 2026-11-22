"""Safe official BIOS revert planner and executor."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from cb4a.manifest import sha256_file
from cb4a.model import DeviceRecord


class RevertError(Exception):
    """Raised when a revert check or flash operation cannot proceed safely."""


@dataclass(frozen=True)
class RevertPlan:
    """Validated revert plan with exact flashrom command and backup digest."""

    device_id: str
    method: Literal["internal", "external"]
    backup_path: Path
    backup_sha256: str
    backup_size_bytes: int
    command: list[str]
    warnings: list[str]


def register_backup(backup_path: Path, expected_size_mib: int, registry_path: Path) -> dict:
    """Verify backup size and write a SHA-256 backup descriptor JSON."""
    if not backup_path.exists():
        raise RevertError(f"Backup image not found: {backup_path}")

    size_bytes = backup_path.stat().st_size
    expected_bytes = expected_size_mib * 1024 * 1024
    if size_bytes != expected_bytes:
        raise RevertError(
            f"Backup size mismatch: {size_bytes} bytes != expected {expected_bytes} bytes "
            f"({expected_size_mib} MiB)"
        )

    digest = sha256_file(backup_path)
    meta = {
        "schema_version": 1,
        "backup_path": str(backup_path.resolve()),
        "size_bytes": size_bytes,
        "sha256": digest,
    }
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def build_revert_plan(
    record: DeviceRecord,
    backup_path: Path,
    method: Literal["internal", "external"],
    expected_sha256: str | None = None,
    programmer: str = "ch341a_spi",
) -> RevertPlan:
    """Validate an official vendor BIOS backup and construct the exact revert command."""
    if not backup_path.exists():
        raise RevertError(f"Official BIOS backup not found: {backup_path}")

    size_bytes = backup_path.stat().st_size
    expected_bytes = record.platform.flash_size_mib * 1024 * 1024
    if size_bytes != expected_bytes:
        raise RevertError(
            f"Backup size {size_bytes} bytes does not match {record.id} flash size "
            f"({expected_bytes} bytes / {record.platform.flash_size_mib} MiB)."
        )

    actual_sha = sha256_file(backup_path)
    if expected_sha256 and actual_sha != expected_sha256.lower():
        raise RevertError(
            f"Backup SHA-256 mismatch: actual {actual_sha} != expected {expected_sha256.lower()}"
        )

    warnings: list[str] = [
        "Verify AC power (internal revert) or remove all batteries and AC (external programmer).",
        "Never pass --noverify to flashrom.",
    ]

    if method == "internal":
        cmd = [
            "sudo",
            "flashrom",
            "-p",
            "internal",
            "--ifd",
            "-i",
            "bios",
            "-w",
            str(backup_path),
        ]
        warnings.append(
            "Internal revert requires coreboot with an unlocked IFD and unlocked BIOS_CNTL. "
            "After booting back into official Lenovo firmware, BLE/SMM_BWP will re-lock."
        )
    else:
        cmd = [
            "sudo",
            "flashrom",
            "-p",
            programmer,
            "-w",
            str(backup_path),
        ]
        warnings.append(
            "Verify programmer VCC is 3.3 V with a multimeter before attaching the SOIC-8 clip."
        )

    return RevertPlan(
        device_id=record.id,
        method=method,
        backup_path=backup_path,
        backup_sha256=actual_sha,
        backup_size_bytes=size_bytes,
        command=cmd,
        warnings=warnings,
    )


def execute_revert_plan(plan: RevertPlan, execute: bool = False) -> int:
    """Execute revert command only when execute=True; otherwise dry-run."""
    if not execute:
        return 0
    if shutil.which("flashrom") is None:
        raise RevertError("flashrom is not installed on the host OS.")
    proc = subprocess.run(plan.command, check=False)
    return proc.returncode
