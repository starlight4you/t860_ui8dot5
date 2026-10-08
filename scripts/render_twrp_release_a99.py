"""Derive A99 phase installer from the fully pinned A74 transaction.

Only an identical SYSTEM reinstall preserves the four opaque active modules.
First installation requires clean DATA and absent legacy metadata; no automatic
format, update deletion, credential migration or hardware replacement.
"""
import hashlib
from pathlib import Path
import render_twrp_a74_support_ui85 as a74

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SYSTEM = 'c2c249d94e4028ba3c550bb4a51fe2c3397bf80f4f8b9f82ad8236f3ed2340a8'

METADATA = r'''

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
check_source_system() {
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
        check_equal 'Identical source/target SYSTEM' "$(config system.sha256)" '@@CURRENT_SYSTEM@@'
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
'''

def support(manifest, tools):
    if manifest['partitions']['system']['sha256'] != SOURCE_SYSTEM:
        raise ValueError('A99 only exports the exact verified SYSTEM; preserve-mode cannot upgrade it')
    if manifest['product_factory_apex_changed'] or manifest['system_files_changed']:
        raise ValueError('Reinstall path forbids APEX/native/source changes')
    legacy = dict(manifest, candidate_id=a74.CANDIDATE, source_inventory_sha256=a74.STAGE,
                  vendor_adaptation={'scope': 'TWO_EXISTING_S6_TEXT_CONFIGS_ONLY',
                                     'full_donor_vendor_replacement': False})
    library, payloads, spec = a74.a74_support(legacy)
    payloads['mainline-guard'] = tools['mainline-guard']
    payloads['fscrypt-readonly-probe'] = tools['fscrypt-readonly-probe']
    text = library.decode()
    start = text.index('a71_check_mainline() {')
    end = text.index('\nupgrade_main() {', start)
    text = text[:start] + METADATA.replace('@@CURRENT_SYSTEM@@', SOURCE_SYSTEM) + text[end:]
    text = a74.replace_once(text, 'A74 experimental upgrade (X710 donor)', '(S9 donor)')
    text = a74.replace_once(text, "A74_PREFLIGHT_PASS:", "A99_PREFLIGHT_PASS:")
    text = a74.replace_once(text, '"$WORK/vendor-config-recovery-guard" "$WORK/mainline-guard"',
                           '"$WORK/vendor-config-recovery-guard" "$WORK/mainline-guard" "$WORK/fscrypt-readonly-probe"')
    text = a74.replace_once(text, '\n    vendor_apply_policy\n', '\n    a99_prepare_upgrade_modules\n    vendor_apply_policy\n')
    start = text.index("A71_SUPPORT_ROWS='")
    end = text.index("'\nCACHE_BLOCK", start)
    rows = '\n'.join(f'{n}\t{len(b)}\t{hashlib.sha256(b).hexdigest()}' for n,b in payloads.items())
    text = text[:start] + "A71_SUPPORT_ROWS='" + rows + text[end:]
    spec = dict(spec)
    spec.update(id='A99_PHASE_RELEASE_METADATA_AWARE', format='3',
                adaptation='A74_TWO_S6_CONFIGS',
                first_install='CLEAN_INSTALL_OR_AUDITED_UI8_DATA_PRESERVING_UPGRADE',
                dirty_reinstall='EXACT_SAME_SYSTEM_ONLY', dirty_upgrade='AUDITED_UI8_ICE_FBE_INODE_PRESERVING_MODULE_BACKUP',
                active_apex_content_validation='NOT_CLAIMED_IN_IDENTICAL_SYSTEM_REINSTALL',
                library_sources={**spec['library_sources'],
                    'scripts/render_twrp_release_a99.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    return text.encode(), payloads, spec
