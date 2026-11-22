"""Unit tests for the cb4a CLI."""

from pathlib import Path

from typer.testing import CliRunner

from cb4a.cli import app

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parent.parent


def test_cli_version() -> None:
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "cb4a 0.1.0" in res.stdout


def test_cli_validate_and_catalog(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(REPO_ROOT)
    res = runner.invoke(app, ["validate", "--strict"])
    assert res.exit_code == 0

    site_dir = tmp_path / "site"
    res_cat = runner.invoke(app, ["catalog", "--out", str(site_dir)])
    assert res_cat.exit_code == 0
    index_html = (site_dir / "index.html").read_text(encoding="utf-8")
    assert "<script" not in index_html.lower()
    assert "http://" not in index_html.lower()
    assert "https://" not in index_html.lower()
    assert (site_dir / "tier-d.html").exists()


def test_cli_flashkit_x230_and_tier_d(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(REPO_ROOT)
    res_ok = runner.invoke(app, ["flashkit", "--id", "lenovo_x230", "--method", "external"])
    assert res_ok.exit_code == 0
    kit_md = (REPO_ROOT / "out" / "kits" / "lenovo_x230" / "flash_external.md").read_text(
        encoding="utf-8"
    )
    assert "8 MiB" in kit_md
    assert "4 MiB" in kit_md

    res_blocked = runner.invoke(
        app, ["flashkit", "--id", "dell_latitude_7490_blocked", "--method", "external"]
    )
    assert res_blocked.exit_code == 24
