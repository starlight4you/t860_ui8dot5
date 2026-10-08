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
    for part in system product; do
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
