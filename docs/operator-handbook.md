# Operator Handbook

1. Collect hardware data on the target Linux host (`dmidecode`, `lspci -nn`, `intelmetool -b`, `flashrom`, `acpidump`).
2. Validate the device record with `make validate`.
3. Build the ROM with `make build ID=<device_id>`.
4. Prove reproducibility with `make offline ID=<device_id>`.
5. Generate flash and recovery procedures with `make kit ID=<device_id>`.
