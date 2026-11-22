"""Pure deterministic portability score and tier engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cb4a.model import DeviceRecord

EXTERNAL_PACKAGES = {"soic8", "soic16", "dip8", "header"}
BLOBS_PENALTY = {"me", "psp", "fsp", "agesa"}


@dataclass(frozen=True)
class ScoreResult:
    """Computed tier, portability score, and reason flags."""

    tier: Literal["A", "B", "C", "D"]
    score: int
    flags: list[str]


def compute_score_and_tier(record: DeviceRecord) -> ScoreResult:
    """Compute the deterministic tier (A-D) and portability score (0-100)."""
    flags: list[str] = []

    boot_guard_blocked = record.blockers.boot_guard.state == "verified"
    psb_blocked = record.blockers.psb.fused
    arm_blocked = record.blockers.arm_signed_bootrom
    active_boot_blocker = boot_guard_blocked or psb_blocked or arm_blocked

    has_recovery = (
        record.blockers.recovery.external_programmer
        or record.blockers.recovery.internal_flash
    )

    if active_boot_blocker:
        flags.append("SD-01:boot_blocker")
    if not has_recovery:
        flags.append("SD-02:no_recovery")

    if active_boot_blocker or not has_recovery:
        return ScoreResult(tier="D", score=0, flags=flags)

    # Determine tier per Chapter 3.2 decision procedure.
    if record.coreboot.in_tree and record.coreboot.mainboard_path:
        tier: Literal["A", "B", "C", "D"] = "A"
    elif record.coreboot.chipset_supported and record.coreboot.sibling_mainboard:
        tier = "B"
    elif record.coreboot.public_datasheet:
        tier = "C"
    else:
        flags.append("SD-03:no_data")
        return ScoreResult(tier="D", score=0, flags=flags)

    # Calculate score criteria SC-01 to SC-09 (max 100).
    points = 0
    if record.coreboot.in_tree and record.coreboot.mainboard_path:
        points += 35  # SC-01
        points += 15  # SC-02 (always true when mainboard is in tree)
        flags.extend(["SC-01", "SC-02"])
    elif record.coreboot.chipset_supported:
        points += 15  # SC-02
        flags.append("SC-02")

    # SC-03: No active hardware boot lock (+15).
    points += 15
    flags.append("SC-03")

    # SC-04: External programmer possible (+10).
    pkg = record.platform.flash_package.lower()
    if record.blockers.recovery.external_programmer and pkg in EXTERNAL_PACKAGES:
        points += 10
        flags.append("SC-04")

    # SC-05: Internal flash possible (+5).
    if record.blockers.recovery.internal_flash:
        points += 5
        flags.append("SC-05")

    # SC-06: EC support in tree or no EC (+5).
    if record.platform.ec is None or "/" in record.platform.ec:
        points += 5
        flags.append("SC-06")

    # SC-07: Payload support complete (+5).
    if record.coreboot.payload_complete:
        points += 5
        flags.append("SC-07")

    # SC-08: Verified build exists (+5).
    if record.status.build_verified:
        points += 5
        flags.append("SC-08")

    # SC-09: Low blob dependency (+5).
    blobs_lower = {b.lower() for b in record.coreboot.blobs_required}
    if not (blobs_lower & BLOBS_PENALTY):
        points += 5
        flags.append("SC-09")

    # Deductions SD-03 and SD-04.
    if not record.coreboot.public_datasheet:
        points -= 20
        flags.append("SD-03")

    if pkg == "wson" and not record.blockers.recovery.external_programmer:
        points -= 10
        flags.append("SD-04")

    score = max(0, min(100, points))
    return ScoreResult(tier=tier, score=score, flags=flags)
