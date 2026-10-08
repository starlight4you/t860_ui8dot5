# A74: full S6 inventory, two exact config states, independent repair entry.
# Support is hash checked before this library's functions can be called.
VENDOR_MOUNT=$WORK/source-vendor
VENDOR_MOUNTED=0
VENDOR_WRITING=0
VENDOR_INITIAL_STATE=
VENDOR_ROLLBACK_STATE=
VENDOR_OPERATION=upgrade
VENDOR_TARGET_STATE=SDK30_ADAPTED
VENDOR_POLICY_REL=etc/seccomp_policy/samsung.software.media.c2-base-policy
VENDOR_MATRIX_REL=etc/vintf/compatibility_matrix.xml

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
    # Never use the repair guard to return a compatible source state.
    if vendor_state28=$("$WORK/vendor-guard-sdk28" "$VENDOR_MOUNT" "$1" 2> "$WORK/vendor-sdk28-check.txt"); then
        case "$vendor_state28" in SDK28_BASELINE|SDK28_ADAPTED) printf '%s\n' "$vendor_state28"; return 0 ;; esac
        return 1
    fi
    if vendor_state30=$("$WORK/vendor-guard-sdk30" "$VENDOR_MOUNT" "$1" 2> "$WORK/vendor-sdk30-check.txt"); then
        case "$vendor_state30" in SDK30_BASELINE|SDK30_ADAPTED) printf '%s\n' "$vendor_state30"; return 0 ;; esac
    fi
    return 1
}
vendor_recovery_eligible() {
    vendor_repair_state=$("$WORK/vendor-config-recovery-guard" "$VENDOR_MOUNT" recover-configs-only \
        2> "$WORK/vendor-repair-check.txt") || return 1
    [ "$vendor_repair_state" = CONFIGS_RECOVERABLE ]
}
vendor_check_before() {
    case "$VENDOR_OPERATION:$VENDOR_TARGET_STATE" in
        upgrade:SDK30_ADAPTED|restore-a70:SDK28_ADAPTED) ;;
        *) abort 'Invalid vendor operation or target' ;;
    esac
    vendor_mount_ro
    if VENDOR_INITIAL_STATE=$(vendor_guard_state any); then
        case "$VENDOR_INITIAL_STATE" in SDK28_BASELINE|SDK28_ADAPTED|SDK30_BASELINE|SDK30_ADAPTED) ;;
            *) abort 'Invalid complete vendor state' ;; esac
        VENDOR_ROLLBACK_STATE=$VENDOR_INITIAL_STATE
    else
        [ "$VENDOR_OPERATION" = restore-a70 ] || abort 'S6 vendor hardware inventory differs; use independent restore'
        vendor_recovery_eligible || abort 'Vendor damage exceeds the two reviewed configs; complete hardware restoration required'
        VENDOR_INITIAL_STATE=CONFIGS_RECOVERABLE
        # A damaged input is not a rollback target. Preserve fixed stable
        # configs on failure, and keep Recovery until SYSTEM/PRODUCT restored.
        VENDOR_ROLLBACK_STATE=SDK28_ADAPTED
        ui_print 'Only reviewed config contents are recoverable; this is not a compatible upgrade source.'
    fi
    vendor_unmount
}
vendor_check_after() {
    vendor_mount_ro
    vendor_final_state=$(vendor_guard_state any) || abort 'Complete final S6 vendor verification failed'
    check_equal 'Complete S6 vendor target' "$vendor_final_state" "$VENDOR_TARGET_STATE"
    vendor_unmount
}
vendor_state_payloads() {
    case "$1" in
        SDK28_BASELINE) VENDOR_MATRIX_PAYLOAD=$WORK/vendor-matrix28; VENDOR_POLICY_PAYLOAD=$WORK/vendor-before-policy ;;
        SDK28_ADAPTED) VENDOR_MATRIX_PAYLOAD=$WORK/vendor-matrix28; VENDOR_POLICY_PAYLOAD=$WORK/vendor-after-policy ;;
        SDK30_BASELINE) VENDOR_MATRIX_PAYLOAD=$WORK/vendor-matrix30; VENDOR_POLICY_PAYLOAD=$WORK/vendor-before-policy ;;
        SDK30_ADAPTED) VENDOR_MATRIX_PAYLOAD=$WORK/vendor-matrix30; VENDOR_POLICY_PAYLOAD=$WORK/vendor-after-policy ;;
        *) return 1 ;;
    esac
}
vendor_write_payloads() {
    # The complete guard has checked the existing inode, nlink and all xattrs.
    # Truncate/write existing files, then retain full guard until final commit.
    cat "$VENDOR_MATRIX_PAYLOAD" > "$VENDOR_MOUNT/$VENDOR_MATRIX_REL" || return 1
    cat "$VENDOR_POLICY_PAYLOAD" > "$VENDOR_MOUNT/$VENDOR_POLICY_REL" || return 1
    sync || return 1
}
vendor_apply_policy() {
    # Existing transaction entry calls this name; it now applies two configs.
    if [ "$VENDOR_INITIAL_STATE" = "$VENDOR_TARGET_STATE" ]; then
        vendor_check_after
        ui_print 'Both reviewed S6 configs already applied; complete vendor verified.'
        return
    fi
    vendor_state_payloads "$VENDOR_TARGET_STATE" || abort 'Missing reviewed target configs'
    vendor_mount_ro
    if [ "$VENDOR_INITIAL_STATE" = CONFIGS_RECOVERABLE ]; then
        [ "$VENDOR_OPERATION" = restore-a70 ] && vendor_recovery_eligible || abort 'Invalid damaged-config restore path'
    else
        check_equal 'Complete source vendor' "$(vendor_guard_state any)" "$VENDOR_INITIAL_STATE"
    fi
    mount -o remount,rw "$VENDOR_MOUNT" || abort 'Cannot mount S6 VENDOR for reviewed configs'
    VENDOR_WRITING=1
    vendor_write_payloads || abort 'Reviewed vendor config write failed'
    vendor_unmount
    vendor_check_after
    ui_print 'Two S6 configs applied; all other hardware contents and metadata verified.'
}
vendor_cleanup() {
    # On a trapped failure, restore the initial known combination. For an
    # independent repair of torn configs, retain stable SDK28+A61 instead.
    if [ "$VENDOR_WRITING" = 1 ]; then
        vendor_restored=0
        if [ "$VENDOR_MOUNTED" = 0 ]; then
            if mount -t ext4 -o ro,noload "$VENDOR_BLOCK" "$VENDOR_MOUNT"; then VENDOR_MOUNTED=1; fi
        fi
        if [ "$VENDOR_MOUNTED" = 1 ] && vendor_recovery_eligible &&
            vendor_state_payloads "$VENDOR_ROLLBACK_STATE" && mount -o remount,rw "$VENDOR_MOUNT" &&
            vendor_write_payloads && umount "$VENDOR_MOUNT"; then
            VENDOR_MOUNTED=0
            if mount -t ext4 -o ro,noload "$VENDOR_BLOCK" "$VENDOR_MOUNT"; then
                VENDOR_MOUNTED=1
                if vendor_restored_state=$(vendor_guard_state any) && [ "$vendor_restored_state" = "$VENDOR_ROLLBACK_STATE" ]; then
                    vendor_restored=1
                fi
            fi
        fi
        if [ "$vendor_restored" = 1 ]; then
            ui_print "S6 configs restored to $VENDOR_ROLLBACK_STATE; remain in Recovery."
        else
            ui_print 'ERROR: complete vendor config restoration not verified; remain in Recovery and use independent restore.'
            return 1
        fi
    fi
    if [ "$VENDOR_MOUNTED" = 1 ]; then
        if umount "$VENDOR_MOUNT"; then VENDOR_MOUNTED=0;
        else ui_print 'ERROR: cannot unmount VENDOR; remain in Recovery.'; return 1; fi
    fi
}
