# Shared functions for TWRP installer and command-level failure tests.
# Constants below describe the T860 physical PIT, not a donor super partition.
SYSTEM_BLOCK=/dev/block/sda24
PRODUCT_BLOCK=/dev/block/sda26
BOOT_BLOCK=/dev/block/sda20
VENDOR_BLOCK=/dev/block/sda25
SYSTEM_BYTES=6534725632
PRODUCT_BYTES=1048576000
BOOT_BYTES=67108864
VENDOR_BYTES=1379926016
BOOT_SHA=523664a8caf6b403526efa6e3b77e8645cc6f84a7573ff7e39159fa9b36843e9
VENDOR_SHA=adcd83034b123edb28f5799e7baff9004fa03f5bb9ec0ff82d911add81c1f7af
TAB=$(printf '\t')
SYSTEM_ALREADY_VERIFIED=0

config() {
    awk -F '\t' -v key="$1" '$1 == key { n++; value=$2 } END { if (n != 1 || value == "") exit 1; print value }' "$WORK/upgrade.tsv"
}
check_equal() { [ "$2" = "$3" ] || abort "$1 mismatch: expected $3; got $2"; }
check_number() { case "$1" in ''|*[!0-9]*) abort "Invalid numeric metadata" ;; esac; }
check_sha() {
    [ "${#1}" = 64 ] || abort "Invalid hash length"
    case "$1" in *[!0-9a-f]*) abort "Invalid SHA256" ;; esac
}
hash_file() { sha256sum "$1" | awk '{print $1}'; }
write_raw() { toybox dd "$@"; }
require_block() { [ -b "$1" ] || abort "Block device missing: $1"; }
check_block() {
    require_block "$2"
    check_equal "$1 path" "$(readlink -f "/dev/block/by-name/$1")" "$2"
    check_equal "$1 bytes" "$(blockdev --getsize64 "$2")" "$3"
}
check_preserved_hardware() {
    check_equal BOOT "$(hash_file "$BOOT_BLOCK")" "$BOOT_SHA"
    check_equal VENDOR "$(hash_file "$VENDOR_BLOCK")" "$VENDOR_SHA"
}
old_property() {
    awk -F '=' -v key="$1" '$1 == key { n++; if(NF!=2) bad=1; v=$2 } END { if(n!=1 || bad) exit 1; print v }' "$SOURCE_MOUNT/system/build.prop"
}
check_source_identity() {
    check_equal "Installed Android SDK" "$(old_property ro.build.version.sdk)" 36
    check_equal "Installed system model" "$(old_property ro.product.system.model)" SM-T860
    installed_oneui=$(old_property ro.build.version.oneui) || abort "Invalid installed One UI property"
    case "$installed_oneui" in
        80000) ;;
        80500)
            check_equal "Retry SYSTEM identity" "$(hash_file "$SYSTEM_BLOCK")" "$(config system.sha256)"
            SYSTEM_ALREADY_VERIFIED=1
            ui_print "Exact target SYSTEM already verified; retrying PRODUCT from this package."
            ;;
        *) abort "Installed One UI mismatch: expected 80000 or exact same-package retry; got $installed_oneui" ;;
    esac
}
check_source_system() {
    mkdir "$SOURCE_MOUNT" || abort "Cannot create source mount"
    mount -t ext4 -o ro,noload "$SYSTEM_BLOCK" "$SOURCE_MOUNT" || abort "Cannot read installed SYSTEM; restore source SYSTEM in Recovery before retrying"
    [ -f "$SOURCE_MOUNT/system/build.prop" ] || abort "Installed SYSTEM layout unsupported"
    check_source_identity
    umount "$SOURCE_MOUNT" || abort "Cannot unmount installed SYSTEM"
    rmdir "$SOURCE_MOUNT"
}
unmount_targets() {
    # Resolve aliases before unmounting. ZIP must not reside on a target FS.
    awk '{ print $1 "\t" $2 }' /proc/mounts >"$WORK/mounts"
    while IFS="$TAB" read -r source point; do
        resolved=$(readlink -f "$source" 2>/dev/null || printf '%s' "$source")
        case "$resolved:$point" in
            "$SYSTEM_BLOCK":*|"$PRODUCT_BLOCK":*|*:/system|*:/system_root|*:/product)
                case "$ZIP" in "$point"|"$point"/*) abort "Move ZIP off SYSTEM/PRODUCT before installation" ;; esac
                umount "$point" || abort "Cannot unmount $point"
                ;;
        esac
    done <"$WORK/mounts"
    # Do not write underneath an active device-mapper target.
    for node in sda24 sda26; do
        for holder in /sys/class/block/"$node"/holders/*; do
            [ ! -e "$holder" ] || abort "Active mapper holds $node"
        done
    done
}
verify_table() {
    part=$1
    total=$2
    # Android recovery mksh uses 32-bit arithmetic. A 6.5 GB SYSTEM cannot
    # participate in shell integer expressions; its 4 KiB block count can.
    total_blocks=$(awk -v bytes="$total" 'BEGIN {printf "%.0f", bytes/4096}')
    expected_index=0
    expected_offset=0
    while IFS="$TAB" read -r index offset size sha member extra; do
        [ -z "$extra" ] || abort "Unexpected chunk columns"
        check_number "$index"; check_number "$offset"; check_number "$size"; check_sha "$sha"
        check_equal "Chunk index" "$index" "$expected_index"
        check_equal "Chunk offset" "$offset" "$expected_offset"
        expected_member=$(printf 'payload/%s/%04d.img' "$part" "$index")
        check_equal "Chunk path" "$member" "$expected_member"
        remaining_blocks=$((total_blocks - expected_offset))
        expected_blocks=16384
        [ "$remaining_blocks" -ge "$expected_blocks" ] || expected_blocks=$remaining_blocks
        [ "$expected_blocks" -gt 0 ] || abort "Extra chunk in $part"
        expected_size=$((expected_blocks * 4096))
        check_equal "Chunk bytes" "$size" "$expected_size"
        [ $((size % 4096)) = 0 ] || abort "Unaligned chunk"
        expected_offset=$((expected_offset + size / 4096))
        expected_index=$((expected_index + 1))
    done <"$WORK/$part.chunks"
    check_equal "$part total blocks" "$expected_offset" "$total_blocks"
    check_equal "$part chunk count" "$expected_index" "$(config "$part.chunk_count")"
    check_sha "$(config "$part.sha256")"
}
extract_chunk() {
    unzip -p "$ZIP" "$1" >"$WORK/chunk.img" || abort "Bad ZIP member: $1"
    check_equal "Extracted bytes" "$(stat -c %s "$WORK/chunk.img")" "$2"
    check_equal "Chunk SHA256" "$(hash_file "$WORK/chunk.img")" "$3"
}
verify_payload() {
    for part in system product boot vendor dtbo vbmeta; do
        ui_print "Checking all $part payload blocks before flashing..."
        while IFS="$TAB" read -r index offset size sha member; do
            extract_chunk "$member" "$size" "$sha"
            rm -f "$WORK/chunk.img"
        done <"$WORK/$part.chunks"
    done
}
write_partition() {
    part=$1
    block=$2
    ui_print "Writing $part; keep device powered until verification finishes..."
    while IFS="$TAB" read -r index offset size sha member; do
        extract_chunk "$member" "$size" "$sha"
        write_raw if="$WORK/chunk.img" of="$block" bs=4096 seek="$offset" conv=notrunc || abort "$part write failed"
        rm -f "$WORK/chunk.img"
    done <"$WORK/$part.chunks"
    sync || abort "Cannot synchronize $part"
    ui_print "Verifying complete $part partition..."
    check_equal "$part readback" "$(hash_file "$block")" "$(config "$part.sha256")"
}
upgrade_main() {
    ui_print "Galaxy Tab S6 One UI 8.5 upgrade (X710 donor)"
    check_equal "Recovery model" "$(getprop ro.product.model)" SM-T860
    check_equal "Package format" "$(config format)" 1
    check_equal "Target model" "$(config target)" SM-T860
    check_equal "Target SDK" "$(config target_sdk)" 36
    check_equal "Target One UI" "$(config target_oneui)" 80500
    check_equal "Donor build" "$(config donor_build)" X710XXS6EZH3
    check_equal "Data policy" "$(config data_policy)" PRESERVE
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
    check_source_system
    ui_print "Checking existing T860 kernel/vendor hardware baseline..."
    check_preserved_hardware
    # All checks above precede the first partition write.
    [ "$SYSTEM_ALREADY_VERIFIED" = 1 ] || write_partition system "$SYSTEM_BLOCK"
    write_partition product "$PRODUCT_BLOCK"
    check_preserved_hardware
    ui_print "SYSTEM/PRODUCT verified. DATA preserved. Reboot manually when ready."
}

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

# A74 format 3, derived from frozen A71 format 2. Appended after the audited common and vendor libraries.
# Exact source and support hashes are rendered from the pinned A71 profile.
A71_SOURCE_SYSTEM_SHA=b3545d22d995d5ced10686e93a64883ab58ba68fe0d4b39453f0caf79747fbf0
A71_SOURCE_A46_SHA=b086ec97a5180832b033934e8fe2ac7c5972feec38580e7bb8b244526105dab3
A71_SOURCE_A70_SHA=226ac43e6d2bb9b504c1459ee074a31eb7f0ea752772793d099e6f1c9db1817b
A71_OPERATION_BANNER='Galaxy Tab S6 One UI 8.5 (S9 donor)'
A71_SUPPORT_ROWS='vendor-guard-sdk28	2694200	db7da35d2f1a7450cf255fe1e1400ba4328a8d8eee054b3636f7ff992180a7cf
vendor-guard-sdk30	2694200	b53e4e4da577f416c7c4892b93e97f391c0b675c57edcbed43c187c9712e5ccc
vendor-config-recovery-guard	2695456	dd9ff7512f202c85beaf0056ce8639bcf8958f3c95e80ab02db6e4f745744a7d
mainline-guard	2242016	4f3f04af10250a0522b4bf2805fe0567fef975da1aea9e24024d86eba8ca8176
vendor-before-policy	1869	e529d80729976c2ef41f6831820da5f387b7cdbd44f8b1b33d0e7cf9cd1462b8
vendor-after-policy	1882	efae1217c1fd598fb80f390a510c857d7adc3ff8018dc3a2571c7d32e7e3bfcc
vendor-matrix28	3435	da6aa90c2c2bdc06208ec8f3342735df0358836ddddb72d6e183b49bff8a79ee
vendor-matrix30	3435	d3b80d5fa526f1cf005e0dcfd3c1747bb10e351664d648cc3c18690134129258
apex-factory.tsv	1349	3db9c6be68d3310e1cad7af3848a675dfef9a225504ad93c830e3ecbffb3c02a
fscrypt-readonly-probe	2220224	575f5670928c27118139e43a21163c675e56049708390b0c4c1767f2f5663d22'
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
    chmod 0700 "$WORK/vendor-guard-sdk28" "$WORK/vendor-guard-sdk30" "$WORK/vendor-config-recovery-guard" "$WORK/mainline-guard" "$WORK/fscrypt-readonly-probe" || abort 'Cannot prepare readonly guards'
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
                case "$installed_sha" in "$A71_SOURCE_A70_SHA"|"45c2eb1cbd74ea6e753aa7b3759e1961c0fa89fa8b8a6859b903d8afaad4fcd3") ;; *) abort 'Installed experimental SYSTEM is not a reviewed A70/A71 source' ;; esac
                ui_print 'Exact audited A70/A71 source verified; installing both complete partitions.'
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



a99_data_fresh() {
    for p in /data/system /data/system_de /data/user_de /data/user /data/app /data/misc_de /data/misc_ce /data/vendor_de /data/vendor_ce /data/unencrypted/t860-metadata \
             /data/apex/active /data/apex/sessions; do
        if [ -e "$p" ] || [ -L "$p" ]; then
            [ -d "$p" ] && [ ! -L "$p" ] || return 1
            contents=$(ls -A "$p") || return 1
            [ -z "$contents" ] || return 1
        fi
    done
}
a99_upgrader_check_source_system() {
    A99_SOURCE_MODE=UI8_UPGRADE
    mkdir "$SOURCE_MOUNT" || abort 'Cannot prepare source view'
    mount -t ext4 -o ro,noload "$SYSTEM_BLOCK" "$SOURCE_MOUNT" || abort 'Prepare SYSTEM as ext4 in TWRP for clean installation'
    if [ -f "$SOURCE_MOUNT/system/build.prop" ]; then
        check_source_identity
        if [ "$SYSTEM_ALREADY_VERIFIED" = 1 ]; then
            if a99_data_fresh && [ ! -e /data/unencrypted/t860-metadata ]; then A99_SOURCE_MODE=CLEAN_INSTALL
            else A99_SOURCE_MODE=IDENTICAL_REINSTALL; fi
        fi
    else
        a99_data_fresh || abort 'No reviewed source SYSTEM; clean DATA needed for a new installation'
        [ -z "$(ls -A "$SOURCE_MOUNT" | awk '$0!="lost+found"')" ] || abort 'Unrecognized SYSTEM contents'
        A99_SOURCE_MODE=CLEAN_INSTALL
        ui_print 'Clean installation on verified S6 hardware.'
    fi
    umount "$SOURCE_MOUNT" || abort 'Cannot release source view'
    rmdir "$SOURCE_MOUNT"
}
a99_prepare_upgrade_modules() {
    [ "$A99_SOURCE_MODE" = UI8_UPGRADE ] || return 0
    "$WORK/mainline-guard" --upgrade-hold "$WORK/apex-factory.tsv" /data/apex/active \
        /data/apex/sessions /cache/apex/sessions /cache/metadata/apex/sessions \
        /metadata/apex/sessions > "$WORK/mainline-backup.txt" 2>&1 || abort 'Module backup refused; user data not cleared'
    sync
}
a71_check_mainline() {
    require_block "$DATA_BLOCK"
    check_equal 'DATA alias' "$(readlink -f /dev/block/by-name/userdata)" "$DATA_BLOCK"
    a71_existing_mount /data "$DATA_BLOCK" f2fs || abort 'Mount DATA in TWRP; no automatic format or decryption'
    check_block cache "$CACHE_BLOCK" "$CACHE_BYTES"
    cache_count=$(awk '$2=="/cache" {n++} END {print n+0}' /proc/mounts) || abort 'Cannot inspect CACHE'
    case "$cache_count" in 0|1) ;; *) abort 'Ambiguous CACHE mounts' ;; esac
    if [ "$cache_count" = 1 ]; then
        a71_existing_mount /cache "$CACHE_BLOCK" ext4 || abort 'CACHE mount differs'
        CACHE_ROOT=/cache
    else
        mkdir "$CACHE_MOUNT" || abort 'Cannot prepare readonly CACHE'
        mount -t ext4 -o ro,noload "$CACHE_BLOCK" "$CACHE_MOUNT" || abort 'Cannot read CACHE'
        CACHE_OWN_MOUNT=1
        CACHE_ROOT=$CACHE_MOUNT
    fi
    [ ! -e /dev/block/by-name/metadata ] || abort 'Unexpected physical METADATA'
    metadata_count=$(awk '$2=="/metadata" {n++} END {print n+0}' /proc/mounts) || abort 'Cannot inspect METADATA'
    case "$metadata_count" in 0|1) ;; *) abort 'Ambiguous METADATA mounts' ;; esac
    if [ "$metadata_count" = 1 ]; then
        metadata_block=$(awk '$2=="/metadata" {n++; s=$1} END {if(n!=1) exit 1; print s}' /proc/mounts)
        metadata_root=$(awk '$5=="/metadata" {n++; r=$4} END {if(n!=1) exit 1; print r}' /proc/self/mountinfo)
        check_equal 'METADATA backing' "$(readlink -f "$metadata_block")" "$DATA_BLOCK"
        check_equal 'METADATA root' "$metadata_root" /unencrypted/t860-metadata
    fi
    for p in /data/unencrypted/t860-metadata-a82-pending /data/unencrypted/t860-metadata/vold/checkpoint \
             "$CACHE_ROOT/t860-metadata/vold/checkpoint" "$CACHE_ROOT/t860-metadata-a82-legacy-retained/vold/checkpoint"; do
        [ ! -e "$p" ] && [ ! -L "$p" ] || abort 'Pending metadata/checkpoint requires separate recovery'
    done
    if [ "$A99_SOURCE_MODE" = IDENTICAL_REINSTALL ]; then
        # Package SYSTEM is the unmodified known-working snapshot. No factory
        # APEX or native view changes are permitted in PRODUCT by the builder.
        check_equal 'Identical source/target SYSTEM' "$(config system.sha256)" 'c2c249d94e4028ba3c550bb4a51fe2c3397bf80f4f8b9f82ad8236f3ed2340a8'
        for p in /data /data/unencrypted /data/unencrypted/t860-metadata; do
            [ -d "$p" ] && [ ! -L "$p" ] || abort 'Canonical metadata backing missing/unsafe'
            "$WORK/fscrypt-readonly-probe" "$p" >> "$WORK/metadata-preflight.txt" 2>&1 || abort 'Metadata must be outside FBE'
        done
        check_equal 'Metadata owner/mode' "$(stat -c '%u:%g:%a' /data/unencrypted/t860-metadata)" 0:0:755
        "$WORK/mainline-guard" --identical-system-reinstall "$WORK/apex-factory.tsv" /data/apex/active \
            /data/apex/sessions /data/unencrypted/t860-metadata/apex/sessions \
            "$CACHE_ROOT/t860-metadata/apex/sessions" "$CACHE_ROOT/t860-metadata-a82-legacy-retained/apex/sessions" \
            "$CACHE_ROOT/apex/sessions" "$CACHE_ROOT/metadata/apex/sessions" \
            > "$WORK/mainline-check.txt" 2>&1 || abort 'Active/session state differs; no updates removed'
        ui_print 'Identical SYSTEM reinstall: current DATA metadata and existing active modules preserved.'
    else
        # Audited UI8 uses the same ICE/FBE storage contract. Preserve its
        # credentials, apps, accounts and encrypted file inodes.
        case "$A99_SOURCE_MODE" in UI8_UPGRADE|CLEAN_INSTALL) ;; *) abort 'Unsupported data migration source' ;; esac
        for p in /data/unencrypted/t860-metadata "$CACHE_ROOT/t860-metadata" "$CACHE_ROOT/t860-metadata-a82-legacy-retained"; do
            [ ! -e "$p" ] && [ ! -L "$p" ] || abort 'Unexpected legacy metadata; separate migration required'
        done
        "$WORK/fscrypt-readonly-probe" /data >> "$WORK/metadata-preflight.txt" 2>&1 || abort 'DATA root must be outside FBE'
        if [ -e /data/unencrypted ] || [ -L /data/unencrypted ]; then
            "$WORK/fscrypt-readonly-probe" /data/unencrypted >> "$WORK/metadata-preflight.txt" 2>&1 || abort 'Private backing parent must be outside FBE'
        fi
        "$WORK/mainline-guard" --upgrade-preflight "$WORK/apex-factory.tsv" /data/apex/active \
            /data/apex/sessions "$CACHE_ROOT/apex/sessions" "$CACHE_ROOT/metadata/apex/sessions" \
            /metadata/apex/sessions \
            > "$WORK/mainline-check.txt" 2>&1 || abort 'Pending or unsafe system module state; no updates removed'
        ui_print 'UI8 data and credentials preserved; target metadata initialized on first boot.'
    fi
    if [ "$CACHE_OWN_MOUNT" = 1 ]; then
        umount "$CACHE_MOUNT" || abort 'Cannot release CACHE'
        CACHE_OWN_MOUNT=0
        rmdir "$CACHE_MOUNT"
    fi
}

upgrade_main() {
    ui_print "$A71_OPERATION_BANNER"
    case "$UPGRADE_PREFLIGHT_ONLY" in ''|--preflight-only) ;; *) abort 'Invalid installation mode' ;; esac
    check_equal 'Recovery model' "$(getprop ro.product.model)" SM-T860
    check_equal 'Package format' "$(config format)" 3
    check_equal 'Target model' "$(config target)" SM-T860
    check_equal 'Target SDK' "$(config target_sdk)" 36
    check_equal 'Target One UI' "$(config target_oneui)" 80500
    check_equal 'Donor build' "$(config donor_build)" X710XXS6EZH3
    check_equal 'Data policy' "$(config data_policy)" PRESERVE
    check_equal 'Adaptation profile' "$(config adaptation)" A74_TWO_S6_CONFIGS
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
        ui_print 'A99_PREFLIGHT_PASS: payload/source/BOOT/complete VENDOR/Mainline checked. No partition writes.'
        A71_COMPLETE=1
        return
    fi
    # No partition or policy write occurs before all checks above have passed.
    a99_prepare_upgrade_modules
    vendor_apply_policy
    [ "$SYSTEM_ALREADY_VERIFIED" = 1 ] || write_partition system "$SYSTEM_BLOCK"
    write_partition product "$PRODUCT_BLOCK"
    check_equal BOOT "$(hash_file "$BOOT_BLOCK")" "$BOOT_SHA"
    vendor_check_after
    VENDOR_WRITING=0
    A71_COMPLETE=1
    ui_print 'SYSTEM/PRODUCT and complete two-config S6 VENDOR verified. DATA preserved. Reboot manually.'
}


DTBO_BLOCK=/dev/block/sda19
DTBO_BYTES=10485760
DTBO_SHA=864ca763a1362a77aa929c3e2f147baa70196c31401b52f76bf0f879d7eb99ec
VBMETA_BLOCK=/dev/block/sdd22
VBMETA_BYTES=65536
STOCK_BOOT_SHA=714ae657b927ba64c8ee58cc03d16370ad2f05a9c020086df5b2d73488a9ed1f
STOCK_VENDOR_SHA=b890c903bc8ad68bcf0f4d16fbae79c35485ebdc0e49e4376139635e67ee40c4

a99_check_vbmeta_source() {
    toybox dd if="$VBMETA_BLOCK" of="$WORK/vbmeta-prefix" bs=8320 count=1 2>/dev/null || abort 'Cannot inspect VBMeta'
    [ "$(stat -c %s "$WORK/vbmeta-prefix")" = 8320 ] || abort 'Short VBMeta source'
    source_vbmeta=$(hash_file "$WORK/vbmeta-prefix")
    case "$source_vbmeta" in
        b79f51f4e96b62ed1c0e9e0276838ca7727b0139ec02699463fd114741890888|24f81a45b1f0d074fab40133fe2da91db4f3c6b5e0d612adecd21c86b62a8afe) ;;
        *) abort 'Unreviewed S6 VBMeta source' ;;
    esac
}
check_source_system() {
    if a99_data_fresh; then
        A99_SOURCE_MODE=CLEAN_INSTALL
        ui_print 'Clean installation from verified S6 stock/project hardware.'
        return
    fi
    a99_upgrader_check_source_system
}
a99_check_hardware() {
    check_equal DTBO "$(hash_file "$DTBO_BLOCK")" "$DTBO_SHA"
    a99_check_vbmeta_source
    source_boot=$(hash_file "$BOOT_BLOCK")
    if [ "$A99_SOURCE_MODE" = CLEAN_INSTALL ]; then
        case "$source_boot" in "$STOCK_BOOT_SHA"|"$BOOT_SHA") ;; *) abort 'Unreviewed clean-install S6 BOOT' ;; esac
        source_vendor=$(hash_file "$VENDOR_BLOCK")
        if [ "$source_vendor" = "$STOCK_VENDOR_SHA" ]; then
            ui_print 'S6 official hardware source verified.'
        else
            vendor_check_before
        fi
    else
        check_equal BOOT "$source_boot" "$BOOT_SHA"
        vendor_check_before
    fi
}
upgrade_main() {
    ui_print "$A71_OPERATION_BANNER"
    check_equal 'Recovery model' "$(getprop ro.product.model)" SM-T860
    case "$UPGRADE_PREFLIGHT_ONLY" in ''|--preflight-only) ;; *) abort 'Invalid installation mode' ;; esac
    check_equal 'Package format' "$(config format)" 3
    check_equal 'Target model' "$(config target)" SM-T860
    check_equal 'Target SDK' "$(config target_sdk)" 36
    check_equal 'Target One UI' "$(config target_oneui)" 80500
    check_equal 'Donor build' "$(config donor_build)" X710XXS6EZH3
    check_equal 'Data policy' "$(config data_policy)" PRESERVE
    check_equal 'Adaptation profile' "$(config adaptation)" A74_TWO_S6_CONFIGS
    check_block system "$SYSTEM_BLOCK" "$SYSTEM_BYTES"
    check_block product "$PRODUCT_BLOCK" "$PRODUCT_BYTES"
    check_block boot "$BOOT_BLOCK" "$BOOT_BYTES"
    check_block vendor "$VENDOR_BLOCK" "$VENDOR_BYTES"
    check_block dtbo "$DTBO_BLOCK" "$DTBO_BYTES"
    check_block vbmeta "$VBMETA_BLOCK" "$VBMETA_BYTES"
    a71_existing_mount /data "$DATA_BLOCK" f2fs || abort 'Mount DATA in TWRP; no automatic format'
    a71_extract_support
    available_kib=$(df -Pk "$WORK" | awk 'END {print $4}')
    check_number "$available_kib"
    [ "$available_kib" -ge 131072 ] || abort '128 MiB free Recovery temporary space required'
    for part in system product boot vendor dtbo vbmeta; do
        case "$part" in system) bytes=$SYSTEM_BYTES ;; product) bytes=$PRODUCT_BYTES ;; boot) bytes=$BOOT_BYTES ;;
            vendor) bytes=$VENDOR_BYTES ;; dtbo) bytes=$DTBO_BYTES ;; vbmeta) bytes=$VBMETA_BYTES ;; esac
        verify_table "$part" "$bytes"
    done
    verify_payload
    unmount_targets
    a71_unmount_vendor
    check_source_system
    a99_check_hardware
    a71_check_mainline
    if [ "$UPGRADE_PREFLIGHT_ONLY" = --preflight-only ]; then
        ui_print 'A99_PREFLIGHT_PASS: full payload/source/hardware/metadata checked. No partition writes.'
        A71_COMPLETE=1
        return
    fi
    if [ "$A99_SOURCE_MODE" = CLEAN_INSTALL ]; then
        write_partition vendor "$VENDOR_BLOCK"
        write_partition system "$SYSTEM_BLOCK"
        write_partition product "$PRODUCT_BLOCK"
        write_partition dtbo "$DTBO_BLOCK"
        write_partition boot "$BOOT_BLOCK"
        write_partition vbmeta "$VBMETA_BLOCK"
        vendor_check_after
    else
        a99_prepare_upgrade_modules
        vendor_apply_policy
        [ "$SYSTEM_ALREADY_VERIFIED" = 1 ] || write_partition system "$SYSTEM_BLOCK"
        write_partition product "$PRODUCT_BLOCK"
        check_equal BOOT "$(hash_file "$BOOT_BLOCK")" "$BOOT_SHA"
        check_equal DTBO "$(hash_file "$DTBO_BLOCK")" "$DTBO_SHA"
        a99_check_vbmeta_source
        vendor_check_after
    fi
    VENDOR_WRITING=0
    A71_COMPLETE=1
    ui_print 'Installation verified. User data preserved unless cleared beforehand. Reboot manually.'
}
