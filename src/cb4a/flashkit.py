"""Flash and recovery kit generator."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape

from cb4a.model import DeviceRecord


class FlashKitError(Exception):
    """Raised when a device or flash method is unsupported."""


def _jinja_env() -> Environment:
    template_dir = Path(__file__).parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=("html", "j2")),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def generate_flashkit(
    record: DeviceRecord,
    method: Literal["external", "internal"],
    out_dir: Path,
) -> list[Path]:
    """Render flash and recovery Markdown procedures into out_dir."""
    if record.status.tier == "D":
        raise FlashKitError(f"E-24: {record.id} is Tier D (blocked); flashing is forbidden.")

    if method == "external" and not record.blockers.recovery.external_programmer:
        raise FlashKitError(f"E-24: {record.id} does not support external programmer flashing.")
    if method == "internal" and not record.blockers.recovery.internal_flash:
        raise FlashKitError(f"E-24: {record.id} does not support internal flashing.")

    env = _jinja_env()
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = {"device": record, "dual_chip": len(record.platform.flash_chips) >= 2}

    flash_tpl = env.get_template(
        "flash_external.md.j2" if method == "external" else "flash_internal.md.j2"
    )
    recover_tpl = env.get_template("recover.md.j2")

    flash_path = out_dir / f"flash_{method}.md"
    recover_path = out_dir / "recover.md"

    flash_path.write_text(flash_tpl.render(**ctx) + "\n", encoding="utf-8")
    recover_path.write_text(recover_tpl.render(**ctx) + "\n", encoding="utf-8")
    return [flash_path, recover_path]
