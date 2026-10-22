# Galaxy Tab S6 SM-T860 · One UI 8.5 · v1.0.3 A111

SM-T860 Wi-Fi only. Back up important data, unlock the bootloader and verify SHA256SUMS before flashing.

## Download and extraction

Odin and TWRP each have a separate set of 7z volumes. Download every volume in the chosen set into one directory, then open `.7z.001` with 7-Zip or Keka to extract the complete flashing file. Never flash individual volumes. Verify the extracted file's SHA256 as well.

## Clean Odin installation

1. Start with the project's T860 Android 12 / DWH1 hardware base and enter Download Mode.
2. In Windows Odin AP, select `AP_TabS6_OneUI8.5_v1.0.3_A111_Clean_Odin.tar.md5`. Leave BL/CP/CSC empty and disable Auto Reboot. Do not load a PIT or enable Re-Partition, Nand Erase or Flash Lock.
3. After PASS, boot directly into the included TWRP. Select Wipe → Format Data → type yes. This erases internal storage; do not format the external SD card.
4. Reboot → System and complete setup. No upgrade ZIP, Magisk or manual QCC command is needed.

AP includes SYSTEM, PRODUCT, VENDOR, BOOT, DTBO, VBMeta and Recovery. It contains no userdata, CACHE, PIT, bootloader, modem, EFS or persist payload.

## Data-preserving TWRP upgrade

**Only upgrade an existing One UI 8.5 installation. This upgrade ZIP does not support One UI 8 (including v0.48.1), One UI 4.1, stock firmware or other ROMs. Use the clean Odin installation when coming from those systems.**

1. Place the complete `TabS6-OneUI8.5-v1.0.3-A111-Upgrade-TWRP.zip` on an external SD card/USB OTG, or install through ADB sideload.
2. Install directly with the project TWRP 3.7.0_9-15_mentalmuso. Do not wipe SYSTEM/PRODUCT/VENDOR first and do not Format Data. This TWRP cannot decrypt internal storage; formatting is not required to work around that limitation.
3. The installer has no installed-version check, SYSTEM/VENDOR source-tree whitelist or required minor-version list. You must confirm that the installed system is One UI 8.5. Model, partition layout, project kernel/DTBO/VBMeta hardware baseline, payload integrity, DATA access and system-module safety checks remain.
4. Wait for `A111 upgrade verified`, then reboot manually.

The upgrade replaces complete SYSTEM, PRODUCT and VENDOR images. It preserves BOOT, DTBO, VBMeta, Recovery and user data. Custom changes inside replaced system partitions are overwritten. Apps, accounts, lock credentials and personal files are retained; vibration preferences are unchanged. After a power loss or interrupted write, remain in Recovery and reinstall the same complete upgrade ZIP. Do not format DATA. If preflight fails, save recovery.log and the indicated evidence directory.

## Build notes

- Retains the accumulated SD storage, translation catalogs, Quick Share, Bluetooth pairing/audio/AAC, Manage accounts, vibration and QCC isolation fixes, and adds A110 S Pen legacy HAL command compatibility.
- Release images exclude local ADB root debugging: `ro.debuggable=0`, USB debugging authorization retained, production SELinux policy and no permissive debugging domain.
- S Pen charging start/stop commands have been verified at the original Wacom driver. Actual Bluetooth pen pairing, charging status and remote actions still require testing by a reporter with a pen.
- QCC isolation runs for the primary user after boot completes, keeps data and the system APK, and skips already-isolated devices.
- No kernel, fast-charge parameter, touch threshold or vibration-preference changes. Intermittent double-tap wake and first-stroke delays are not claimed as fixed in this release.
