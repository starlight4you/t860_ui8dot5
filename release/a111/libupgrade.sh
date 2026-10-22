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

DTBO_BLOCK=/dev/block/sda19
DTBO_BYTES=10485760
DTBO_SHA=864ca763a1362a77aa929c3e2f147baa70196c31401b52f76bf0f879d7eb99ec
VBMETA_BLOCK=/dev/block/sdd22
VBMETA_BYTES=65536
CACHE_BLOCK=/dev/block/sda27
CACHE_BYTES=419430400
DATA_BLOCK=/dev/block/sda30
CACHE_MOUNT=$WORK/source-cache
CACHE_OWN_MOUNT=0
A71_COMPLETE=0
A99_SOURCE_MODE=IDENTICAL_REINSTALL
UPGRADE_PREFLIGHT_ONLY=${4:-}
A111_SUPPORT_ROWS='mainline-guard	2242016	4f3f04af10250a0522b4bf2805fe0567fef975da1aea9e24024d86eba8ca8176
apex-factory.tsv	1349	3db9c6be68d3310e1cad7af3848a675dfef9a225504ad93c830e3ecbffb3c02a
fscrypt-readonly-probe	2220224	575f5670928c27118139e43a21163c675e56049708390b0c4c1767f2f5663d22
partition-probe	2221128	396857efa02d30f602ccabc4b9e6abd72c920ddbc755ace44c29a6e76ab787c0
upgrade-access-probe	2237944	027ca8d7b174c589e18bde6569e422e7f2ba21cebe22502840550339e08ef41e'
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
    for part in system product vendor; do
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
a102_access_preflight() {
    if "$WORK/upgrade-access-probe" /data/apex/active /data/apex/sessions > "$WORK/module-access.txt" 2>&1; then
        return 0
    fi
    while IFS= read -r line; do ui_print "$line"; done < "$WORK/module-access.txt"
    abort 'Required module directories are unreadable/unsafe in this Recovery. No partition writes performed; do not format DATA.'
}
a102_module_abort() {
    evidence=$1
    message=$2
    if [ -f "$WORK/$evidence" ]; then
        while IFS= read -r line; do ui_print "$line"; done < "$WORK/$evidence"
    fi
    abort "$message"
}
a99_check_vbmeta_source() {
    toybox dd if="$VBMETA_BLOCK" of="$WORK/vbmeta-prefix" bs=8320 count=1 2>/dev/null || abort 'Cannot inspect VBMeta'
    [ "$(stat -c %s "$WORK/vbmeta-prefix")" = 8320 ] || abort 'Short VBMeta source'
    source_vbmeta=$(hash_file "$WORK/vbmeta-prefix")
    case "$source_vbmeta" in
        b79f51f4e96b62ed1c0e9e0276838ca7727b0139ec02699463fd114741890888|24f81a45b1f0d074fab40133fe2da91db4f3c6b5e0d612adecd21c86b62a8afe) ;;
        *) abort 'Unreviewed S6 VBMeta source' ;;
    esac
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
        for p in /data /data/unencrypted /data/unencrypted/t860-metadata; do
            [ -d "$p" ] && [ ! -L "$p" ] || abort 'Canonical metadata backing missing/unsafe'
            "$WORK/fscrypt-readonly-probe" "$p" >> "$WORK/metadata-preflight.txt" 2>&1 || abort 'Metadata must be outside FBE'
        done
        check_equal 'Metadata owner/mode' "$(stat -c '%u:%g:%a' /data/unencrypted/t860-metadata)" 0:0:755
        "$WORK/mainline-guard" --identical-system-reinstall "$WORK/apex-factory.tsv" /data/apex/active \
            /data/apex/sessions /data/unencrypted/t860-metadata/apex/sessions \
            "$CACHE_ROOT/t860-metadata/apex/sessions" "$CACHE_ROOT/t860-metadata-a82-legacy-retained/apex/sessions" \
            "$CACHE_ROOT/apex/sessions" "$CACHE_ROOT/metadata/apex/sessions" \
            > "$WORK/mainline-check.txt" 2>&1 || a102_module_abort mainline-check.txt 'Active/session state differs; no updates removed'
        ui_print 'Current DATA metadata and compatible active modules preserved.'
    if [ "$CACHE_OWN_MOUNT" = 1 ]; then
        umount "$CACHE_MOUNT" || abort 'Cannot release CACHE'
        CACHE_OWN_MOUNT=0
        rmdir "$CACHE_MOUNT"
    fi
}
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
