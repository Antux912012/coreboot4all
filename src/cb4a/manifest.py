"""Manifest generation, privacy scrubbing, and ROM verification."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from cb4a.model import BuildManifest

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")


def sha256_file(path: Path) -> str:
    """Return lowercase SHA-256 hex digest of path."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scrub_check(manifest_text: str) -> None:
    """Raise ValueError if manifest text contains forbidden personal or MAC data."""
    if EMAIL_RE.search(manifest_text):
        raise ValueError("Manifest contains an email address")
    if MAC_RE.search(manifest_text):
        raise ValueError("Manifest contains a MAC address")


def write_manifest(manifest: BuildManifest, output_path: Path) -> None:
    """Validate, scrub-check, and write manifest JSON."""
    payload = json.dumps(manifest.model_dump(), indent=2) + "\n"
    scrub_check(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(payload, encoding="utf-8")


def write_sha256sums(rom_path: Path, output_path: Path) -> str:
    """Calculate ROM SHA-256 and write SHA256SUMS."""
    digest = sha256_file(rom_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{digest}  {rom_path.name}\n", encoding="utf-8")
    return digest


def verify_rom_against_manifest(rom_path: Path, manifest_path: Path) -> tuple[bool, str, str]:
    """Compare ROM SHA-256 against manifest.output.sha256."""
    manifest = BuildManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    actual = sha256_file(rom_path)
    expected = manifest.output.sha256
    return actual == expected, actual, expected
