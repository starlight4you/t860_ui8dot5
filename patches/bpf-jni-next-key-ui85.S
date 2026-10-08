/* Review source for the fixed in-function window at VA0x521c.
 * Keep ENOENT and additionally handle T860 LPM ENOTSUPP524.
 * CCMP uses NZCV=4 (Z=1) when errno==524; otherwise it compares errno to2.
 * The displaced vtable load occupies the original NOP. No new code cave.
 */
.text
.global reviewed_next_key_window
reviewed_next_key_window:
    cmp     w22, #524
    ccmp    w22, #2, #4, ne
    b.eq    .+0x74
    ldr     x8, [x20]
