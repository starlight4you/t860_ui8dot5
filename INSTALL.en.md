# Galaxy Tab S6 SM-T860 · One UI 8.5 · v1.0.2 A109

This cumulative build includes A100, A102, A104/A106, A107 V2 and automatic QCC isolation. SM-T860 Wi-Fi only. The QCC-only A108 packages are withdrawn.

Back up important data and check SHA256SUMS. For split downloads, place all volumes of one set together and open .7z.001 with 7-Zip/Keka. Extract a complete package before flashing; never flash individual volumes. Check the extracted package hash as well.

Split downloads: clean installation uses `Clean-Odin-v1.0.2-A109.7z.001` through `.004` (4 volumes); upgrades use `Upgrade-TWRP-v1.0.2-A109.7z.001` through `.003` (3 volumes).

## Clean Odin installation

1. Use a bootloader-unlocked T860 with the project Android 12/DWH1 hardware base. Enter Download Mode.
2. Select `AP_TabS6_OneUI8.5_v1.0.2_A109_Clean_Odin.tar.md5` in Windows Odin AP. Leave BL/CP/CSC empty and disable Auto Reboot. Do not load a PIT or enable Re-Partition, Nand Erase or Flash Lock.
3. Wait for PASS, then boot directly into the included TWRP. Choose Wipe → Format Data → type yes. This erases internal storage; do not format the external SD card.
4. Reboot → System and complete setup. No upgrade ZIP, manual QCC command or Magisk installation is required.

AP contains SYSTEM, PRODUCT, VENDOR, BOOT, DTBO, VBMeta and Recovery. It contains no userdata, CACHE, PIT, bootloader, modem, EFS or persist payload.

## Data-preserving TWRP upgrade

1. Put the complete `TabS6-OneUI8.5-v1.0.2-A109-Upgrade-TWRP.zip` on an SD card, or use ADB sideload.
2. Install using the project TWRP 3.7.0_9-15_mentalmuso. Do not wipe SYSTEM/PRODUCT first or Format Data. This TWRP cannot decrypt internal storage; formatting is not needed to address that limitation.
3. Reviewed sources include project UI8 v0.48.1, v1.0.0/A99, A100/A102, and complete A104, stable A105, A106/A107 or A109 patched systems.
4. Wait for `A109 upgrade verified`, then reboot manually. If source/module/hardware checks refuse the operation, save recovery.log and the specific error, resolve the cause and keep the checks enabled.

The upgrade preserves apps, accounts, lock credentials and personal files. It writes SYSTEM/PRODUCT, transactionally handles three existing VENDOR files and three new vibrator files, and preserves BOOT/DTBO/VBMeta/Recovery. Remain in Recovery after interruption and follow the recorded error; do not repeatedly format data.

## First boot and scope

- After boot completion QCC is uninstalled for user 0 with keep-data enabled; its APK/native components remain. Already-isolated devices are skipped. Original errors may briefly occur before boot completes. Optional status: `adb shell logcat -d -s T860QccPolicy:I`.
- Touch feedback, gesture vibration and other user preferences are not forcibly enabled. Restoring motor detection does not override per-scenario settings.
- AAC, accounts and vibration use the exact previously device-validated payloads. This cumulative package has offline payload/format/transaction checks; no cumulative full flash or DATA wipe was performed in this run.
- Intermittent double-tap/first-stroke observations remain without a root-cause patch. Battery capacity is confirmed at 7040mAh; remaining time is a history-based estimate. No invented capacity/charging fix is included. Ordinary app updates remain available; existing Play system-module update restrictions remain.
