# v1.0.2 A109 · Cumulative fixes · 2026-10-21

- Retain published A99/A100 fixes: SD storage, S Pen translation/SIS catalogs, Quick Share, Bluetooth pairing keys and primary audio routing, background fs-verity, BSOH capability handling and normal GPU fallback logging.
- Include A104 Manage accounts crash compatibility while preserving the signed Settings app and receiver security checks.
- Include user-confirmed A106 AAC hardware audio support, which incorporates A104. Supersede the temporary A105 AAC restriction; retain the signed Bluetooth app, pairing and RT scheduling fixes.
- Include user-confirmed A107 V2 vibrator AIDL compatibility and Samsung extension over the original C HAL. Exclude the failed V1. Preserve touch/gesture vibration preferences.
- Automatically isolate QCC for user 0 while keeping its system APK and data; skip already-isolated devices.
- Retain A102 module-tool fixes. Add reviewed A104/A105/A106/A107/A109 sources and transactional vibration-file additions with rollback, without bypassing source/session/hardware checks.
- No new kernel, charging or touch-threshold changes. Intermittent double-tap/first-stroke observations remain diagnostic records, not claimed fixes.
