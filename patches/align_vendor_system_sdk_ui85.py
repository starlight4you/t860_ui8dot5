#!/usr/bin/env python3
"""Build the evidenced S6 vendor SDK30 matrix candidate, without firmware writes."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform(raw, spec):
    if sha(raw) == spec['target_sha256']:
        return raw, False
    if sha(raw) != spec['source_sha256'] or len(raw) != spec['bytes']:
        raise ValueError('unreviewed S6 device matrix input')
    before = ET.fromstring(raw)
    if before.attrib != {'version': '2.0', 'type': 'device'} or len(before.findall('hal')) != spec['hal_count'] or before.findtext('vendor-ndk/version') != str(spec['vendor_ndk']):
        raise ValueError('original S6 HAL/VNDK scope differs')
    sdk = before.findall('system-sdk')
    if len(sdk) != 1 or [v.text for v in sdk[0]] != [str(spec['source_system_sdk'])]:
        raise ValueError('unique original Java requirement differs')
    source = b'<system-sdk>\n        <version>28</version>'
    target = b'<system-sdk>\n        <version>30</version>'
    if spec['source_system_sdk'] != 28 or spec['target_system_sdk'] != 30 or raw.count(source) != 1:
        raise ValueError('reviewed API30 contract transform only')
    result = raw.replace(source, target)
    if sha(result) != spec['target_sha256'] or len(result) != len(raw):
        raise ValueError('candidate bytes differ from reviewed exact transform')
    after = ET.fromstring(result)
    if [v.text for v in after.findall('system-sdk/version')] != ['30']:
        raise ValueError('candidate does not retain explicit Java contract')
    left, right = copy.deepcopy(before), copy.deepcopy(after)
    left.remove(left.find('system-sdk')); right.remove(right.find('system-sdk'))
    if ET.tostring(left) != ET.tostring(right):
        raise ValueError('non-SDK HAL/VNDK/device requirement changed')
    return result, True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', type=Path, required=True)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('fresh host candidate output required')
    spec = json.loads(a.profile.read_text())
    if spec['id'] != 'A74-VENDOR-SYSTEM-SDK30' or spec['file'] != 'etc/vintf/compatibility_matrix.xml':
        raise ValueError('reviewed SDK30 profile required')
    for relative, pin in spec['evidence'].items():
        if sha((ROOT / relative).read_bytes()) != pin:
            raise ValueError('device contract evidence changed')
    contract = json.loads((ROOT / 'docs/audit/vendor-system-sdk30-contract-ui85-a74.json').read_text())
    metadata = json.loads((ROOT / 'docs/audit/vendor-sdk30-compiler-metadata-ui85-a74.json').read_text())
    live = json.loads((ROOT / 'docs/audit/live-vendor-sdk30-definitions-ui85-a74.json').read_text())
    if contract['platform_member_references'] != 154 or contract['missing_members'] or contract['shape_or_visibility_differences'] or metadata['sdk30_non_metadata_type_gaps'] or len(live['platform_member_results']) != 154 or not live['live_inputs_core_boot_unchanged']:
        raise ValueError('fixed consumer contract basis missing')
    raw = a.original.read_bytes()
    result, changed = transform(raw, spec)
    a.out.mkdir(parents=True, mode=0o700)
    (a.out / 'compatibility_matrix.xml').write_bytes(result)
    offsets = [i for i, (old, new) in enumerate(zip(raw, result)) if old != new]
    report = {'schema': 1, 'status': 'FIXED_VENDOR_SDK30_MATRIX_CANDIDATE_BUILT',
              'profile_sha256': sha(a.profile.read_bytes()), 'patcher_sha256': sha(Path(__file__).read_bytes()),
              'source_sha256': sha(raw), 'candidate_sha256': sha(result), 'bytes': len(result),
              'changed': changed, 'changed_byte_offsets': offsets,
              'all_non_sdk_xml_requirements_identical': True, 'system_sdk_requirement_retained': 30,
              'evidence_pins': spec['evidence'], 'source_hardware_files_modified': False,
              'device_partitions_modified': False, 'installed': False, 'full_vintf': 'NOT_PASSED'}
    (a.out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
