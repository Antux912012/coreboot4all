"""Typer command line interface for Coreboot4All."""

from __future__ import annotations

import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cb4a import __version__
from cb4a.build import BuildStageError, run_build
from cb4a.catalog import generate_catalog
from cb4a.flashkit import FlashKitError, generate_flashkit
from cb4a.manifest import verify_rom_against_manifest, write_sha256sums
from cb4a.records import export_json_schema, load_all_records
from cb4a.score import compute_score_and_tier

app = typer.Typer(
    name="cb4a",
    help="Coreboot4All device catalog, build orchestrator, and flash kit generator.",
    no_args_is_help=True,
)
catalog_app = typer.Typer(help="Generate and inspect the static device catalog.")
app.add_typer(catalog_app, name="catalog")

console = Console()


def _repo_root() -> Path:
    return Path.cwd()


def _find_device(device_id: str, repo_root: Path):
    records, _ = load_all_records(repo_root / "devices")
    for path, rec in records:
        if rec.id == device_id:
            return path, rec
    console.print(f"[red]E-21: Device '{device_id}' not found.[/red]")
    raise typer.Exit(code=21)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"cb4a {__version__}")
        raise typer.Exit(code=0)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", callback=_version_callback, is_eager=True, help="Print version and exit."
    ),
) -> None:
    """Coreboot4All CLI."""


@app.command()
def validate(
    path: Path = typer.Option(Path("devices"), "--path", help="Path to device records directory."),
    strict: bool = typer.Option(False, "--strict", help="Verify Tier A defconfig files exist."),
) -> None:
    """Validate all YAML device records."""
    repo_root = _repo_root()
    target = path if path.is_absolute() else repo_root / path
    records, errors = load_all_records(target, strict=strict)

    log_path = repo_root / "out" / "logs" / "validation.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "\n".join(errors) + ("\n" if errors else "Validation OK\n"), encoding="utf-8"
    )

    if errors:
        for err in errors:
            console.print(f"[red]E-20: {err}[/red]")
        raise typer.Exit(code=20)

    export_json_schema(repo_root / "src" / "cb4a" / "data" / "schema.json")
    console.print(f"[green]Validated {len(records)} device record(s) successfully.[/green]")


@app.command()
def score(
    device_id: str = typer.Option(..., "--id", help="Device record ID."),
) -> None:
    """Print computed portability score and tier for a device."""
    _, rec = _find_device(device_id, _repo_root())
    res = compute_score_and_tier(rec)
    typer.echo(f"id={rec.id} tier={res.tier} score={res.score} flags={','.join(res.flags)}")


@app.command()
def build(
    device_id: str = typer.Option(..., "--id", help="Device record ID."),
    jobs: int = typer.Option(int(os.environ.get("CB4A_JOBS", "4")), "--jobs", help="Make jobs."),
    offline: bool = typer.Option(False, "--offline", help="Require all sources locally."),
    payload: Optional[str] = typer.Option(None, "--payload", help="Override payload name."),
) -> None:
    """Build the coreboot ROM for one Tier A device."""
    repo_root = _repo_root()
    path, rec = _find_device(device_id, repo_root)
    try:
        manifest = run_build(
            rec, path, repo_root, jobs=jobs, offline=offline, payload_override=payload
        )
    except BuildStageError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=exc.exit_code)
    console.print(
        f"[green]Built {manifest.output.rom} ({manifest.output.size_bytes} bytes, "
        f"sha256={manifest.output.sha256})[/green]"
    )


@app.command()
def manifest(
    device_id: str = typer.Option(..., "--id", help="Device record ID."),
    rom: Path = typer.Option(..., "--rom", help="Path to built ROM."),
) -> None:
    """Write SHA256SUMS for a ROM and verify against an existing manifest."""
    repo_root = _repo_root()
    _find_device(device_id, repo_root)
    if not rom.exists():
        console.print(f"[red]E-23: ROM not found at {rom}[/red]")
        raise typer.Exit(code=23)
    build_dir = repo_root / "out" / "builds" / device_id
    digest = write_sha256sums(rom, build_dir / "SHA256SUMS")
    manifest_path = build_dir / "manifest.json"
    if manifest_path.exists():
        ok, actual, expected = verify_rom_against_manifest(rom, manifest_path)
        if not ok:
            console.print(f"[red]E-23: SHA-256 mismatch: {actual} != {expected}[/red]")
            raise typer.Exit(code=23)
    typer.echo(f"sha256={digest}")


@app.command()
def verify(
    device_id: str = typer.Option(..., "--id", help="Device record ID."),
    rom: Path = typer.Option(..., "--rom", help="Path to ROM image."),
) -> None:
    """Compare a ROM image against its build manifest."""
    repo_root = _repo_root()
    _find_device(device_id, repo_root)
    manifest_path = repo_root / "out" / "builds" / device_id / "manifest.json"
    if not rom.exists() or not manifest_path.exists():
        console.print("[red]E-23: ROM or manifest.json is missing.[/red]")
        raise typer.Exit(code=23)
    ok, actual, expected = verify_rom_against_manifest(rom, manifest_path)
    if not ok:
        console.print(f"[red]E-23: Checksum mismatch ({actual} != {expected}).[/red]")
        raise typer.Exit(code=23)
    console.print(f"[green]Verified {rom} (sha256={actual}).[/green]")


class FlashMethod(str, Enum):
    external = "external"
    internal = "internal"


class CatalogFormat(str, Enum):
    html = "html"
    json = "json"


@app.command()
def flashkit(
    device_id: str = typer.Option(..., "--id", help="Device record ID."),
    method: FlashMethod = typer.Option(
        FlashMethod.external, "--method", help="Flashing method."
    ),
) -> None:
    """Generate flash and recovery Markdown procedures."""
    repo_root = _repo_root()
    _, rec = _find_device(device_id, repo_root)
    out_dir = repo_root / "out" / "kits" / device_id
    try:
        files = generate_flashkit(rec, method.value, out_dir)
    except FlashKitError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=24)
    for item in files:
        console.print(f"[green]Wrote {item}[/green]")


@catalog_app.callback(invoke_without_command=True)
def catalog_generate(
    ctx: typer.Context,
    out: Path = typer.Option(Path("site"), "--out", help="Output directory for static site."),
    fmt: CatalogFormat = typer.Option(CatalogFormat.html, "--format", help="Output format."),
) -> None:
    """Generate the static HTML and JSON device catalog."""
    if ctx.invoked_subcommand is not None:
        return
    repo_root = _repo_root()
    records, errors = load_all_records(repo_root / "devices")
    if errors:
        for err in errors:
            console.print(f"[red]E-20: {err}[/red]")
        raise typer.Exit(code=20)
    out_dir = out if out.is_absolute() else repo_root / out
    generate_catalog([rec for _, rec in records], out_dir, fmt=fmt.value)
    console.print(f"[green]Generated catalog for {len(records)} device(s) in {out_dir}.[/green]")


@catalog_app.command("count")
def catalog_count() -> None:
    """Print the number of device records for each tier."""
    repo_root = _repo_root()
    records, errors = load_all_records(repo_root / "devices")
    if errors:
        for err in errors:
            console.print(f"[red]E-20: {err}[/red]")
        raise typer.Exit(code=20)
    counts = {tier: sum(1 for _, r in records if r.status.tier == tier) for tier in "ABCD"}
    table = Table(title="Coreboot4All Catalog Counts")
    table.add_column("Tier")
    table.add_column("Count", justify="right")
    for tier in "ABCD":
        table.add_row(tier, str(counts[tier]))
    table.add_row("Total", str(len(records)))
    console.print(table)


@app.command()
def doctor() -> None:
    """Check the host or container build environment."""
    tools = ["python3", "git", "make"]
    in_container = Path("/opt/xgcc/bin").exists()
    if in_container:
        tools.extend(["i386-elf-gcc", "iasl", "gnatmake"])
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        console.print(f"[red]E-25: Missing tools: {', '.join(missing)}[/red]")
        raise typer.Exit(code=25)
    console.print("[green]Environment check passed.[/green]")
