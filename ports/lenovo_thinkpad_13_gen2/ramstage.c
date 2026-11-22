/* SPDX-License-Identifier: GPL-2.0-only */

#include <soc/gpio.h>
#include <soc/ramstage.h>

void thinkpad13g2_config_gpios(void);

void mainboard_silicon_init_params(FSP_SIL_UPD *params)
{
	thinkpad13g2_config_gpios();
}
