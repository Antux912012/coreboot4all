# Device Tier Model

Coreboot4All sorts every device into one of four tiers before a build runs:

- **Tier A (Supported):** The mainboard is in the coreboot tree, no active boot blocker exists, and a recovery path exists.
- **Tier B (Near-supported):** The chipset is in the tree and a similar mainboard exists, with no boot blocker.
- **Tier C (Research):** Public silicon documentation exists, with no boot blocker.
- **Tier D (Blocked):** An active boot blocker (Boot Guard verified mode, AMD PSB fuse, signed ARM boot ROM), no recovery path, or no public data.
