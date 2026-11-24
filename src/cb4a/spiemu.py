"""Virtual 3.3 V SPI programmer emulator implementing the flashrom serprog TCP protocol.

Emulates a 16 MiB Macronix MX25L12805D (JEDEC ID 0xC2 0x20 0x18) SPI NOR flash
over TCP so `flashrom -p serprog:ip=127.0.0.1:<port>` can run 3-read backups,
layout-restricted BIOS flashes, EC-preservation checks, and `cb4a revert` dry
runs against a virtual flash image before touching physical hardware.
"""

from __future__ import annotations

import hashlib
import socketserver
import struct
import threading
from dataclasses import dataclass
from pathlib import Path

# serprog protocol constants (flashrom serprog.h)
S_ACK = 0x06
S_NAK = 0x15

S_CMD_NOP = 0x00
S_CMD_Q_IFACE = 0x01
S_CMD_Q_CMDMAP = 0x02
S_CMD_Q_PGMNAME = 0x03
S_CMD_Q_SERBUF = 0x04
S_CMD_Q_BUSTYPE = 0x05
S_CMD_SYNCNOP = 0x10
S_CMD_S_BUSTYPE = 0x12
S_CMD_O_SPIOP = 0x13
S_CMD_S_SPI_FREQ = 0x14
S_CMD_S_PIN_STATE = 0x15

BUS_SPI = 1 << 3

# MX25L12805D constants (16 MiB)
MX25L12805D_SIZE = 16 * 1024 * 1024
MX25L12805D_JEDEC = bytes([0xC2, 0x20, 0x18])
LENOVO_EC_START = 0x800000
LENOVO_EC_END = 0x830000


class VoltageError(ValueError):
    """Raised when the virtual programmer voltage does not match 3.3 V."""


class ProtectedRegionError(RuntimeError):
    """Raised when an erase/write attempts to modify a protected flash region."""


@dataclass
class VirtualFlashStats:
    reads: int = 0
    writes: int = 0
    erases: int = 0
    ec_violations: int = 0


class VirtualMX25L12805D:
    """In-memory + file-backed Macronix MX25L12805D SPI NOR flash state machine."""

    def __init__(
        self,
        image_path: Path,
        *,
        voltage_mv: int = 3300,
        protect_ec: bool = True,
        init_from: Path | None = None,
    ) -> None:
        if voltage_mv != 3300:
            raise VoltageError(
                f"Unsafe programmer voltage {voltage_mv} mV: MX25L12805D requires 3300 mV (3.3 V)."
            )
        self.image_path = image_path
        self.voltage_mv = voltage_mv
        self.protect_ec = protect_ec
        self.write_enabled = False
        self.status_reg = 0x00
        self.stats = VirtualFlashStats()
        self.lock = threading.Lock()

        if init_from is not None:
            raw = init_from.read_bytes()
            if len(raw) != MX25L12805D_SIZE:
                raise ValueError(
                    f"Expected {MX25L12805D_SIZE} bytes in {init_from}, got {len(raw)}"
                )
            self.data = bytearray(raw)
            self.flush()
        elif image_path.exists():
            raw = image_path.read_bytes()
            if len(raw) != MX25L12805D_SIZE:
                raise ValueError(
                    f"Expected {MX25L12805D_SIZE} bytes in {image_path}, got {len(raw)}"
                )
            self.data = bytearray(raw)
        else:
            self.data = bytearray([0xFF] * MX25L12805D_SIZE)
            self.flush()

        self.initial_ec_sha256 = self.ec_sha256()

    def ec_sha256(self) -> str:
        return hashlib.sha256(self.data[LENOVO_EC_START:LENOVO_EC_END]).hexdigest()

    def flush(self) -> None:
        self.image_path.parent.mkdir(parents=True, exist_ok=True)
        self.image_path.write_bytes(self.data)

    def _check_ec_guard(self, start: int, length: int) -> None:
        if not self.protect_ec:
            return
        end = start + length
        if start < LENOVO_EC_END and end > LENOVO_EC_START:
            self.stats.ec_violations += 1
            raise ProtectedRegionError(
                f"Blocked write/erase to protected LENOVO_EC region "
                f"(0x{start:06x}..0x{end:06x} overlaps 0x{LENOVO_EC_START:06x}..0x{LENOVO_EC_END:06x})."
            )

    def _erase_range(self, start: int, size: int) -> None:
        self._check_ec_guard(start, size)
        end = min(start + size, MX25L12805D_SIZE)
        self.data[start:end] = b"\xff" * (end - start)
        self.stats.erases += 1
        self.write_enabled = False

    def spi_transact(self, tx: bytes, rx_len: int) -> bytes:
        """Execute one SPI transaction (opcode + address + data)."""
        if not tx:
            return b"\xff" * rx_len

        with self.lock:
            op = tx[0]
            if op == 0x9F:  # RDID (JEDEC)
                resp = MX25L12805D_JEDEC
                return (resp + b"\xff" * rx_len)[:rx_len]

            if op == 0x05:  # RDSR
                sr = self.status_reg | (0x02 if self.write_enabled else 0x00)
                return bytes([sr]) * rx_len

            if op == 0x06:  # WREN
                self.write_enabled = True
                return b""

            if op == 0x04:  # WRDI
                self.write_enabled = False
                return b""

            if op == 0x01 and len(tx) >= 2:  # WRSR
                if self.write_enabled:
                    self.status_reg = tx[1] & 0xFC
                    self.write_enabled = False
                return b""

            if op == 0x03 and len(tx) >= 4:  # READ
                addr = ((tx[1] << 16) | (tx[2] << 8) | tx[3]) % MX25L12805D_SIZE
                self.stats.reads += 1
                out = bytearray(rx_len)
                for i in range(rx_len):
                    out[i] = self.data[(addr + i) % MX25L12805D_SIZE]
                return bytes(out)

            if op == 0x0B and len(tx) >= 5:  # FAST_READ (1 dummy byte)
                addr = ((tx[1] << 16) | (tx[2] << 8) | tx[3]) % MX25L12805D_SIZE
                self.stats.reads += 1
                out = bytearray(rx_len)
                for i in range(rx_len):
                    out[i] = self.data[(addr + i) % MX25L12805D_SIZE]
                return bytes(out)

            if op == 0x02 and len(tx) >= 4:  # PP (Page Program, 1 -> 0 only)
                if not self.write_enabled:
                    return b""
                addr = ((tx[1] << 16) | (tx[2] << 8) | tx[3]) % MX25L12805D_SIZE
                payload = tx[4:]
                self._check_ec_guard(addr, len(payload))
                page_base = addr & ~0xFF
                for idx, byte in enumerate(payload):
                    target = page_base + ((addr + idx) & 0xFF)
                    self.data[target] &= byte
                self.stats.writes += 1
                self.write_enabled = False
                return b""

            if op == 0x20 and len(tx) >= 4:  # SE 4 KiB
                if self.write_enabled:
                    addr = (((tx[1] << 16) | (tx[2] << 8) | tx[3]) & ~0xFFF) % MX25L12805D_SIZE
                    self._erase_range(addr, 4096)
                return b""

            if op == 0x52 and len(tx) >= 4:  # BE 32 KiB
                if self.write_enabled:
                    addr = (((tx[1] << 16) | (tx[2] << 8) | tx[3]) & ~0x7FFF) % MX25L12805D_SIZE
                    self._erase_range(addr, 32768)
                return b""

            if op == 0xD8 and len(tx) >= 4:  # BE 64 KiB
                if self.write_enabled:
                    addr = (((tx[1] << 16) | (tx[2] << 8) | tx[3]) & ~0xFFFF) % MX25L12805D_SIZE
                    self._erase_range(addr, 65536)
                return b""

            if op in (0x60, 0xC7):  # Chip Erase
                if self.write_enabled:
                    self._erase_range(0, MX25L12805D_SIZE)
                return b""

            return b"\xff" * rx_len


class _SerprogHandler(socketserver.BaseRequestHandler):
    def _recv_exact(self, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = self.request.recv(n - len(buf))
            if not chunk:
                raise EOFError
            buf.extend(chunk)
        return bytes(buf)

    def handle(self) -> None:
        flash: VirtualMX25L12805D = self.server.flash  # type: ignore[attr-defined]
        cmd_bitmap = 0
        for c in (
            S_CMD_NOP,
            S_CMD_Q_IFACE,
            S_CMD_Q_CMDMAP,
            S_CMD_Q_PGMNAME,
            S_CMD_Q_SERBUF,
            S_CMD_Q_BUSTYPE,
            S_CMD_SYNCNOP,
            S_CMD_S_BUSTYPE,
            S_CMD_O_SPIOP,
            S_CMD_S_SPI_FREQ,
            S_CMD_S_PIN_STATE,
        ):
            cmd_bitmap |= 1 << c
        cmd_map_bytes = cmd_bitmap.to_bytes(32, "little")

        try:
            while True:
                raw_cmd = self.request.recv(1)
                if not raw_cmd:
                    break
                cmd = raw_cmd[0]

                if cmd == S_CMD_NOP:
                    self.request.sendall(bytes([S_ACK]))
                elif cmd == S_CMD_Q_IFACE:
                    self.request.sendall(bytes([S_ACK]) + struct.pack("<H", 1))
                elif cmd == S_CMD_Q_CMDMAP:
                    self.request.sendall(bytes([S_ACK]) + cmd_map_bytes)
                elif cmd == S_CMD_Q_PGMNAME:
                    name = b"cb4a-spiemu-3.3v".ljust(16, b"\x00")[:16]
                    self.request.sendall(bytes([S_ACK]) + name)
                elif cmd == S_CMD_Q_SERBUF:
                    self.request.sendall(bytes([S_ACK]) + struct.pack("<H", 0xFFFF))
                elif cmd == S_CMD_Q_BUSTYPE:
                    self.request.sendall(bytes([S_ACK, BUS_SPI]))
                elif cmd == S_CMD_SYNCNOP:
                    self.request.sendall(bytes([S_NAK, S_ACK]))
                elif cmd == S_CMD_S_BUSTYPE:
                    bus = self._recv_exact(1)[0]
                    self.request.sendall(bytes([S_ACK if (bus & BUS_SPI) else S_NAK]))
                elif cmd == S_CMD_S_SPI_FREQ:
                    freq = struct.unpack("<I", self._recv_exact(4))[0]
                    self.request.sendall(bytes([S_ACK]) + struct.pack("<I", freq or 16_000_000))
                elif cmd == S_CMD_S_PIN_STATE:
                    _ = self._recv_exact(1)
                    self.request.sendall(bytes([S_ACK]))
                elif cmd == S_CMD_O_SPIOP:
                    hdr = self._recv_exact(6)
                    slen = int.from_bytes(hdr[0:3], "little")
                    rlen = int.from_bytes(hdr[3:6], "little")
                    tx = self._recv_exact(slen)
                    try:
                        rx = flash.spi_transact(tx, rlen)
                    except ProtectedRegionError:
                        self.request.sendall(bytes([S_NAK]))
                        continue
                    self.request.sendall(bytes([S_ACK]) + rx)
                else:
                    self.request.sendall(bytes([S_NAK]))
        except EOFError:
            pass
        finally:
            flash.flush()


class VirtualProgrammerServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, host: str, port: int, flash: VirtualMX25L12805D) -> None:
        self.flash = flash
        super().__init__((host, port), _SerprogHandler)
