/* SPDX-License-Identifier: GPL-2.0-only */

#include <bootblock_common.h>
#include <device/pci_ops.h>
#include <intelblocks/lpc_lib.h>
#include <soc/pci_devs.h>

void bootblock_mainboard_early_init(void)
{
	/*
	 * ThinkPad 13 2nd Gen uses an ITE EC (ITE EC-V14.4, r0jht26w) with
	 * standard ACPI I/O 0x62/0x66 plus LPC Generic Memory Range (LGMR)
	 * at 0xFE700000 for XECR (0xFE700100) and UCSI XTCR (0xFE700B00).
	 */
	pci_write_config32(PCH_DEV_LPC, 0x98, 0xfe700001);
}
