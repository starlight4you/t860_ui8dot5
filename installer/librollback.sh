# Separate restore entry point, appended to the pinned shared installer library.
# Restore an entire known snapshot; never mix old framework into a new donor.
rollback_main() {
    ui_print "RESTORE A46 CURRENT ONE UI 8 SYSTEM/PRODUCT (not the UI8.5 upgrade)"
    check_equal "Recovery model" "$(getprop ro.product.model)" SM-T860
    check_equal "Package format" "$(config format)" 1
    check_equal "Package mode" "$(config mode)" SOURCE_ROLLBACK_A46
    check_equal "Target model" "$(config target)" SM-T860
    check_equal "Restore SDK" "$(config target_sdk)" 36
    check_equal "Restore One UI" "$(config target_oneui)" 80000
    check_equal "Data policy" "$(config data_policy)" PRESERVE
    check_equal "Restore SYSTEM snapshot" "$(config system.sha256)" @@SYSTEM_SHA@@
    check_equal "Restore PRODUCT snapshot" "$(config product.sha256)" @@PRODUCT_SHA@@
    check_block system "$SYSTEM_BLOCK" "$SYSTEM_BYTES"
    check_block product "$PRODUCT_BLOCK" "$PRODUCT_BYTES"
    check_block boot "$BOOT_BLOCK" "$BOOT_BYTES"
    check_block vendor "$VENDOR_BLOCK" "$VENDOR_BYTES"
    available_kib=$(df -Pk "$WORK" | awk 'END {print $4}')
    check_number "$available_kib"
    [ "$available_kib" -ge 131072 ] || abort "Recovery requires 128 MiB free temporary space"
    verify_table system "$SYSTEM_BYTES"
    verify_table product "$PRODUCT_BYTES"
    verify_payload
    unmount_targets
    check_preserved_hardware
    # A damaged or half-written SYSTEM need not mount for a full raw restore.
    write_partition system "$SYSTEM_BLOCK"
    write_partition product "$PRODUCT_BLOCK"
    check_preserved_hardware
    ui_print "Original SYSTEM/PRODUCT verified. User data state was not restored. Reboot manually."
}
