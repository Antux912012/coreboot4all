/* SPDX-License-Identifier: GPL-2.0-only */

/* ThinkPad 13 2nd Gen ACPI EC (0x62/0x66, GPE 0x17 verified from host dmesg & DSDT) */
Device (EC)
{
	Name (_HID, EisaId ("PNP0C09"))
	Name (_UID, 1)
	Name (_GPE, 0x17)

	Method (_STA, 0, NotSerialized)
	{
		Return (0x0F)
	}

	Name (_CRS, ResourceTemplate ()
	{
		IO (Decode16, 0x0062, 0x0062, 0x00, 0x01)
		IO (Decode16, 0x0066, 0x0066, 0x00, 0x01)
	})

	Device (HKEY)
	{
		Name (_HID, EisaId ("LEN0268"))
		Method (_STA, 0, NotSerialized)
		{
			Return (0x0F)
		}
	}
}
