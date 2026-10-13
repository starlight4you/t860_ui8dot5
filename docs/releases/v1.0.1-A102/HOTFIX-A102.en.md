# v1.0.1 A102 upgrade installer hotfix · 2026-10-13

For upgrades from v0.48.1, use **Upgrade-TWRP-v1.0.1-A102.7z.001–003**. This replaces the A100 upgrade package. Clean installations continue to use the existing A100 Odin package.

Fixes an incompatible bundled Mainline guard: the A100 installer called upgrade options that its helper did not implement, causing “Pending or unsafe system module state” after source verification passed. The replacement supports upgrade preflight and inode-preserving module backups. Unreadable module directories are detected earlier, and detailed module errors are displayed in Recovery.

SYSTEM/PRODUCT images, the kernel, and VENDOR adaptations are unchanged. Device, source, and pending-update checks remain enabled. DATA, apps, accounts, and lock credentials are preserved. Validation includes 67 module cases, 9 access cases, and all 114 payload chunks and 21 support files using the original Recovery tools.

1. Download all three A102 volumes and `SHA256SUMS-A102` into one folder; verify their hashes.
2. Open `.001` with 7-Zip and extract `TabS6-OneUI8.5-v1.0.1-A102-Upgrade-TWRP.zip`. Do not flash the split volumes directly.
3. Copy the extracted ZIP to an SD card or use ADB sideload, then install it in TWRP. This TWRP cannot decrypt internal storage; do not format DATA to work around that limitation.
4. Reboot manually after successful installation. If it stops again, save the detailed module error now shown; do not bypass pending-session checks.

The optional `TabS6-Upgrade-Check-A102.zip` performs read-only diagnosis and does not install a ROM. Run it from an SD card to compare the old and corrected guard and check directory accessibility.

Charging check: this charger raised the battery from 15% to 65% in about 69 minutes with continuous PDIC/Fast/HV1 status and a peak temperature of 31.4°C. Rated capacity remains 7040mAh.
