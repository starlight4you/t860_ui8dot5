# v1.0.3 A111 · Cumulative fixes · 2026-10-22

- Retains all effective v1.0.2/A109 fixes: SD storage, S Pen translation/SIS catalogs, Quick Share, Bluetooth pairing and audio routing, A106 AAC, A104 Manage accounts, A107 V2 vibration, QCC keep-data isolation and background compatibility handling.
- Adds A110 S Pen legacy HAL compatibility, forwarding BLE_CHARGING / EPEN_SAVING commands to the original T860 Wacom interface without kernel changes.
- Excludes local ADB root debugging; production debugging properties and SELinux policy are retained with USB authorization.
- Removes installed-version checks and SYSTEM/VENDOR source-tree whitelists. The upgrade replaces all three images while preserving data. Model, partition, hardware baseline, payload and module safety checks remain.
- **The upgrade ZIP supports One UI 8.5 only. Use a clean Odin installation for One UI 8/v0.48.1, stock firmware or other ROMs.**
- Excludes the superseded A105 AAC restriction and failed A107 V1 vibrator. Preserves touch/gesture vibration preferences. No claim of a fix for unresolved double-tap wake, first-stroke delay or fast charging.
