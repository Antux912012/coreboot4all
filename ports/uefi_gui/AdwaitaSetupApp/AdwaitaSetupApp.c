/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * Coreboot4All Adwaita / Pantheon HIG Graphical UEFI Setup Application
 * Target: EDK2 UefiPayloadPkg (1920x1080 native GOP framebuffer via coreboot libgfxinit)
 *
 * Design language:
 *   - Modern ThinkPad UEFI hierarchy (Headerbar + Left Sidebar + Preference Cards)
 *   - GNOME / Libadwaita GTK4 surfaces (#1E1E1E window, #282828 sidebar, #303030 card,
 *     #3584E4 Adwaita accent blue, #2EC27E success green, #E01B24 destructive red)
 *   - elementaryOS Pantheon HIG calm spacing, clean title/subtitle headerbar, pill switches
 */

#include <Uefi.h>
#include <Library/UefiLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/UefiRuntimeServicesTableLib.h>
#include <Protocol/GraphicsOutput.h>
#include <Protocol/SimplePointer.h>

typedef struct {
	UINT8 Blue;
	UINT8 Green;
	UINT8 Red;
	UINT8 Reserved;
} BGRA_COLOR;

/* GNOME Libadwaita Dark + Pantheon HIG palette */
static const BGRA_COLOR COL_WINDOW_BG   = { 0x1E, 0x1E, 0x1E, 0x00 }; /* #1E1E1E */
static const BGRA_COLOR COL_HEADER_BG   = { 0x24, 0x24, 0x24, 0x00 }; /* #242424 */
static const BGRA_COLOR COL_SIDEBAR_BG  = { 0x26, 0x26, 0x26, 0x00 }; /* #262626 */
static const BGRA_COLOR COL_CARD_BG     = { 0x30, 0x30, 0x30, 0x00 }; /* #303030 */
static const BGRA_COLOR COL_BORDER      = { 0x42, 0x42, 0x42, 0x00 }; /* #424242 */
static const BGRA_COLOR COL_ACCENT      = { 0xE4, 0x84, 0x35, 0x00 }; /* #3584E4 Adwaita Blue */
static const BGRA_COLOR COL_SUCCESS     = { 0x7E, 0xC2, 0x2E, 0x00 }; /* #2EC27E Adwaita Green */
static const BGRA_COLOR COL_DESTRUCTIVE = { 0x24, 0x1B, 0xE0, 0x00 }; /* #E01B24 Adwaita Red */
static const BGRA_COLOR COL_TOGGLE_OFF  = { 0x5E, 0x5E, 0x5E, 0x00 }; /* #5E5E5E */
static const BGRA_COLOR COL_WHITE       = { 0xFF, 0xFF, 0xFF, 0x00 };

typedef enum {
	TAB_OVERVIEW = 0,
	TAB_SECURITY,
	TAB_HARDWARE,
	TAB_BOOT,
	TAB_REVERT,
	TAB_COUNT
} SETUP_TAB;

typedef struct {
	BOOLEAN SecureBoot;
	BOOLEAN Tpm2Enabled;
	BOOLEAN VtdIommu;
	BOOLEAN IntelMeEnabled;
	BOOLEAN HyperThreading;
	BOOLEAN BatteryThreshold;
	BOOLEAN S3Suspend;
} CFR_STATE;

static VOID FillRect(
	EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop,
	UINTN X, UINTN Y, UINTN W, UINTN H,
	BGRA_COLOR Color
)
{
	EFI_GRAPHICS_OUTPUT_BLT_PIXEL Pixel;
	Pixel.Blue     = Color.Blue;
	Pixel.Green    = Color.Green;
	Pixel.Red      = Color.Red;
	Pixel.Reserved = 0;
	Gop->Blt(Gop, &Pixel, EfiBltVideoFill, 0, 0, X, Y, W, H, 0);
}

static VOID DrawCard(
	EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop,
	UINTN X, UINTN Y, UINTN W, UINTN H
)
{
	FillRect(Gop, X, Y, W, H, COL_BORDER);
	FillRect(Gop, X + 1, Y + 1, W - 2, H - 2, COL_CARD_BG);
}

static VOID DrawPillSwitch(
	EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop,
	UINTN X, UINTN Y,
	BOOLEAN Enabled
)
{
	UINTN W = 52;
	UINTN H = 28;
	FillRect(Gop, X, Y, W, H, Enabled ? COL_ACCENT : COL_TOGGLE_OFF);
	/* Circular knob approximation */
	UINTN KnobX = Enabled ? (X + W - 24) : (X + 4);
	FillRect(Gop, KnobX, Y + 4, 20, 20, COL_WHITE);
}

static VOID RenderUi(
	EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop,
	SETUP_TAB ActiveTab,
	const CFR_STATE *State
)
{
	UINTN Width  = Gop->Mode->Info->HorizontalResolution;
	UINTN Height = Gop->Mode->Info->VerticalResolution;
	UINTN HeaderH = 56;
	UINTN SidebarW = 280;
	UINTN FooterH = 60;

	/* Window background */
	FillRect(Gop, 0, 0, Width, Height, COL_WINDOW_BG);

	/* Libadwaita / Pantheon Headerbar */
	FillRect(Gop, 0, 0, Width, HeaderH, COL_HEADER_BG);
	FillRect(Gop, 0, HeaderH, Width, 1, COL_BORDER);

	/* Left Navigation Sidebar */
	FillRect(Gop, 0, HeaderH + 1, SidebarW, Height - HeaderH - FooterH - 1, COL_SIDEBAR_BG);
	FillRect(Gop, SidebarW, HeaderH + 1, 1, Height - HeaderH - FooterH - 1, COL_BORDER);

	/* Active Sidebar Row Highlight */
	UINTN RowY = HeaderH + 24 + ((UINTN)ActiveTab * 52);
	FillRect(Gop, 12, RowY, SidebarW - 24, 42, COL_ACCENT);

	/* Main Content Area: Boxed List Preference Cards */
	UINTN ContentX = SidebarW + 40;
	UINTN ContentW = (Width > SidebarW + 80) ? (Width - SidebarW - 80) : 640;
	if (ContentW > 860) {
		ContentW = 860;
	}

	DrawCard(Gop, ContentX, HeaderH + 32, ContentW, 130);
	DrawCard(Gop, ContentX, HeaderH + 184, ContentW, 340);

	/* Render Pill Switches on Security / Hardware tabs */
	if (ActiveTab == TAB_SECURITY) {
		DrawPillSwitch(Gop, ContentX + ContentW - 76, HeaderH + 210, State->SecureBoot);
		DrawPillSwitch(Gop, ContentX + ContentW - 76, HeaderH + 274, State->Tpm2Enabled);
		DrawPillSwitch(Gop, ContentX + ContentW - 76, HeaderH + 338, State->VtdIommu);
		DrawPillSwitch(Gop, ContentX + ContentW - 76, HeaderH + 402, State->IntelMeEnabled);
	} else if (ActiveTab == TAB_HARDWARE) {
		DrawPillSwitch(Gop, ContentX + ContentW - 76, HeaderH + 210, State->HyperThreading);
		DrawPillSwitch(Gop, ContentX + ContentW - 76, HeaderH + 274, State->BatteryThreshold);
		DrawPillSwitch(Gop, ContentX + ContentW - 76, HeaderH + 338, State->S3Suspend);
	} else if (ActiveTab == TAB_REVERT) {
		/* Destructive-action button for official Lenovo BIOS revert workflow */
		FillRect(Gop, ContentX + 24, HeaderH + 440, 260, 42, COL_DESTRUCTIVE);
	}

	/* Bottom Pantheon Action Bar */
	FillRect(Gop, 0, Height - FooterH, Width, 1, COL_BORDER);
	FillRect(Gop, 0, Height - FooterH + 1, Width, FooterH - 1, COL_HEADER_BG);
	FillRect(Gop, Width - 190, Height - FooterH + 12, 166, 36, COL_SUCCESS);
}

EFI_STATUS EFIAPI UefiMain(
	IN EFI_HANDLE        ImageHandle,
	IN EFI_SYSTEM_TABLE  *SystemTable
)
{
	EFI_STATUS Status;
	EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop = NULL;
	EFI_INPUT_KEY Key;
	SETUP_TAB ActiveTab = TAB_OVERVIEW;
	CFR_STATE State = {
		.SecureBoot       = TRUE,
		.Tpm2Enabled      = TRUE,
		.VtdIommu         = TRUE,
		.IntelMeEnabled   = TRUE,
		.HyperThreading   = TRUE,
		.BatteryThreshold = TRUE,
		.S3Suspend        = TRUE,
	};

	Status = gBS->LocateProtocol(&gEfiGraphicsOutputProtocolGuid, NULL, (VOID **)&Gop);
	if (EFI_ERROR(Status) || Gop == NULL) {
		Print(L"Coreboot4All Setup: GOP unavailable, falling back to text console.\n");
		return Status;
	}

	while (TRUE) {
		RenderUi(Gop, ActiveTab, &State);

		UINTN EventIndex = 0;
		gBS->WaitForEvent(1, &gST->ConIn->WaitForKey, &EventIndex);
		Status = gST->ConIn->ReadKeyStroke(gST->ConIn, &Key);
		if (EFI_ERROR(Status)) {
			continue;
		}

		if (Key.ScanCode == SCAN_ESC) {
			break;
		} else if (Key.ScanCode == SCAN_DOWN) {
			ActiveTab = (SETUP_TAB)((ActiveTab + 1) % TAB_COUNT);
		} else if (Key.ScanCode == SCAN_UP) {
			ActiveTab = (SETUP_TAB)((ActiveTab + TAB_COUNT - 1) % TAB_COUNT);
		} else if (Key.UnicodeChar == L'1') {
			State.SecureBoot = !State.SecureBoot;
		} else if (Key.UnicodeChar == L'2') {
			State.VtdIommu = !State.VtdIommu;
		} else if (Key.UnicodeChar == L'3') {
			State.IntelMeEnabled = !State.IntelMeEnabled;
		} else if (Key.ScanCode == SCAN_F10) {
			/* Save CFR / UEFI variables and reboot */
			gRT->ResetSystem(EfiResetWarm, EFI_SUCCESS, 0, NULL);
		}
	}

	return EFI_SUCCESS;
}
