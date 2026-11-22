"""coreboot build pipeline orchestrator (stages B0 to B8)."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from cb4a.manifest import sha256_file, write_manifest, write_sha256sums
from cb4a.model import (
    BuildManifest,
    DeviceRecord,
    ManifestBuildInfo,
    ManifestOutputInfo,
    ManifestReproducibleInfo,
    ManifestSourceInfo,
    ManifestToolchainInfo,
    ManifestVerificationInfo,
)
from cb4a.records import validate_record_rules


class BuildStageError(Exception):
    """Build failure carrying a stable cb4a exit code."""

    def __init__(self, exit_code: int, message: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _run_logged(
    cmd: list[str], cwd: Path, log_handle, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    log_handle.write(f"$ {' '.join(cmd)}\n")
    log_handle.flush()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log_handle.write(proc.stdout)
    log_handle.flush()
    return proc


def _read_commit_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return "0" * 40


def _first_line(cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
        return out.splitlines()[0].strip() if out else "unknown"
    except Exception:
        return "unknown"


def _parse_cbfs_entries(cbfs_text: str) -> list[str]:
    entries: list[str] = []
    in_table = False
    for line in cbfs_text.splitlines():
        if line.startswith("Name ") and "Offset" in line:
            in_table = True
            continue
        if in_table:
            stripped = line.strip()
            if not stripped:
                continue
            name = stripped.split()[0]
            if name != "(empty)":
                entries.append(name)
    return entries


def run_build(
    record: DeviceRecord,
    record_path: Path,
    repo_root: Path,
    jobs: int = 4,
    offline: bool = False,
    payload_override: str | None = None,
) -> BuildManifest:
    """Execute build stages B0 through B8 for one device record."""
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cache_dir = Path(os.environ.get("CB4A_CACHE_DIR", "/cache"))
    sources_dir = cache_dir / "sources"
    coreboot_dir = sources_dir / "coreboot"

    build_dir = repo_root / "out" / "builds" / record.id
    obj_dir = build_dir / "obj"
    log_path = repo_root / "out" / "logs" / f"{record.id}.build.log"
    build_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as log:
        # B0: Check record and tier.
        log.write(f"[B0] Validating {record.id} (tier {record.status.tier})\n")
        errors = validate_record_rules(record, record_path)
        if errors:
            raise BuildStageError(20, "; ".join(errors))
        if record.status.tier != "A" or not record.coreboot.defconfig:
            raise BuildStageError(
                24, f"E-24: {record.id} is tier {record.status.tier}; only Tier A builds"
            )

        defconfig_path = repo_root / record.coreboot.defconfig
        if not defconfig_path.exists():
            raise BuildStageError(26, f"E-26: Missing defconfig {defconfig_path}")

        # B1: Verify coreboot source tree at pinned tag.
        log.write(f"[B1] Checking coreboot source at {coreboot_dir}\n")
        if not (coreboot_dir / ".git").exists():
            raise BuildStageError(
                26, f"E-26: Missing coreboot source tree at {coreboot_dir}. Run make fetch."
            )

        # B2: Verify submodules and pre-fetched external payloads.
        log.write("[B2] Checking submodules and payload trees\n")
        required_paths = [
            coreboot_dir / "3rdparty" / "blobs",
            coreboot_dir / "3rdparty" / "libgfxinit",
        ]
        payload_name = payload_override or record.coreboot.payload
        if payload_name == "seabios":
            required_paths.append(
                coreboot_dir / "payloads" / "external" / "SeaBIOS" / "seabios"
            )
        elif payload_name == "edk2":
            required_paths.append(
                coreboot_dir / "payloads" / "external" / "edk2" / "workspace"
            )

        for req in required_paths:
            if offline and (not req.exists() or not any(req.iterdir())):
                raise BuildStageError(
                    26, f"E-26: Offline build missing required source path: {req}"
                )

        # B3: Isolated obj dir + DOTCONFIG + make olddefconfig.
        log.write("[B3] Configuring coreboot via make olddefconfig\n")
        if obj_dir.exists():
            shutil.rmtree(obj_dir)
        obj_dir.mkdir(parents=True, exist_ok=True)
        dotconfig = build_dir / ".config"
        shutil.copy2(defconfig_path, dotconfig)

        env = os.environ.copy()
        env.update(
            {
                "LANG": "C",
                "LC_ALL": "C",
                "TZ": "UTC0",
                "SOURCE_DATE_EPOCH": env.get("SOURCE_DATE_EPOCH", "1700000000"),
            }
        )

        proc = _run_logged(
            ["make", f"DOTCONFIG={dotconfig}", f"obj={obj_dir}", "olddefconfig"],
            coreboot_dir,
            log,
            env=env,
        )
        if proc.returncode != 0:
            raise BuildStageError(22, f"E-22: make olddefconfig failed for {record.id}")

        # B4: Build ROM with BUILD_TIMELESS=1.
        log.write("[B4] Building coreboot.rom with BUILD_TIMELESS=1\n")
        proc = _run_logged(
            [
                "make",
                f"-j{jobs}",
                "BUILD_TIMELESS=1",
                f"DOTCONFIG={dotconfig}",
                f"obj={obj_dir}",
            ],
            coreboot_dir,
            log,
            env=env,
        )
        built_rom = obj_dir / "coreboot.rom"
        if proc.returncode != 0 or not built_rom.exists():
            raise BuildStageError(22, f"E-22: coreboot build failed for {record.id}")

        rom_out = build_dir / "coreboot.rom"
        shutil.copy2(built_rom, rom_out)

        # B5: Inspect FMAP and CBFS contents.
        log.write("[B5] Inspecting ROM layout and CBFS\n")
        cbfstool_bin = shutil.which("cbfstool") or str(obj_dir / "cbfstool")
        cbfs_txt = build_dir / "cbfs.txt"
        layout_proc = _run_logged([cbfstool_bin, str(rom_out), "layout"], coreboot_dir, log)
        print_proc = _run_logged([cbfstool_bin, str(rom_out), "print"], coreboot_dir, log)
        cbfs_combined = (
            f"=== FMAP LAYOUT ===\n{layout_proc.stdout}\n"
            f"=== CBFS PRINT ===\n{print_proc.stdout}"
        )
        cbfs_txt.write_text(cbfs_combined, encoding="utf-8")

        # B6: Calculate SHA-256 checksums.
        log.write("[B6] Writing SHA256SUMS\n")
        rom_sha = write_sha256sums(rom_out, build_dir / "SHA256SUMS")

        # B8: QEMU verification only for emulation/qemu-* targets.
        qemu_status = "not_applicable"
        if record.coreboot.mainboard_path and record.coreboot.mainboard_path.startswith(
            "emulation/qemu-"
        ):
            qemu_bin = shutil.which("qemu-system-x86_64")
            qemu_log = build_dir / "qemu.log"
            if qemu_bin:
                machine = "pc" if "i440fx" in record.coreboot.mainboard_path else "q35"
                qproc = subprocess.run(
                    [
                        "timeout",
                        "10s",
                        qemu_bin,
                        "-M",
                        machine,
                        "-bios",
                        str(rom_out),
                        "-serial",
                        "stdio",
                        "-display",
                        "none",
                        "-no-reboot",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                qemu_log.write_text(qproc.stdout, encoding="utf-8")
                qemu_status = (
                    "pass"
                    if ("coreboot-" in qproc.stdout or "SeaBIOS" in qproc.stdout)
                    else "fail"
                )
            else:
                qemu_log.write_text(
                    "qemu-system-x86_64 not installed in builder container; "
                    "run make qemu-test on host.\n",
                    encoding="utf-8",
                )

        # B7: Write manifest.json.
        finished = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest = BuildManifest(
            schema_version=1,
            device_id=record.id,
            build=ManifestBuildInfo(
                started_utc=started,
                finished_utc=finished,
                host_arch=platform.machine(),
                container_image=f"cb4a/builder:{record.coreboot.coreboot_tag}",
                container_digest="sha256:" + ("0" * 64),
            ),
            source=ManifestSourceInfo(
                coreboot_tag=record.coreboot.coreboot_tag,
                coreboot_commit=_read_commit_file(sources_dir / "coreboot.commit"),
                blobs_commit=_read_commit_file(sources_dir / "blobs.commit"),
                payload=payload_name,
                payload_commit=_read_commit_file(sources_dir / f"{payload_name}.commit"),
                config_sha256=sha256_file(dotconfig),
            ),
            toolchain=ManifestToolchainInfo(
                sdk_image="coreboot/coreboot-sdk:2026-09-27_97eb3c4d52",
                sdk_digest="sha256:" + ("0" * 64),
                gcc_version=_first_line(["i386-elf-gcc", "--version"]),
            ),
            output=ManifestOutputInfo(
                rom=f"out/builds/{record.id}/coreboot.rom",
                size_bytes=rom_out.stat().st_size,
                sha256=rom_sha,
                cbfs_entries=_parse_cbfs_entries(print_proc.stdout),
            ),
            reproducible=ManifestReproducibleInfo(
                build_timeless=True,
                second_build_sha256=None,
                match=False,
            ),
            verification=ManifestVerificationInfo(
                qemu_boot=qemu_status,
                hardware_tested=record.status.hardware_tested,
            ),
        )
        write_manifest(manifest, build_dir / "manifest.json")
        return manifest
