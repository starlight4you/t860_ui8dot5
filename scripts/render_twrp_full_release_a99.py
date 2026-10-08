"""A99 unified stock clean install and UI8 data-preserving upgrade.
Clean installs alone bootstrap the audited S6 hardware images; upgrade uses
existing complete vendor inventory checks and two text config transaction.
"""
import hashlib
from pathlib import Path
import render_twrp_release_a99 as base

FULL = r'''
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
'''

def support(manifest, tools):
    library,payloads,spec=base.support(manifest,tools)
    text=library.decode()
    # Only the full payload preflight function is broadened; the frozen common
    # format-1 entry is never invoked by this appended unified entry.
    start=text.index('verify_payload() {');end=text.index('\nwrite_partition()',start)
    fragment=text[start:end]
    if fragment.count('for part in system product; do')!=1:raise ValueError('Payload loop differs')
    text=text[:start]+fragment.replace('for part in system product; do','for part in system product boot vendor dtbo vbmeta; do')+text[end:]
    # Rename only A99's source wrapper, preserving strict original UI8 identity.
    marker='check_source_system() {\n    A99_SOURCE_MODE=UI8_UPGRADE'
    if text.count(marker)!=1:raise ValueError('Source wrapper differs')
    text=text.replace(marker,'a99_upgrader_check_source_system() {\n    A99_SOURCE_MODE=UI8_UPGRADE')
    text+='\n'+FULL
    spec=dict(spec,id='A99_UNIFIED_STOCK_CLEAN_UI8_UPGRADE',hardware_bootstrap='CLEAN_INSTALL_ONLY_S6_BOOT_VENDOR_DTBO_VBMETA',
        library_sources={**spec['library_sources'],'scripts/render_twrp_full_release_a99.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    return text.encode(),payloads,spec
