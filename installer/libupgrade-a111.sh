# A111 replaces full production images. Installed version/tree is never read.
# No userdata writes, module migration, root setup or automatic reboot.
a71_extract_support() {
    printf '%s\n' "$A111_SUPPORT_ROWS" > "$WORK/support-pins.tsv"
    while IFS="$TAB" read -r name size sha; do
        check_number "$size"; check_sha "$sha"
        unzip -p "$ZIP" "rom/support/$name" > "$WORK/$name" || abort "Missing support: $name"
        check_equal "$name bytes" "$(stat -c %s "$WORK/$name")" "$size"
        check_equal "$name SHA256" "$(hash_file "$WORK/$name")" "$sha"
        case "$name" in *.tsv) ;; *) chmod 0700 "$WORK/$name" || abort 'Cannot prepare support' ;; esac
    done < "$WORK/support-pins.tsv"
}
unmount_targets() {
    awk '{ print $1 "\t" $2 }' /proc/mounts > "$WORK/mounts"
    while IFS="$TAB" read -r source point; do
        resolved=$(readlink -f "$source" 2>/dev/null || printf '%s' "$source")
        case "$resolved:$point" in
            "$SYSTEM_BLOCK":*|"$PRODUCT_BLOCK":*|"$VENDOR_BLOCK":*|*:/system|*:/system_root|*:/product|*:/vendor)
                case "$ZIP" in "$point"|"$point"/*) abort 'Move ZIP off target partition' ;; esac
                umount "$point" || abort "Cannot unmount $point"
                ;;
        esac
    done < "$WORK/mounts"
    for part in system product vendor; do
        case "$part" in system) block=$SYSTEM_BLOCK; bytes=$SYSTEM_BYTES;; product) block=$PRODUCT_BLOCK; bytes=$PRODUCT_BYTES;; vendor) block=$VENDOR_BLOCK; bytes=$VENDOR_BYTES;; esac
        base=${block##*/}
        for holder in /sys/class/block/$base/holders/*; do
            [ ! -e "$holder" ] || abort "Active mapper holds $part"
        done
        for source in $(awk '$1 ~ /^\/dev\/block\// {print $1}' /proc/mounts); do
            [ "$(readlink -f "$source")" != "$block" ] || abort "$part remains mounted"
        done
        "$WORK/partition-probe" writable "$block" "$bytes" >> "$WORK/write-open.txt" 2>&1 ||
            abort "$part cannot be opened for writing; no partition writes performed"
    done
}
check_hardware() {
    check_equal BOOT "$(hash_file "$BOOT_BLOCK")" "$BOOT_SHA"
    check_equal DTBO "$(hash_file "$DTBO_BLOCK")" "$DTBO_SHA"
    a99_check_vbmeta_source
}
cleanup() {
    result=$?
    trap - EXIT HUP INT TERM
    set +e
    if [ "$CACHE_OWN_MOUNT" = 1 ]; then umount "$CACHE_MOUNT" || result=1; fi
    if [ "$A71_COMPLETE" = 1 ] && [ "$result" = 0 ]; then rm -rf "$WORK"
    else ui_print "Installation stopped. Logs retained at $WORK; remain in Recovery. Do not format DATA."; fi
    exit "$result"
}
upgrade_main() {
    ui_print 'Galaxy Tab S6 One UI 8.5 v1.0.3 A111 cumulative upgrade'
    ui_print 'ONLY upgrade an existing One UI 8.5 installation. No source-version whitelist.'
    check_equal 'Recovery model' "$(getprop ro.product.model)" SM-T860
    case "$UPGRADE_PREFLIGHT_ONLY" in ''|--preflight-only) ;; *) abort 'Invalid installation mode';; esac
    check_equal 'Package format' "$(config format)" 4
    check_equal 'Target model' "$(config target)" SM-T860
    check_equal 'Target SDK' "$(config target_sdk)" 36
    check_equal 'Target One UI' "$(config target_oneui)" 80500
    check_equal 'Data policy' "$(config data_policy)" PRESERVE
    check_equal 'Adaptation profile' "$(config adaptation)" A111_FULL_PRODUCTION_IMAGES
    check_block system "$SYSTEM_BLOCK" "$SYSTEM_BYTES"
    check_block product "$PRODUCT_BLOCK" "$PRODUCT_BYTES"
    check_block vendor "$VENDOR_BLOCK" "$VENDOR_BYTES"
    check_block boot "$BOOT_BLOCK" "$BOOT_BYTES"
    check_block dtbo "$DTBO_BLOCK" "$DTBO_BYTES"
    check_block vbmeta "$VBMETA_BLOCK" "$VBMETA_BYTES"
    a71_existing_mount /data "$DATA_BLOCK" f2fs || abort 'Mount DATA in TWRP; do not format for upgrade'
    a71_extract_support
    a102_access_preflight
    available_kib=$(df -Pk "$WORK" | awk 'END {print $4}')
    check_number "$available_kib"
    [ "$available_kib" -ge 131072 ] || abort '128 MiB free Recovery temporary space required'
    verify_table system "$SYSTEM_BYTES"
    verify_table product "$PRODUCT_BYTES"
    verify_table vendor "$VENDOR_BYTES"
    verify_payload
    check_hardware
    a71_check_mainline
    unmount_targets
    if [ "$UPGRADE_PREFLIGHT_ONLY" = --preflight-only ]; then
        A71_COMPLETE=1
        ui_print 'A111_UPGRADE_PREFLIGHT_PASS: all payloads/hardware/module state checked; no partition writes.'
        return
    fi
    write_partition vendor "$VENDOR_BLOCK"
    write_partition system "$SYSTEM_BLOCK"
    write_partition product "$PRODUCT_BLOCK"
    check_hardware
    A71_COMPLETE=1
    ui_print 'A111 upgrade verified. Data preserved; reboot manually.'
}
