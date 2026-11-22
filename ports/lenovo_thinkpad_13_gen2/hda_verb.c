/* SPDX-License-Identifier: GPL-2.0-only */

#include <device/azalia_device.h>

/* Extracted from live ThinkPad 13 2nd Gen (20J1003WGM) /proc/asound/card0/codec#0 & #2 */
const u32 cim_verb_data[] = {
	0x10ec0298, /* Vendor/Device ID: Realtek ALC298 */
	0x17aa5063, /* Subsystem ID: Lenovo ThinkPad 13 2nd Gen */
	12,
	AZALIA_SUBVENDOR(0, 0x17aa5063),
	AZALIA_PIN_CFG(0, 0x12, 0x90a60140), /* Internal Mic */
	AZALIA_PIN_CFG(0, 0x13, 0x40000000),
	AZALIA_PIN_CFG(0, 0x14, 0x90170110), /* Internal Speaker */
	AZALIA_PIN_CFG(0, 0x17, 0x411111f0),
	AZALIA_PIN_CFG(0, 0x18, 0x03a11030), /* Ext Left Mic Jack */
	AZALIA_PIN_CFG(0, 0x19, 0x411111f0),
	AZALIA_PIN_CFG(0, 0x1a, 0x411111f0),
	AZALIA_PIN_CFG(0, 0x1d, 0x40648605),
	AZALIA_PIN_CFG(0, 0x1e, 0x411111f0),
	AZALIA_PIN_CFG(0, 0x1f, 0x411111f0),
	AZALIA_PIN_CFG(0, 0x21, 0x03211020), /* Ext Left Headphone Jack */

	0x8086280b, /* Vendor/Device ID: Intel Kabylake HDMI */
	0x80860101, /* Subsystem ID */
	4,
	AZALIA_SUBVENDOR(2, 0x80860101),
	AZALIA_PIN_CFG(2, 0x05, 0x18560010),
	AZALIA_PIN_CFG(2, 0x06, 0x18560010),
	AZALIA_PIN_CFG(2, 0x07, 0x18560010),
};

const u32 pc_beep_verbs[] = {};

AZALIA_ARRAY_SIZES;
