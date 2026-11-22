"""Static HTML and JSON catalog generator (zero JavaScript, zero external assets)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from cb4a.model import DeviceRecord


def _jinja_env() -> Environment:
    template_dir = Path(__file__).parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=("html", "j2")),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def generate_catalog(
    records: list[DeviceRecord],
    out_dir: Path,
    fmt: str = "html",
) -> None:
    """Render static catalog HTML and/or JSON into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sorted_records = sorted(records, key=lambda r: (r.status.tier, -r.status.score, r.id))

    if fmt in ("json", "html"):
        catalog_json = {
            "schema_version": 1,
            "generated_utc": generated_utc,
            "count": len(sorted_records),
            "devices": [r.model_dump() for r in sorted_records],
        }
        (out_dir / "catalog.json").write_text(
            json.dumps(catalog_json, indent=2) + "\n", encoding="utf-8"
        )

    if fmt == "json":
        return

    env = _jinja_env()
    devices_out = out_dir / "devices"
    devices_out.mkdir(parents=True, exist_ok=True)

    counts = {tier: sum(1 for r in sorted_records if r.status.tier == tier) for tier in "ABCD"}
    tier_d_records = [r for r in sorted_records if r.status.tier == "D"]

    (out_dir / "index.html").write_text(
        env.get_template("index.html.j2").render(
            devices=sorted_records,
            counts=counts,
            generated_utc=generated_utc,
        ),
        encoding="utf-8",
    )

    (out_dir / "tier-d.html").write_text(
        env.get_template("tier_d.html.j2").render(
            devices=tier_d_records,
            generated_utc=generated_utc,
        ),
        encoding="utf-8",
    )

    record_tpl = env.get_template("record.html.j2")
    for rec in sorted_records:
        (devices_out / f"{rec.id}.html").write_text(
            record_tpl.render(device=rec, generated_utc=generated_utc),
            encoding="utf-8",
        )
