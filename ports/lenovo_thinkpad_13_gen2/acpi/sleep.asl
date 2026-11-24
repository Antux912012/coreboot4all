/* SPDX-License-Identifier: GPL-2.0-only */

Method (MPTS, 1, Serialized)
{
	/* Prepare to Sleep hook (Arg0 = target S-state) */
}

Method (MWAK, 1, Serialized)
{
	/* Wake hook: notify AC, battery, and lid after S3 resume */
	Notify (\_SB.ACAD, 0x80)
	Notify (\_SB.BAT1, 0x80)
	Notify (\_SB.LID, 0x80)
}
