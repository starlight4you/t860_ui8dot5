# Galaxy Tab S6 SM-T860 · One UI 8.5 · v1.0.1 A100

Two packages use the same A100 repair images whose file contents and permissions match the running test tablet. **SM-T860 Wi-Fi only; not T865/T867.** Back up important data. An unlocked bootloader and the project's verified Samsung Android 12/DWH1 hardware baseline are required. Neither package replaces the bootloader or supplies PIT, EFS, persist, modem or user-data images.

| Package after extraction | Purpose | Data handling |
|---|---|---|
| AP_TabS6_OneUI8.5_v1.0.1_A100_Clean_Odin.tar.md5 | Clean installation with Odin, AP slot | Manually Format Data in TWRP after flashing; internal storage is erased |
| TabS6-OneUI8.5-v1.0.1-A100-Upgrade-TWRP.zip | Upgrade from the audited project UI8 v0.48.1, v1.0.0/A99 or current A100 trees | Keeps apps, accounts, credentials and files; no Format Data |

## Download and extract

Download **all volumes of one package**:

- Clean installation: `Clean-Odin-v1.0.1-A100.7z.001` through `.004` (4 volumes).
- Data-preserving upgrade: `Upgrade-TWRP-v1.0.1-A100.7z.001` through `.003` (3 volumes).

Keep that group's volumes in the same folder, without renaming them. Open `.7z.001` in 7-Zip / Keka to extract the original `.tar.md5` or complete `.zip`. **Do not flash individual volumes. GitHub's automatically generated Source code archives are not flashable ROM packages.**

Download `SHA256SUMS`. Verify each downloaded volume and the extracted original package. Linux: `sha256sum -c SHA256SUMS --ignore-missing`; macOS: `shasum -a 256 <filename>`; Windows PowerShell: `Get-FileHash <filename> -Algorithm SHA256`. Files for the other package can be skipped, but every volume of your selected package is required. Extracted package hashes:

```text
Odin: 15fc234753a7825df0b604ad3741fe662adfdea7cc9a23dff30bef1c4e25c436
TWRP: 601fc2b993bddad88344cced5c73335ed7be7e44da2cbdc6cf043a3a4e6a9bbf
```

## Clean installation with Odin

1. Prepare Odin and Samsung USB drivers on Windows. With the tablet powered off, hold both volume buttons and connect USB to the PC, then follow the Download Mode prompts. Unlock the bootloader beforehand.
2. Load the extracted `.tar.md5` into **AP** and wait for the MD5 check. Leave BL, CP and CSC empty. Uncheck **Auto Reboot**. Leave **Re-Partition, Nand Erase and Flash Lock unchecked**, and do not load a PIT.
3. Click Start and wait for PASS. The AP contains SYSTEM, PRODUCT, VENDOR, BOOT, DTBO, VBMeta and the verified TWRP Recovery.
4. Keep USB connected. Hold Power + Volume Down until the screen turns black, then immediately switch to Power + Volume Up to enter TWRP. Select **Wipe → Format Data → type yes**. This erases internal storage. **Do not format the external SD card.**
5. Select **Reboot → System** and complete initial setup. The Odin package already contains the ROM; do not flash the upgrade ZIP afterward.
6. **Apply the QCC user-level isolation below after a clean installation.** This is DATA state and does not survive Format Data. An upgrade retains existing isolation.

The AP itself does not contain a userdata/cache erase payload; the manual Format Data step makes this a clean installation. If the device remains in Download Mode, repeat step 4 to enter Recovery.

The developer's [Samsung flashing instructions](https://topjohnwu.github.io/Magisk/install.html#samsung-devices) provide background on loading AP TAR files. This ROM does not require Magisk.

## Upgrade with TWRP while preserving data

1. Copy the **fully extracted ZIP** to a location readable by TWRP, such as an external SD card.
2. Enter the project's TWRP **3.7.0_9-15_mentalmuso** and confirm DATA mounts. **Do not Format Data or wipe SYSTEM/PRODUCT first.**
3. Select Install and flash the ZIP. The installer first verifies all payloads, the existing source system, hardware files and module state.
4. Wait for **A100 upgrade verified**, then manually select Reboot → System.

The upgrade writes complete SYSTEM and PRODUCT images and performs a verified three-file VENDOR transaction: two existing compatibility configurations and the display diagnostic library. It preserves BOOT, DTBO, VBMeta and Recovery. UI8's old system-module updates are backed up while preserving their original inodes; compatible UI8.5 sources retain their existing module state.

If the installer rejects an unaudited source, pending modules, unmountable DATA or inaccessible partitions, keep the installation log and resolve the cause in the current system. **Do not bypass validation.** These source/state checks occur before partition writes.

## QCC isolation after a clean installation

The optional S9 QCC telemetry client waits for a HAL absent on T860. The verified workaround is a user 0 uninstall that preserves data. Ordinary disable-user did not stop this persistent client. Its factory APK and other underlying services remain in the ROM.

After initial setup, enable USB debugging and use Android platform-tools on your computer:

```text
adb shell getprop ro.product.model
adb shell sha256sum /system_ext/app/QCC/QCC.apk
```

The model must be `SM-T860` and the APK SHA256 must be `44315310e814f2294789cca3b7b9b6e5d484d88b186c35b7e32101784a94f00e`. Only after confirming both, run:

```text
adb shell pm uninstall -k --user 0 --versionCode 6 com.qti.qcc
adb shell sync
adb reboot
```

Wait for uninstall to return Success before continuing. This affects only the specified QCC version for that user and preserves its data. Upgrade users whose QCC is already isolated do not repeat this step.

## Fixes, verification and remaining limitations

This release includes the SD mount-parameter repair, original signed Quick Share preinstallation, SIS language catalog and dual-cache migration, Bluetooth pairing persistence and A2DP primary routing, AFC startup permissions, a narrowly scoped fs-verity permission, corrected BSOH capability and removal of one normal GPU fallback diagnostic call. Rejected Bluetooth v1/v2 and SBC encodedFormats candidates are not included.

- Physical S Pen translation into Arabic and EDIFIER MR3 SBC speaker playback were verified. Other languages, translation with every network disabled, other headphones/codecs and actual Quick Share transfers have not been fully tested.
- Actual slow charging and intermittent double-tap/first-stroke reports still lack controlled reproduction. Document edge/perspective scanning is unavailable; some portrait libraries and all AI modes are not fully certified.
- The existing pause of Google Play system-module updates is retained.
- Galaxy Store catalog compatibility configuration is application DATA and is not copied from the test tablet into firmware. A clean installation or clearing Store storage needs configuration for the specifically verified Store version; this package does not claim to resolve every Store catalog restriction.
- SYSTEM/PRODUCT free space meets the original 64 MiB stage threshold, but not the stable-release targets of 256 MiB/100 MiB.

Package formats, image readbacks, every payload and the upgrade transactions were checked. The actual tablet passed the complete upgrade package's **read-only Recovery preflight**, with all six partition hashes unchanged. **No new Odin clean flash, DATA format or full TWRP upgrade was performed on the test tablet.** The fixes were verified on the running tablet; its file contents and permissions match the packaged images.
