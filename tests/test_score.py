"""Unit tests for the deterministic portability score and tier engine."""

from pathlib import Path

from cb4a.records import load_record
from cb4a.score import compute_score_and_tier

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_tier_a_qemu_score() -> None:
    rec = load_record(REPO_ROOT / "devices" / "emulation" / "qemu_q35.yaml")
    res = compute_score_and_tier(rec)
    assert res.tier == "A"
    assert res.score == 95


def test_tier_a_x230_score() -> None:
    rec = load_record(REPO_ROOT / "devices" / "lenovo" / "x230.yaml")
    res = compute_score_and_tier(rec)
    assert res.tier == "A"
    assert res.score == 90


def test_tier_d_boot_guard_zero_score() -> None:
    rec = load_record(REPO_ROOT / "devices" / "dell" / "latitude_7490_blocked.yaml")
    res = compute_score_and_tier(rec)
    assert res.tier == "D"
    assert res.score == 0
    assert "SD-01:boot_blocker" in res.flags


def test_no_recovery_forces_tier_d() -> None:
    rec = load_record(REPO_ROOT / "devices" / "lenovo" / "x230.yaml")
    rec.blockers.recovery.external_programmer = False
    rec.blockers.recovery.internal_flash = False
    res = compute_score_and_tier(rec)
    assert res.tier == "D"
    assert res.score == 0
    assert "SD-02:no_recovery" in res.flags


def test_maximum_score_is_100() -> None:
    rec = load_record(REPO_ROOT / "devices" / "emulation" / "qemu_q35.yaml")
    rec.status.build_verified = True
    res = compute_score_and_tier(rec)
    assert res.score == 100
