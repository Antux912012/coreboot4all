/* SPDX-License-Identifier: GPL-2.0-only */

/* ThinkPad 13 2nd Gen ITE EC (ITE EC-V14.4: 0x62/0x66, XECR 0xFE700100, XTCR 0xFE700B00, GPE 0x17) */
Device (EC)
{
	Name (_HID, EisaId ("PNP0C09"))
	Name (_UID, 1)
	Name (_GPE, 0x17)
	Mutex (MUT0, 0)

	Method (_STA, 0, NotSerialized)
	{
		Return (0x0F)
	}

	Name (_CRS, ResourceTemplate ()
	{
		IO (Decode16, 0x0062, 0x0062, 0x00, 0x01)
		IO (Decode16, 0x0066, 0x0066, 0x00, 0x01)
	})

	OperationRegion (ERAM, EmbeddedControl, Zero, 0xFF)
	Field (ERAM, ByteAcc, NoLock, Preserve)
	{
		Offset (0x01),
		ENBK, 1,
		ENFP, 1,
		    , 4,
		ENBT, 1,
		Offset (0x0C),
		HLCL, 4,
		Offset (0x3A),
		    , 5,
		CWLN, 1,
		CWWAN, 1,
	}

	OperationRegion (XECR, SystemMemory, 0xFE700100, 0x0100)
	Field (XECR, ByteAcc, NoLock, Preserve)
	{
		Offset (0x38),
		XB0S, 7,
		XBTS, 1,
		Offset (0x46),
		    , 2,
		XPLD, 1,
		    , 3,
		XYAC, 1,
		    , 1,
		Offset (0x78),
		XTM0, 8,
		XTM1, 8,
		Offset (0xE0),
		XCRC, 16,
		XCAC, 16,
		XCVO, 16,
	}

	OperationRegion (XTCR, SystemMemory, 0xFE700B00, 0x0100)
	Field (XTCR, ByteAcc, NoLock, Preserve)
	{
		Offset (0x80),
		VER1, 8,
		VER2, 8,
		RSV1, 8,
		RSV2, 8,
		CCI0, 8,
		CCI1, 8,
		CCI2, 8,
		CCI3, 8,
		CTL0, 8,
		CTL1, 8,
		CTL2, 8,
		CTL3, 8,
		CTL4, 8,
		CTL5, 8,
		CTL6, 8,
		CTL7, 8,
		MGI0, 8,
		MGI1, 8,
		MGI2, 8,
		MGI3, 8,
		MGI4, 8,
		MGI5, 8,
		MGI6, 8,
		MGI7, 8,
		MGI8, 8,
		MGI9, 8,
		MGIA, 8,
		MGIB, 8,
		MGIC, 8,
		MGID, 8,
		MGIE, 8,
		MGIF, 8,
		MGO0, 8,
		MGO1, 8,
		MGO2, 8,
		MGO3, 8,
		MGO4, 8,
		MGO5, 8,
		MGO6, 8,
		MGO7, 8,
		MGO8, 8,
		MGO9, 8,
		MGOA, 8,
		MGOB, 8,
		MGOC, 8,
		MGOD, 8,
		MGOE, 8,
		MGOF, 8,
	}

	/* EC Query Handlers (AC, Battery, Lid, Hotkeys, UCSI) */
	Method (_Q26, 0, NotSerialized)
	{
		Notify (\_SB.ACAD, 0x80)
		Notify (\_SB.BAT1, 0x80)
	}

	Method (_Q27, 0, NotSerialized)
	{
		Notify (\_SB.ACAD, 0x80)
		Notify (\_SB.BAT1, 0x80)
	}

	Method (_Q2A, 0, NotSerialized)
	{
		Notify (\_SB.LID, 0x80)
	}

	Method (_Q2B, 0, NotSerialized)
	{
		Notify (\_SB.LID, 0x80)
	}

	Method (_Q4A, 0, NotSerialized)
	{
		Notify (\_SB.BAT1, 0x80)
	}

	Method (_Q4B, 0, NotSerialized)
	{
		Notify (\_SB.BAT1, 0x81)
	}

	Method (_Q79, 0, NotSerialized)
	{
		Notify (\_SB.UBTC, 0x80)
	}

	Device (HKEY)
	{
		Name (_HID, EisaId ("LEN0268"))
		Method (_STA, 0, NotSerialized)
		{
			Return (0x0F)
		}
		Method (MHKV, 0, NotSerialized)
		{
			Return (0x0100)
		}
	}
}
