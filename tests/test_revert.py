"""Unit tests for the safe official BIOS revert utility."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cb4a.cli import app
from cb4a.manifest import sha256_file
from cb4a.records import load_record
from cb4a.revert import RevertError, build_revert_plan, register_backup

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parent.parent


def test_revert_plan_dry_run_and_sha_check(tmp_path: Path) -> None:
    rec = load_record(REPO_ROOT / "devices" / "lenovo" / "thinkpad_13_gen2.yaml")
    backup = tmp_path / "official_R0JET48W.rom"
    backup.write_bytes(b"\xff" * (16 * 1024 * 1024))
    digest = sha256_file(backup)

    meta = register_backup(backup, 16, tmp_path / "backup_meta.json")
    assert meta["sha256"] == digest

    plan = build_revert_plan(rec, backup, method="internal", expected_sha256=digest)
    assert plan.backup_sha256 == digest
    assert "--ifd" in plan.command
    assert "bios" in plan.command

    with pytest.raises(RevertError, match="SHA-256 mismatch"):
        build_revert_plan(rec, backup, method="external", expected_sha256="0" * 64)


def test_revert_cli_dry_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(REPO_ROOT)
    backup = tmp_path / "official_16m.rom"
    backup.write_bytes(b"\xaa" * (16 * 1024 * 1024))
    res = runner.invoke(
        app,
        [
            "revert",
            "--id",
            "lenovo_thinkpad_13_gen2",
            "--backup",
            str(backup),
            "--method",
            "external",
        ],
    )
    assert res.exit_code == 0
    assert "Dry-run complete" in res.stdout
