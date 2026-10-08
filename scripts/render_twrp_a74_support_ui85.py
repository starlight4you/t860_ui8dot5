#!/usr/bin/env python3
"""Render separate A74 upgrade/restore support, preserving frozen A71 behavior."""
import argparse
import hashlib
import json
from pathlib import Path

import build_twrp_upgrade as transport

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = 'A74-X710-EZH3-T860-UI85-FCM4-SDK30'
STAGE = 'bf2f94d72b890db7397605f518800169cd9680424d0c366722f6db7a42fb4931'
CURRENT_A71 = '45c2eb1cbd74ea6e753aa7b3759e1961c0fa89fa8b8a6859b903d8afaad4fcd3'
SUPPORT = {
    'vendor-guard-sdk28': (2694200, 'db7da35d2f1a7450cf255fe1e1400ba4328a8d8eee054b3636f7ff992180a7cf'),
    'vendor-guard-sdk30': (2694200, 'b53e4e4da577f416c7c4892b93e97f391c0b675c57edcbed43c187c9712e5ccc'),
    'vendor-config-recovery-guard': (2695456, 'dd9ff7512f202c85beaf0056ce8639bcf8958f3c95e80ab02db6e4f745744a7d'),
    'mainline-guard': (2237192, '402e84d1c6e60087db2c78ab6869581e51dd3bdf7a5adcca3a521d57dd7b4081'),
    'vendor-before-policy': (1869, 'e529d80729976c2ef41f6831820da5f387b7cdbd44f8b1b33d0e7cf9cd1462b8'),
    'vendor-after-policy': (1882, 'efae1217c1fd598fb80f390a510c857d7adc3ff8018dc3a2571c7d32e7e3bfcc'),
    'vendor-matrix28': (3435, 'da6aa90c2c2bdc06208ec8f3342735df0358836ddddb72d6e183b49bff8a79ee'),
    'vendor-matrix30': (3435, 'd3b80d5fa526f1cf005e0dcfd3c1747bb10e351664d648cc3c18690134129258'),
    'apex-factory.tsv': (1349, '3db9c6be68d3310e1cad7af3848a675dfef9a225504ad93c830e3ecbffb3c02a'),
}


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('ambiguous A71 template derivation: ' + old[:80])
    return text.replace(old, new)


def a74_support(manifest, operation='upgrade'):
    if operation not in ('upgrade', 'restore-a70') or manifest['candidate_id'] != CANDIDATE:
        raise ValueError('A74 candidate/operation mismatch')
    if manifest['source_inventory_sha256' if operation == 'upgrade' else 'support_stage_reference_sha256'] != STAGE:
        raise ValueError('FCM4 system stage basis differs')
    profile = json.loads((ROOT / 'device/s6/twrp-installer-a74.json').read_text())
    if profile['id'] != 'A74_TWO_CONFIG_INSTALLER_CANDIDATE_V1' or profile['format'] != '3' or profile['adaptation'] != 'A74_TWO_S6_CONFIGS' or profile['candidate_id'] != CANDIDATE:
        raise ValueError('A74 profile differs')
    for relative, pin in profile['evidence'].items():
        if transport.sha_file(ROOT / relative) != pin:
            raise ValueError('A74 evidence changed: ' + relative)
    tests = json.loads((ROOT / 'docs/audit/vendor-config-transaction-ui85-a74.json').read_text())
    if not tests['all_passed'] or tests['case_count'] != 24 or not tests['original_vendor_unchanged']:
        raise ValueError('complete native config transaction evidence missing')
    if (tests['inputs']['libvendor-a74.sh'] != transport.sha_file(ROOT / 'installer/libvendor-a74.sh')
            or tests['test_source_sha256'] != transport.sha_file(ROOT / 'scripts/test_vendor_config_transaction_ui85.py')
            or not all(case['pass'] for case in tests['cases'])):
        raise ValueError('config tests do not bind current transaction implementation')
    for name in ('vendor-guard-sdk28', 'vendor-guard-sdk30', 'vendor-config-recovery-guard',
                 'vendor-before-policy', 'vendor-after-policy', 'vendor-matrix28', 'vendor-matrix30'):
        if tests['inputs'][name] != SUPPORT[name][1]:
            raise ValueError('native/config transaction test used different payload: ' + name)
    native = json.loads((ROOT / 'docs/audit/native-target-retry-ui85-a71-v2.json').read_text())
    if native['native_final_rc'] != 0 or native['zip_sha256'] != 'ef80d7d31024c6117844241aa78885bd80848d5e8adce8a3d9f91d7749ab0899' or native['system_written']:
        raise ValueError('exact A71 target retry provenance missing')
    pair = json.loads((ROOT / 'docs/audit/vendor-sdk-guard-pair-tests-ui85-a74.json').read_text())
    if not pair['pass'] or len(pair['cases']) != 42:
        raise ValueError('complete strict vendor guard evidence missing')
    if profile['library_sources'] != {
            rel: transport.sha_file(ROOT / rel) for rel in ('installer/libupgrade.sh', 'installer/libupgrade-a71.sh',
                                                           'installer/libvendor-a74.sh', 'installer/librestore-a70.sh')}:
        raise ValueError('audited installer template changed')
    # Reuse all frozen A71 source snapshot, hardware, Mainline and support
    # validation; never reinterpret an unknown ROM as an accepted source.
    old_manifest = dict(manifest)
    old_manifest['candidate_id'] = 'A71-X710-EZH3-T860-UI85-REPAIRED'
    old_manifest['source_inventory_sha256' if operation == 'upgrade' else 'support_stage_reference_sha256'] = 'e21e7efaaa1e1d06154cda4dc63ae31c1e6d5f887f9b8929c0535304607f6df7'
    _, _, old = transport.a71_support(old_manifest, operation)
    if set(profile['support']) != set(SUPPORT):
        raise ValueError('unexpected A74 support entries')
    payloads, rows = {}, []
    for name, (size, digest) in SUPPORT.items():
        entry = profile['support'][name]; path = ROOT / entry['path']
        if path.is_symlink() or path.resolve().parent != (ROOT / 'device/s6/prebuilts/installer-a74').resolve() or entry['sha256'] != digest or entry['bytes'] != size:
            raise ValueError('unreviewed support identity/path')
        raw = path.read_bytes()
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('support contents changed: ' + name)
        payloads[name] = raw; rows.append(f'{name}\t{size}\t{digest}')
    fragment = (ROOT / 'installer/libupgrade-a71.sh').read_text()
    if transport.sha_file(ROOT / 'installer/libupgrade-a71.sh') != '498d72fd8b751d3e7696ee5daba7bca30b5a8c579b9e8a2cfaf737dcfdf5c35d':
        raise ValueError('frozen A71 transaction base changed')
    fragment = replace_once(fragment, '# A71 format 2.', '# A74 format 3, derived from frozen A71 format 2.')
    fragment = replace_once(fragment, "A71_OPERATION_BANNER='Galaxy Tab S6 One UI 8.5 A71 experimental upgrade (X710 donor)'", "A71_OPERATION_BANNER='Galaxy Tab S6 One UI 8.5 A74 experimental upgrade (X710 donor)'")
    fragment = replace_once(fragment, 'chmod 0700 "$WORK/vendor-guard" "$WORK/mainline-guard"',
                            'chmod 0700 "$WORK/vendor-guard-sdk28" "$WORK/vendor-guard-sdk30" "$WORK/vendor-config-recovery-guard" "$WORK/mainline-guard"')
    fragment = replace_once(fragment, 'check_equal \'Audited A70 experimental SYSTEM\' "$installed_sha" "$A71_SOURCE_A70_SHA"',
                            'case "$installed_sha" in "$A71_SOURCE_A70_SHA"|"' + CURRENT_A71 + '") ;; *) abort \'Installed experimental SYSTEM is not a reviewed A70/A71 source\' ;; esac')
    fragment = replace_once(fragment, 'Exact audited A70 source verified; installing both complete partitions.',
                            'Exact audited A70/A71 source verified; installing both complete partitions.')
    fragment = replace_once(fragment, "check_equal 'Package format' \"$(config format)\" 2", "check_equal 'Package format' \"$(config format)\" 3")
    fragment = replace_once(fragment, 'A71_ONE_S6_CODEC2_POLICY', 'A74_TWO_S6_CONFIGS')
    fragment = replace_once(fragment, 'A71_PREFLIGHT_PASS:', 'A74_PREFLIGHT_PASS:')
    fragment = replace_once(fragment, 'SYSTEM/PRODUCT and complete adapted S6 VENDOR verified.',
                            'SYSTEM/PRODUCT and complete two-config S6 VENDOR verified.')
    snapshot, experimental = old['audited_source_snapshot'], old['audited_experimental_source']
    for marker, value in {'@@SOURCE_SYSTEM_SHA@@': old['source_system_raw_sha256'],
                          '@@SOURCE_A46_SHA@@': snapshot['system_sha256'], '@@SOURCE_A70_SHA@@': experimental['system_sha256'],
                          '@@SUPPORT_ROWS@@': '\n'.join(rows)}.items():
        fragment = replace_once(fragment, marker, value)
    if '@@' in fragment:
        raise ValueError('unresolved transaction marker')
    if operation == 'restore-a70':
        fragment = replace_once(fragment, '\nupgrade_main() {', '\na71_upgrade_transaction() {')
        restore = (ROOT / 'installer/librestore-a70.sh').read_text()
        restore = 'VENDOR_OPERATION=restore-a70\nVENDOR_TARGET_STATE=SDK28_ADAPTED\n' + restore
        for part in ('system', 'product'):
            restore = replace_once(restore, '@@RESTORE_' + part.upper() + '_SHA@@', experimental[part + '_sha256'])
        fragment += '\n' + restore
    library = (ROOT / 'installer/libupgrade.sh').read_bytes() + b'\n' + (ROOT / 'installer/libvendor-a74.sh').read_bytes() + b'\n' + fragment.encode()
    return library, payloads, profile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--operation', choices=['upgrade', 'restore-a70'], default='upgrade')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('fresh render output required')
    manifest = {'candidate_id': CANDIDATE, 'source_inventory_sha256': STAGE, 'support_stage_reference_sha256': STAGE}
    library, support, profile = a74_support(manifest, a.operation)
    a.out.mkdir(parents=True, mode=0o700)
    (a.out / 'libupgrade.sh').write_bytes(library)
    for name, raw in support.items():
        (a.out / name).write_bytes(raw)
    result = {'schema': 1, 'operation': a.operation, 'library_sha256': hashlib.sha256(library).hexdigest(),
              'support_names': sorted(support), 'profile': profile['id'], 'device_writes': False,
              'whole_zip_runtime': 'NOT_TESTED', 'builder_sha256': transport.sha_file(Path(__file__))}
    (a.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
