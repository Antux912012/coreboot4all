/* SPDX-License-Identifier: GPL-2.0-only */

Scope (\_SB)
{
	Device (ACAD)
	{
		Name (_HID, "ACPI0003")
		Name (_PCL, Package () { \_SB })

		Method (_PSR, 0, NotSerialized)
		{
			Return (\_SB.PCI0.LPCB.EC.XYAC)
		}
	}

	Device (LID)
	{
		Name (_HID, EisaId ("PNP0C0D"))
		Name (_PRW, Package () { 0x18, 0x04 })

		Method (_LID, 0, NotSerialized)
		{
			Return (\_SB.PCI0.LPCB.EC.XPLD)
		}
	}

	Device (BAT1)
	{
		Name (_HID, EisaId ("PNP0C0A"))
		Name (_UID, 1)
		Name (_PCL, Package () { \_SB })

		Method (_STA, 0, NotSerialized)
		{
			If (\_SB.PCI0.LPCB.EC.XBTS)
			{
				Return (0x1F)
			}
			Return (0x0F)
		}

		Method (_BIF, 0, NotSerialized)
		{
			Return (Package () {
				0x00000000, /* Power Unit: mWh */
				0x0000A410, /* Design Capacity (42000 mWh placeholder) */
				0x0000A410, /* Last Full Charge Capacity */
				0x00000001, /* Rechargeable */
				0x00002B5C, /* Design Voltage (11100 mV) */
				0x00000834, /* Warning Capacity */
				0x00000190, /* Low Capacity */
				0x00000001, /* Granularity 1 */
				0x00000001, /* Granularity 2 */
				"01AV400",
				"0001",
				"LION",
				"LGC"
			})
		}

		Method (_BST, 0, NotSerialized)
		{
			Local0 = Zero
			If (\_SB.PCI0.LPCB.EC.XYAC)
			{
				If ((\_SB.PCI0.LPCB.EC.XCAC > Zero))
				{
					Local0 = 0x02 /* Charging */
				}
			}
			Else
			{
				Local0 = 0x01 /* Discharging */
			}
			Return (Package () {
				Local0,
				\_SB.PCI0.LPCB.EC.XCAC,
				\_SB.PCI0.LPCB.EC.XCRC,
				\_SB.PCI0.LPCB.EC.XCVO
			})
		}
	}

	Device (UBTC)
	{
		Name (_HID, EisaId ("USBC000"))
		Name (_CID, EisaId ("PNP0CA0"))
		Name (_UID, Zero)
		Name (_ADR, Zero)

		Method (_STA, 0, NotSerialized)
		{
			Return (0x0F)
		}

		Method (_CRS, 0, NotSerialized)
		{
			Name (RBUF, ResourceTemplate ()
			{
				Memory32Fixed (ReadWrite, 0xFE700B80, 0x00000030)
			})
			Return (RBUF)
		}
	}
}

Scope (\_TZ)
{
	ThermalZone (THM0)
	{
		Method (_TMP, 0, NotSerialized)
		{
			Local0 = \_SB.PCI0.LPCB.EC.XTM0
			Return (((Local0 * 10) + 2732))
		}
		Method (_CRT, 0, NotSerialized)
		{
			Return (3732) /* 100 C */
		}
	}
}
