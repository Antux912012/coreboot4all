#!/usr/bin/env bash
# Boot-test an emulation/qemu-* coreboot ROM in QEMU and check serial output.
set -euo pipefail

ID="${1:-emulation_qemu_q35}"
ROM="out/builds/${ID}/coreboot.rom"
LOG="out/builds/${ID}/qemu.log"

if [ ! -f "${ROM}" ]; then
  echo "E-21: ROM not found at ${ROM}" >&2
  exit 21
fi

if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
  echo "E-25: qemu-system-x86_64 is not installed on host." >&2
  exit 25
fi

MACHINE="q35"
if [[ "${ID}" == *"i440fx"* ]]; then
  MACHINE="pc"
fi

timeout 12s qemu-system-x86_64 \
  -M "${MACHINE}" \
  -bios "${ROM}" \
  -serial stdio \
  -display none \
  -no-reboot > "${LOG}" 2>&1 || true

if grep -qE "coreboot-|SeaBIOS" "${LOG}"; then
  echo "QEMU boot check passed for ${ID} (${LOG})"
  exit 0
fi

echo "E-22: QEMU boot check did not observe coreboot/SeaBIOS banner in ${LOG}" >&2
exit 22
