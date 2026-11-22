"""YAML device record loading, rule validation, and schema export."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from cb4a.model import DeviceRecord
from cb4a.score import compute_score_and_tier

DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


class RecordValidationError(Exception):
    """Raised when one or more device records fail validation."""


def discover_record_files(devices_dir: Path) -> list[Path]:
    """Return sorted YAML record paths under devices_dir."""
    if not devices_dir.exists():
        return []
    return sorted(
        [*devices_dir.rglob("*.yaml"), *devices_dir.rglob("*.yml")]
    )


def load_record(path: Path) -> DeviceRecord:
    """Load and schema-validate one YAML device record."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RecordValidationError(f"{path}: YAML root must be a mapping")
    try:
        return DeviceRecord.model_validate(raw)
    except ValidationError as exc:
        raise RecordValidationError(f"{path}: {exc}") from exc


def validate_record_rules(record: DeviceRecord, path: Path) -> list[str]:
    """Check business rules 3-10 from Chapter 4.4 and return error messages."""
    errors: list[str] = []

    computed = compute_score_and_tier(record)
    if record.status.score != computed.score:
        errors.append(
            f"{path}: status.score={record.status.score} does not match "
            f"computed score {computed.score} (flags={computed.flags})"
        )
    if record.status.tier != computed.tier:
        errors.append(
            f"{path}: status.tier={record.status.tier} does not match "
            f"computed tier {computed.tier}"
        )

    if record.status.tier == "A":
        if not record.coreboot.mainboard_path or not record.coreboot.defconfig:
            errors.append(f"{path}: Tier A record requires mainboard_path and defconfig")
        if not (
            record.blockers.recovery.external_programmer
            or record.blockers.recovery.internal_flash
        ):
            errors.append(
                f"{path}: Tier A record requires external_programmer or internal_flash"
            )

    if record.status.build_verified and not record.artifacts.rom_sha256:
        errors.append(f"{path}: build_verified=true requires artifacts.rom_sha256")

    if not DATE_RE.search(record.blockers.boot_guard.source):
        errors.append(f"{path}: blockers.boot_guard.source must include YYYY-MM-DD date")
    if not DATE_RE.search(record.blockers.psb.source):
        errors.append(f"{path}: blockers.psb.source must include YYYY-MM-DD date")

    return errors


def load_all_records(
    devices_dir: Path, strict: bool = False
) -> tuple[list[tuple[Path, DeviceRecord]], list[str]]:
    """Load and validate all records under devices_dir."""
    records: list[tuple[Path, DeviceRecord]] = []
    errors: list[str] = []
    seen_ids: dict[str, Path] = {}

    for path in discover_record_files(devices_dir):
        try:
            rec = load_record(path)
        except RecordValidationError as exc:
            errors.append(str(exc))
            continue

        if rec.id in seen_ids:
            errors.append(
                f"{path}: duplicate id '{rec.id}' (already seen in {seen_ids[rec.id]})"
            )
        else:
            seen_ids[rec.id] = path

        errors.extend(validate_record_rules(rec, path))
        if strict and rec.status.tier == "A" and rec.coreboot.defconfig:
            defconfig_path = devices_dir.parent / rec.coreboot.defconfig
            if not defconfig_path.exists():
                errors.append(f"{path}: missing defconfig {rec.coreboot.defconfig}")

        records.append((path, rec))

    if not records and not errors:
        errors.append(f"No device records found under {devices_dir}")

    return records, errors


def export_json_schema(output_path: Path) -> None:
    """Write JSON Schema generated from DeviceRecord to output_path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = DeviceRecord.model_json_schema()
    output_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
