/* SPDX-License-Identifier: GPL-2.0-only */

/* Internal PS/2 Keyboard (MSFT0001 / PNP0303) & Elantech TrackPoint/Touchpad (LEN2032 / PNP0F03) */
Device (PS2K)
{
	Name (_HID, "MSFT0001")
	Name (_CID, EisaId ("PNP0303"))

	Method (_STA, 0, NotSerialized)
	{
		Return (0x0F)
	}

	Name (_CRS, ResourceTemplate ()
	{
		IO (Decode16, 0x0060, 0x0060, 0x01, 0x01)
		IO (Decode16, 0x0064, 0x0064, 0x01, 0x01)
		IRQ (Edge, ActiveHigh, Exclusive, ) { 1 }
	})
}

Device (PS2M)
{
	Name (_HID, "LEN2032")
	Name (_CID, EisaId ("PNP0F03"))

	Method (_STA, 0, NotSerialized)
	{
		Return (0x0F)
	}

	Name (_CRS, ResourceTemplate ()
	{
		IRQ (Edge, ActiveHigh, Exclusive, ) { 12 }
	})
}
