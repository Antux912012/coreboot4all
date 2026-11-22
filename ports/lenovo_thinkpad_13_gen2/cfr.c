/* SPDX-License-Identifier: GPL-2.0-only */

#include <boot/coreboot_tables.h>
#include <drivers/option/cfr_frontend.h>
#include <intelblocks/cfr.h>
#include <soc/cfr.h>

/* Keep Intel ME and VT-d/IOMMU exposed and configurable in CFR setup. */
static struct sm_obj_form system_form = {
	.ui_name = "System & Security",
	.obj_list = (const struct sm_object *[]) {
		&hyper_threading,
		&vtd,
		&me_state,
		&me_state_counter,
		&igd_dvmt,
		&igd_aperture,
		&pciexp_aspm,
		&pciexp_clk_pm,
		&pciexp_l1ss,
		&pciexp_speed,
		&s0ix_enable,
		&legacy_8254_timer,
		NULL
	},
};

static struct sm_obj_form *sm_root[] = {
	&system_form,
	NULL
};

void mb_cfr_setup_menu(struct lb_cfr *cfr_root)
{
	cfr_write_setup_menu(cfr_root, sm_root);
}
