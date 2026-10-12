# v1.0.1 A100 · 2026-10-12

This release integrates the following repairs into a verified copy of v1.0.0/A99:

- Make SD card mount parameters compatible with the older S6 driver.
- Restore the original signed Quick Share package and permission allowlist.
- Restore the SIS translation language catalog and migrate both caches. Arabic download, retention across reboots and physical S Pen translation passed.
- Fix Bluetooth pairing persistence with native v3 and A2DP primary routing while retaining the original S6 audio policy.
- Grant AFC control-node permissions before zygote starts. Actual charging speed still needs a wall-charger test.
- Add the single required fs-verity ioctl permission for user configuration files.
- Correct the unsupported BSOH capability declaration.
- Remove one normal GPU fallback diagnostic call; composition logic and other diagnostics are unchanged.

Clean installation now uses an Odin AP package; data-preserving upgrades use a separate TWRP ZIP. Firmware does not include the test tablet's user data. See INSTALL.en.md for the clean-install QCC step and Galaxy Store catalog limitations. Intermittent double-tap wake and first-stroke reports are not marked fixed.

Verification: image/format readback, all 114 payload chunks and 20 support files in original TWRP userspace, 12 VENDOR transaction cases, and a complete read-only preflight on the actual tablet. No full clean/upgrade flash was performed.
