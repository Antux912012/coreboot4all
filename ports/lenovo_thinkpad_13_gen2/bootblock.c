/* SPDX-License-Identifier: GPL-2.0-only */

#include <bootblock_common.h>

void bootblock_mainboard_early_init(void)
{
	/* ThinkPad 13 2nd Gen uses standard ACPI EC at 0x62/0x66 (no PMH7/MEC1653). */
}
