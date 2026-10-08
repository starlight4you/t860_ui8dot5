# Format 2: complete S6 vendor guard and exactly one Codec2 text-policy change.
# Loaded only after this library, the native guard and both policies are pinned.
VENDOR_MOUNT=$WORK/source-vendor
VENDOR_MOUNTED=0
VENDOR_WRITING=0
VENDOR_INITIAL_STATE=
VENDOR_POLICY_REL=etc/seccomp_policy/samsung.software.media.c2-base-policy
VENDOR_BEFORE_SHA=e529d80729976c2ef41f6831820da5f387b7cdbd44f8b1b33d0e7cf9cd1462b8
VENDOR_AFTER_SHA=efae1217c1fd598fb80f390a510c857d7adc3ff8018dc3a2571c7d32e7e3bfcc

vendor_mount_ro() {
    [ "$VENDOR_MOUNTED" = 0 ] || abort 'VENDOR mount already active'
    [ -d "$VENDOR_MOUNT" ] || mkdir "$VENDOR_MOUNT" || abort 'Cannot create VENDOR mount'
    mount -t ext4 -o ro,noload "$VENDOR_BLOCK" "$VENDOR_MOUNT" || abort 'Cannot read S6 VENDOR'
    VENDOR_MOUNTED=1
}
vendor_unmount() {
    umount "$VENDOR_MOUNT" || abort 'Cannot unmount S6 VENDOR'
    VENDOR_MOUNTED=0
}
vendor_guard_state() {
    "$WORK/vendor-guard" "$VENDOR_MOUNT" "$1"
}
vendor_check_before() {
    vendor_mount_ro
    VENDOR_INITIAL_STATE=$(vendor_guard_state any) || abort 'S6 vendor hardware inventory differs'
    case "$VENDOR_INITIAL_STATE" in BASELINE|ADAPTED) ;; *) abort 'Invalid vendor state' ;; esac
    vendor_unmount
}
vendor_check_after() {
    vendor_mount_ro
    check_equal 'Complete adapted S6 vendor' "$(vendor_guard_state adapted)" ADAPTED
    vendor_unmount
}
vendor_apply_policy() {
    if [ "$VENDOR_INITIAL_STATE" = ADAPTED ]; then
        vendor_check_after
        ui_print 'Reviewed Codec2 rule already applied; complete vendor verified.'
        return
    fi
    [ "$VENDOR_INITIAL_STATE" = BASELINE ] || abort 'Missing original vendor verification'
    vendor_mount_ro
    check_equal 'Complete original S6 vendor' "$(vendor_guard_state baseline)" BASELINE
    # The native guard has checked inode links, owner/mode and every raw xattr.
    # Keep the existing inode; never replace any HAL or firmware.
    mount -o remount,rw "$VENDOR_MOUNT" || abort 'Cannot mount S6 VENDOR for one policy'
    VENDOR_WRITING=1
    cat "$WORK/vendor-after-policy" > "$VENDOR_MOUNT/$VENDOR_POLICY_REL" || abort 'Codec2 policy write failed'
    sync || abort 'Codec2 policy sync failed'
    vendor_unmount
    vendor_check_after
    # Keep rollback armed until the whole SYSTEM/PRODUCT transaction succeeds.
    ui_print 'One Codec2 rule applied; all other S6 vendor contents and metadata verified.'
}
vendor_cleanup() {
    # EXIT handling must run before WORK is removed. Retain verified rollback
    # payload on failure; restoration is reported only after whole-tree guard.
    if [ "$VENDOR_WRITING" = 1 ]; then
        if [ "$VENDOR_MOUNTED" = 0 ]; then
            if mount -t ext4 -o rw "$VENDOR_BLOCK" "$VENDOR_MOUNT"; then VENDOR_MOUNTED=1; fi
        fi
        restored=0
        if [ "$VENDOR_MOUNTED" = 1 ]; then
            if mount -o remount,rw "$VENDOR_MOUNT" &&
                cat "$WORK/vendor-before-policy" > "$VENDOR_MOUNT/$VENDOR_POLICY_REL" && sync &&
                umount "$VENDOR_MOUNT"; then
                VENDOR_MOUNTED=0
                if mount -t ext4 -o ro,noload "$VENDOR_BLOCK" "$VENDOR_MOUNT"; then
                    VENDOR_MOUNTED=1
                    if [ "$(vendor_guard_state baseline)" = BASELINE ]; then restored=1; fi
                fi
            fi
        fi
        if [ "$restored" = 1 ]; then ui_print 'Original Codec2 policy restored; remain in Recovery.'
        else ui_print 'ERROR: Codec2 restoration not verified; restore saved original policy before boot.'; fi
    fi
    if [ "$VENDOR_MOUNTED" = 1 ]; then
        if umount "$VENDOR_MOUNT"; then VENDOR_MOUNTED=0;
        else ui_print 'ERROR: cannot unmount VENDOR; remain in Recovery.'; return 1; fi
    fi
}
