"""Unit tests for YAML record loading and rule validation."""

from pathlib import Path

from cb4a.records import load_all_records, load_record, validate_record_rules

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_all_seed_records_valid() -> None:
    records, errors = load_all_records(REPO_ROOT / "devices", strict=True)
    assert not errors
    assert len(records) >= 5


def test_missing_date_in_blocker_source_rejected() -> None:
    path = REPO_ROOT / "devices" / "lenovo" / "x230.yaml"
    rec = load_record(path)
    rec.blockers.boot_guard.source = "intelmetool output without date"
    errors = validate_record_rules(rec, path)
    assert any("YYYY-MM-DD" in e for e in errors)


def test_score_mismatch_rejected() -> None:
    path = REPO_ROOT / "devices" / "lenovo" / "x230.yaml"
    rec = load_record(path)
    rec.status.score = 1
    errors = validate_record_rules(rec, path)
    assert any("status.score" in e for e in errors)
