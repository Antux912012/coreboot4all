#!/usr/bin/env bash
# Read-only hardware inspection script for Coreboot4All.
# Collects Boot Guard, CSME, GPIO, PCI, ACPI, and SPI flash info on the host OS.
set -uo pipefail

DEVICE_ID="${1:-lenovo_thinkpad_13_gen2}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="${REPO_ROOT}/out/devices/${DEVICE_ID}/raw"
TOOL_DIR="${REPO_ROOT}/out/devices/${DEVICE_ID}/bin"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  echo "Usage: sudo bash scripts/inspect-host.sh [device_id]"
  echo "Default device_id: lenovo_thinkpad_13_gen2"
  exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run with sudo: sudo bash $0 ${DEVICE_ID}"
  exit 1
fi

mkdir -p "${RAW_DIR}" "${TOOL_DIR}"
echo "=== Coreboot4All Host Inspection (${DEVICE_ID}) ==="
echo "Output directory: ${RAW_DIR}"

# 1. Extract intelmetool and inteltool from cb4a/tools:1.0 if not already extracted.
TARGET_USER="${SUDO_USER:-$(logname 2>/dev/null || echo root)}"
if [ ! -x "${TOOL_DIR}/intelmetool" ] || [ ! -x "${TOOL_DIR}/inteltool" ]; then
  echo "[1/7] Extracting intelmetool and inteltool from cb4a/tools:1.0..."
  if command -v docker >/dev/null 2>&1; then
    su -s /bin/bash "${TARGET_USER}" -c "docker run --rm --userns=keep-id --network none -v ${TOOL_DIR}:/out cb4a/tools:1.0 cp /usr/local/bin/intelmetool /usr/local/bin/inteltool /out/" || true
  fi
fi

# 2. Check kernel cmdline for iomem=relaxed.
echo "[2/7] Checking kernel parameters..."
cat /proc/cmdline > "${RAW_DIR}/cmdline.txt"
if grep -qw "iomem=relaxed" /proc/cmdline; then
  IOMEM_RELAXED="yes"
else
  IOMEM_RELAXED="no"
  echo "NOTE: 'iomem=relaxed' is NOT in /proc/cmdline. inteltool and intelmetool -m may be restricted by the kernel, but MSR 0x13A (Boot Guard) can still be read."
fi

# 3. Load msr kernel module and read Boot Guard MSR 0x13A + intelmetool -b.
echo "[3/7] Checking Intel Boot Guard (MSR 0x13A & intelmetool -b)..."
modprobe msr 2>/dev/null || true

if [ -r /dev/cpu/0/msr ]; then
  python3 -c '
import os, struct
fd = os.open("/dev/cpu/0/msr", os.O_RDONLY)
os.lseek(fd, 0x13A, os.SEEK_SET)
val = struct.unpack("<Q", os.read(fd, 8))[0]
os.close(fd)
print(f"MSR_BOOT_GUARD_SACM_INFO (0x13A) = 0x{val:016x}")
print(f"  NEM_ENABLED        (bit 0): {(val >> 0) & 1}")
print(f"  TPM_SUCCESS        (bit 1): {(val >> 1) & 1}")
print(f"  TPM_DEACTIVATED    (bit 2): {(val >> 2) & 1}")
print(f"  FORCE_ANCHOR_BOOT  (bit 3): {(val >> 3) & 1}")
print(f"  MEASURED_BOOT      (bit 5): {(val >> 5) & 1}")
print(f"  VERIFIED_BOOT      (bit 6): {(val >> 6) & 1}")
print(f"  REVOKED            (bit 7): {(val >> 7) & 1}")
print(f"  BTG_CAPABILITY     (bit 32): {(val >> 32) & 1}")
' > "${RAW_DIR}/msr_13a.txt" 2>&1 || echo "Failed to read MSR 0x13A" > "${RAW_DIR}/msr_13a.txt"
else
  echo "/dev/cpu/0/msr not readable" > "${RAW_DIR}/msr_13a.txt"
fi

if [ -x "${TOOL_DIR}/intelmetool" ]; then
  "${TOOL_DIR}/intelmetool" -b > "${RAW_DIR}/intelmetool_b.txt" 2>&1 || true
  "${TOOL_DIR}/intelmetool" -m > "${RAW_DIR}/intelmetool_m.txt" 2>&1 || true
else
  echo "intelmetool binary not found in ${TOOL_DIR}" > "${RAW_DIR}/intelmetool_b.txt"
fi

# 4. Run inteltool -a (requires iomem=relaxed for full MMIO/GPIO dump).
echo "[4/7] Running inteltool -a..."
if [ -x "${TOOL_DIR}/inteltool" ]; then
  "${TOOL_DIR}/inteltool" -a > "${RAW_DIR}/inteltool.txt" 2>&1 || true
else
  echo "inteltool binary not found in ${TOOL_DIR}" > "${RAW_DIR}/inteltool.txt"
fi

# 5. Collect DMI, PCI, and MEI sysfs info.
echo "[5/7] Collecting DMI and PCI configuration..."
if command -v dmidecode >/dev/null 2>&1; then
  dmidecode > "${RAW_DIR}/dmidecode.txt" 2>&1 || true
fi
lspci -nn > "${RAW_DIR}/lspci.txt" 2>&1 || true
lspci -nnvv -s 00:16.0 > "${RAW_DIR}/lspci_mei.txt" 2>&1 || true
cat /sys/class/mei/mei0/fw_status > "${RAW_DIR}/mei_fw_status.txt" 2>&1 || true

# 6. Collect ACPI tables (read-only).
echo "[6/7] Collecting ACPI tables..."
if command -v acpidump >/dev/null 2>&1; then
  acpidump -o "${RAW_DIR}/acpidump.dat" > "${RAW_DIR}/acpidump.log" 2>&1 || true
else
  mkdir -p "${RAW_DIR}/acpi_tables"
  cp /sys/firmware/acpi/tables/DSDT "${RAW_DIR}/acpi_tables/" 2>/dev/null || true
  cp /sys/firmware/acpi/tables/FACP "${RAW_DIR}/acpi_tables/" 2>/dev/null || true
  cp /sys/firmware/acpi/tables/SSDT* "${RAW_DIR}/acpi_tables/" 2>/dev/null || true
fi

# 7. Read-only SPI flash probe (if flashrom is installed on host).
echo "[7/7] Probing SPI flash (read-only)..."
if command -v flashrom >/dev/null 2>&1; then
  flashrom -p internal --flash-name > "${RAW_DIR}/flashrom_probe.txt" 2>&1 || true
  flashrom -p internal --ifd -i bios -r "${RAW_DIR}/bios_region.bin" >> "${RAW_DIR}/flashrom_probe.txt" 2>&1 || true
else
  echo "flashrom is not installed on host (install with: sudo apt install flashrom)" > "${RAW_DIR}/flashrom_probe.txt"
fi

# Fix ownership back to invoking user so non-root tools can read everything.
if [ "${TARGET_USER}" != "root" ]; then
  chown -R "${TARGET_USER}:${TARGET_USER}" "${RAW_DIR}" 2>/dev/null || true
fi

# Build concise summary to paste back.
{
  echo "=== SUMMARY ==="
  echo "iomem_relaxed=${IOMEM_RELAXED}"
  cat "${RAW_DIR}/msr_13a.txt"
  echo "--- intelmetool -b ---"
  cat "${RAW_DIR}/intelmetool_b.txt"
  echo "--- flashrom_probe ---"
  tail -n 20 "${RAW_DIR}/flashrom_probe.txt"
  echo "--- files ---"
  ls -lh "${RAW_DIR}"
} | tee "${RAW_DIR}/summary.txt"

echo ""
echo "Done! Paste the output above (or ${RAW_DIR}/summary.txt) back to the assistant."
