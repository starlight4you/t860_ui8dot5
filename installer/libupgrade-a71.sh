# A71 format 2. Appended after the audited common and vendor libraries.
# Exact source and support hashes are rendered from the pinned A71 profile.
A71_SOURCE_SYSTEM_SHA=@@SOURCE_SYSTEM_SHA@@
A71_SOURCE_A46_SHA=@@SOURCE_A46_SHA@@
A71_SOURCE_A70_SHA=@@SOURCE_A70_SHA@@
A71_OPERATION_BANNER='Galaxy Tab S6 One UI 8.5 A71 experimental upgrade (X710 donor)'
A71_SUPPORT_ROWS='@@SUPPORT_ROWS@@'
CACHE_BLOCK=/dev/block/sda27
CACHE_BYTES=419430400
DATA_BLOCK=/dev/block/sda30
CACHE_MOUNT=$WORK/source-cache
CACHE_OWN_MOUNT=0
A71_COMPLETE=0
UPGRADE_PREFLIGHT_ONLY=${4:-}

cleanup() {
    cleanup_result=$?
    trap - EXIT HUP INT TERM
    set +e
    if ! vendor_cleanup; then cleanup_result=1; A71_COMPLETE=0; fi
    if [ "$CACHE_OWN_MOUNT" = 1 ]; then
        if ! umount "$CACHE_MOUNT"; then cleanup_result=1; A71_COMPLETE=0; fi
    fi
    source_mount_count=$(awk -v p="$SOURCE_MOUNT" '$2==p {n++} END {print n+0}' /proc/mounts) || source_mount_count=UNKNOWN
    case "$source_mount_count" in
        0) ;;
        1) if ! umount "$SOURCE_MOUNT"; then cleanup_result=1; A71_COMPLETE=0; fi ;;
        *) cleanup_result=1; A71_COMPLETE=0 ;;
    esac
    work_mount_count=$(awk -v p="$WORK" '$2==p || index($2,p "/")==1 {n++} END {print n+0}' /proc/mounts) || work_mount_count=UNKNOWN
    case "$work_mount_count" in
        0) ;;
        *) cleanup_result=1; A71_COMPLETE=0
           ui_print 'ERROR: temporary mount state not clear; evidence directory retained.' ;;
    esac
    if [ "$A71_COMPLETE" = 1 ]; then
        rm -rf "$WORK"
    else
        ui_print "Installation stopped. Evidence and original policy retained at $WORK; remain in Recovery."
    fi
    exit "$cleanup_result"
}

a71_extract_support() {
    printf '%s\n' "$A71_SUPPORT_ROWS" > "$WORK/support-pins.tsv"
    while IFS="$TAB" read -r name size sha; do
        check_number "$size"; check_sha "$sha"
        unzip -p "$ZIP" "rom/support/$name" > "$WORK/$name" || abort "Missing support: $name"
        check_equal "$name bytes" "$(stat -c %s "$WORK/$name")" "$size"
        check_equal "$name SHA256" "$(hash_file "$WORK/$name")" "$sha"
    done < "$WORK/support-pins.tsv"
    chmod 0700 "$WORK/vendor-guard" "$WORK/mainline-guard" || abort 'Cannot prepare readonly guards'
}

check_source_identity() {
    check_equal 'Installed Android SDK' "$(old_property ro.build.version.sdk)" 36
    check_equal 'Installed system model' "$(old_property ro.product.system.model)" SM-T860
    installed_oneui=$(old_property ro.build.version.oneui) || abort 'Invalid installed One UI property'
    installed_sha=$(hash_file "$SYSTEM_BLOCK") || abort 'Cannot verify installed SYSTEM'
    case "$installed_oneui" in
        80000)
            case "$installed_sha" in
                "$A71_SOURCE_SYSTEM_SHA"|"$A71_SOURCE_A46_SHA") ;;
                *) abort 'Installed One UI 8 SYSTEM is not a reviewed v0.48.1 source' ;;
            esac
            ;;
        80500)
            if [ "$installed_sha" = "$(config system.sha256)" ]; then
                SYSTEM_ALREADY_VERIFIED=1
                ui_print 'Exact target SYSTEM already verified; retrying PRODUCT from this package.'
            else
                check_equal 'Audited A70 experimental SYSTEM' "$installed_sha" "$A71_SOURCE_A70_SHA"
                ui_print 'Exact audited A70 source verified; installing both complete partitions.'
            fi
            ;;
        *) abort "Unsupported installed One UI: $installed_oneui" ;;
    esac
}

a71_unmount_vendor() {
    awk '{ print $1 "\t" $2 }' /proc/mounts > "$WORK/vendor-mounts"
    while IFS="$TAB" read -r source point; do
        resolved=$(readlink -f "$source" 2>/dev/null || printf '%s' "$source")
        case "$resolved:$point" in
            "$VENDOR_BLOCK":*|*:/vendor)
                check_equal 'Mounted VENDOR source' "$resolved" "$VENDOR_BLOCK"
                case "$ZIP" in "$point"|"$point"/*) abort 'Move ZIP off VENDOR before installation' ;; esac
                umount "$point" || abort "Cannot unmount $point"
                ;;
        esac
    done < "$WORK/vendor-mounts"
    for holder in /sys/class/block/sda25/holders/*; do
        [ ! -e "$holder" ] || abort 'Active mapper holds VENDOR'
    done
}

a71_existing_mount() {
    # Caller checks partition aliases/sizes independently. Do not accept a
    # nested bind with a different filesystem root as the real DATA/CACHE root.
    point=$1; block=$2; filesystem=$3
    mount_row=$(awk -v p="$point" '$2 == p {n++; row=$1 " " $3} END {if(n!=1) exit 1; print row}' /proc/mounts) || return 1
    mount_source=${mount_row%% *}; mount_type=${mount_row#* }
    check_equal "$point filesystem" "$mount_type" "$filesystem"
    check_equal "$point block" "$(readlink -f "$mount_source")" "$block"
    root_field=$(awk -v p="$point" '$5 == p {n++; r=$4} END {if(n!=1) exit 1; print r}' /proc/self/mountinfo) || abort "Ambiguous $point mountinfo"
    check_equal "$point filesystem root" "$root_field" /
    [ -d "$point" ] && [ ! -L "$point" ] || abort "Unsafe $point directory"
}

a71_check_mainline() {
    require_block "$DATA_BLOCK"
    check_equal 'DATA alias' "$(readlink -f /dev/block/by-name/userdata)" "$DATA_BLOCK"
    a71_existing_mount /data "$DATA_BLOCK" f2fs || abort 'Mount existing DATA in TWRP before retry; installer will not mount or format DATA'
    check_block cache "$CACHE_BLOCK" "$CACHE_BYTES"
    cache_mount_count=$(awk '$2=="/cache" {n++} END {print n+0}' /proc/mounts) || abort 'Cannot inspect existing CACHE mount state'
    case "$cache_mount_count" in 0|1) ;; *) abort 'Ambiguous CACHE mounts' ;; esac
    if [ "$cache_mount_count" = 1 ]; then
        a71_existing_mount /cache "$CACHE_BLOCK" ext4 || abort 'CACHE mount identity unavailable'
        CACHE_ROOT=/cache
    else
        mkdir "$CACHE_MOUNT" || abort 'Cannot prepare readonly CACHE mount'
        mount -t ext4 -o ro,noload "$CACHE_BLOCK" "$CACHE_MOUNT" || abort 'Cannot read existing CACHE'
        CACHE_OWN_MOUNT=1
        CACHE_ROOT=$CACHE_MOUNT
    fi
    # T860 has no METADATA partition. Never silently scan an unrelated mount.
    [ ! -e /dev/block/by-name/metadata ] || abort 'Unexpected METADATA hardware layout'
    metadata_mount_count=$(awk '$2=="/metadata" {n++} END {print n+0}' /proc/mounts) || abort 'Cannot inspect existing METADATA mount state'
    case "$metadata_mount_count" in 0|1) ;; *) abort 'Ambiguous METADATA mounts' ;; esac
    if [ "$metadata_mount_count" = 1 ]; then
        metadata_source=$(awk '$2=="/metadata" {n++; s=$1} END {if(n!=1) exit 1; print s}' /proc/mounts) || abort 'Ambiguous METADATA mount'
        check_equal 'METADATA backing block' "$(readlink -f "$metadata_source")" "$CACHE_BLOCK"
        "$WORK/mainline-guard" "$WORK/apex-factory.tsv" /data/apex/active \
            /data/apex/sessions "$CACHE_ROOT/apex/sessions" "$CACHE_ROOT/metadata/apex/sessions" \
            "$CACHE_ROOT/t860-metadata/apex/sessions" /metadata/apex/sessions \
            > "$WORK/mainline-check.txt" 2>&1 || abort 'System module preflight refused; see mainline-check.txt. No update files removed.'
    else
        "$WORK/mainline-guard" "$WORK/apex-factory.tsv" /data/apex/active \
            /data/apex/sessions "$CACHE_ROOT/apex/sessions" "$CACHE_ROOT/metadata/apex/sessions" \
            "$CACHE_ROOT/t860-metadata/apex/sessions" \
            > "$WORK/mainline-check.txt" 2>&1 || abort 'System module preflight refused; see mainline-check.txt. No update files removed.'
    fi
    if [ "$CACHE_OWN_MOUNT" = 1 ]; then
        umount "$CACHE_MOUNT" || abort 'Cannot release readonly CACHE'
        CACHE_OWN_MOUNT=0
        rmdir "$CACHE_MOUNT"
    fi
    ui_print 'Existing DATA/CACHE system module state passed readonly preflight.'
}

upgrade_main() {
    ui_print "$A71_OPERATION_BANNER"
    case "$UPGRADE_PREFLIGHT_ONLY" in ''|--preflight-only) ;; *) abort 'Invalid installation mode' ;; esac
    check_equal 'Recovery model' "$(getprop ro.product.model)" SM-T860
    check_equal 'Package format' "$(config format)" 2
    check_equal 'Target model' "$(config target)" SM-T860
    check_equal 'Target SDK' "$(config target_sdk)" 36
    check_equal 'Target One UI' "$(config target_oneui)" 80500
    check_equal 'Donor build' "$(config donor_build)" X710XXS6EZH3
    check_equal 'Data policy' "$(config data_policy)" PRESERVE
    check_equal 'Adaptation profile' "$(config adaptation)" A71_ONE_S6_CODEC2_POLICY
    check_block system "$SYSTEM_BLOCK" "$SYSTEM_BYTES"
    check_block product "$PRODUCT_BLOCK" "$PRODUCT_BYTES"
    check_block boot "$BOOT_BLOCK" "$BOOT_BYTES"
    check_block vendor "$VENDOR_BLOCK" "$VENDOR_BYTES"
    a71_extract_support
    available_kib=$(df -Pk "$WORK" | awk 'END {print $4}')
    check_number "$available_kib"
    [ "$available_kib" -ge 131072 ] || abort 'Recovery requires 128 MiB free temporary space after support extraction'
    verify_table system "$SYSTEM_BYTES"
    verify_table product "$PRODUCT_BYTES"
    verify_payload
    unmount_targets
    a71_unmount_vendor
    check_source_system
    check_equal BOOT "$(hash_file "$BOOT_BLOCK")" "$BOOT_SHA"
    vendor_check_before
    a71_check_mainline
    if [ "$UPGRADE_PREFLIGHT_ONLY" = --preflight-only ]; then
        ui_print 'A71_PREFLIGHT_PASS: payload/source/BOOT/complete VENDOR/Mainline checked. No partition writes.'
        A71_COMPLETE=1
        return
    fi
    # No partition or policy write occurs before all checks above have passed.
    vendor_apply_policy
    [ "$SYSTEM_ALREADY_VERIFIED" = 1 ] || write_partition system "$SYSTEM_BLOCK"
    write_partition product "$PRODUCT_BLOCK"
    check_equal BOOT "$(hash_file "$BOOT_BLOCK")" "$BOOT_SHA"
    vendor_check_after
    VENDOR_WRITING=0
    A71_COMPLETE=1
    ui_print 'SYSTEM/PRODUCT and complete adapted S6 VENDOR verified. DATA preserved. Reboot manually.'
}
