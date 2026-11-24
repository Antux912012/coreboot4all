/* SPDX-License-Identifier: GPL-2.0-only */

#include <soc/romstage.h>
#include <spd_bin.h>
#include <string.h>

void mainboard_memory_init_params(FSPM_UPD *mupd)
{
	FSP_M_CONFIG *mem_cfg = &mupd->FspmConfig;
	static const u16 rcomp_resistor[] = { 121, 81, 100 };
	static const u16 rcomp_target[] = { 100, 40, 40, 23, 40 };

	/* Verify Rcomp/DqPinsInterleaved/CaVrefConfig against Phase 0 inteltool -a dump. */
	memcpy(&mem_cfg->RcompResistor, rcomp_resistor, sizeof(rcomp_resistor));
	memcpy(&mem_cfg->RcompTarget, rcomp_target, sizeof(rcomp_target));
	mem_cfg->DqPinsInterleaved = true;
	mem_cfg->CaVrefConfig = 2;
	mem_cfg->MemorySpdDataLen = CONFIG_DIMM_SPD_SIZE;

	/* 2x DDR4 SODIMM slots (ChannelA-DIMM0 at 0x50, ChannelB-DIMM0 at 0x52) */
	struct spd_block blk = { .addr_map = { 0x50, 0x52 } };
	get_spd_smbus(&blk);
	dump_spd_info(&blk);

	mem_cfg->MemorySpdPtr00 = (uintptr_t)blk.spd_array[0];
	mem_cfg->MemorySpdPtr10 = (uintptr_t)blk.spd_array[1];
}
