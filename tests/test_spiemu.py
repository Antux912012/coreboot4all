"""Tests for the virtual 3.3 V SPI programmer emulator."""

from __future__ import annotations

import socket
import struct
import threading
from pathlib import Path

import pytest

from cb4a.spiemu import (
    LENOVO_EC_START,
    MX25L12805D_JEDEC,
    MX25L12805D_SIZE,
    S_ACK,
    S_CMD_O_SPIOP,
    S_CMD_Q_IFACE,
    S_CMD_SYNCNOP,
    S_NAK,
    VirtualFlashStats,
    VirtualMX25L12805D,
    VirtualProgrammerServer,
    VoltageError,
)


def test_voltage_guard_rejects_5v(tmp_path: Path) -> None:
    with pytest.raises(VoltageError):
        VirtualMX25L12805D(tmp_path / "chip.bin", voltage_mv=5000)


def test_ec_region_guard_blocks_write_and_erase(tmp_path: Path) -> None:
    chip = VirtualMX25L12805D(tmp_path / "chip.bin", voltage_mv=3300, protect_ec=True)
    # WREN + 4 KiB sector erase at LENOVO_EC_START
    chip.spi_transact(b"\x06", 0)
    with pytest.raises(Exception, match="LENOVO_EC"):
        chip.spi_transact(b"\x20" + LENOVO_EC_START.to_bytes(3, "big"), 0)
    assert chip.stats.ec_violations == 1

    # Writing to 0x830000 (COREBOOT area) succeeds with 1->0 semantics
    chip.spi_transact(b"\x06", 0)
    chip.spi_transact(b"\x02" + (0x830000).to_bytes(3, "big") + b"\xde\xad\xbe\xef", 0)
    out = chip.spi_transact(b"\x03" + (0x830000).to_bytes(3, "big"), 4)
    assert out == b"\xde\xad\xbe\xef"
    assert chip.ec_sha256() == chip.initial_ec_sha256


def test_serprog_tcp_roundtrip(tmp_path: Path) -> None:
    chip = VirtualMX25L12805D(tmp_path / "chip.bin", voltage_mv=3300, protect_ec=True)
    assert chip.image_path.stat().st_size == MX25L12805D_SIZE

    server = VirtualProgrammerServer("127.0.0.1", 0, chip)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
            sock.sendall(bytes([S_CMD_SYNCNOP]))
            assert sock.recv(2) == bytes([S_NAK, S_ACK])

            sock.sendall(bytes([S_CMD_Q_IFACE]))
            resp = sock.recv(3)
            assert resp[0] == S_ACK and struct.unpack("<H", resp[1:])[0] == 1

            # RDID (0x9F)
            sock.sendall(bytes([S_CMD_O_SPIOP]) + (1).to_bytes(3, "little") + (3).to_bytes(3, "little") + b"\x9f")
            rdid = sock.recv(4)
            assert rdid[0] == S_ACK and rdid[1:] == MX25L12805D_JEDEC
            assert isinstance(chip.stats, VirtualFlashStats)
    finally:
        server.shutdown()
        server.server_close()
