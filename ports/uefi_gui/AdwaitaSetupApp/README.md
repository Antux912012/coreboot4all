# AdwaitaSetupApp — Modern ThinkPad UEFI Setup UI (GNOME/Libadwaita & Pantheon HIG)

This EDK2 UEFI application renders a native 1920x1080 GOP graphical setup interface inspired by
modern Lenovo ThinkPad BIOS screens combined with GNOME Libadwaita (GTK4) and elementaryOS
Pantheon Human Interface Guidelines.

## Integration into EDK2 (`UefiPayloadPkg`)

1. Copy `AdwaitaSetupApp/` into `payloads/external/edk2/workspace/tianocore/UefiPayloadPkg/Application/AdwaitaSetupApp/`.
2. Add `UefiPayloadPkg/Application/AdwaitaSetupApp/AdwaitaSetupApp.inf` under `[Components]` in `UefiPayloadPkg.dsc`.
3. Add `INF UefiPayloadPkg/Application/AdwaitaSetupApp/AdwaitaSetupApp.inf` to `UefiPayloadPkg.fdf` so it registers as the graphical Setup / Boot Manager entry.
4. Preview the design locally in any browser using `out/kits/lenovo_thinkpad_13_gen2/uefi_gui_preview.html`.
