#!/usr/bin/env python3
"""Prepare narrow NetworkStack bpffs permissions in the original new donor CIL."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INPUT_SHA = 'f208e23c6c58c037ba22ee171e8b3a3c8a48a7078cdcb5e4993e67a617f2c188'
OUTPUT_SHA = 'ebce484182f38f70dbc1269ad9ba24b8c78c94dba1b55c955f574f5c8b712138'
BOOT_SHA = '523664a8caf6b403526efa6e3b77e8645cc6f84a7573ff7e39159fa9b36843e9'
ALLOW = '(allow network_stack fs_bpf (file (read write getattr)))'
METADATA = {'uid': 0, 'gid': 0, 'mode': '0644', 'selinux': 'u:object_r:sepolicy_file:s0'}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(raw: bytes, profile: dict, device_cil: bytes) -> bytes:
    if (profile['id'] != 'B06-NETWORK-STACK-POLICY' or profile['donor_build'] != 'X710XXS6EZH3'
            or profile['hardware_boot_sha256'] != BOOT_SHA or profile['input_sha256'] != INPUT_SHA
            or len(raw) != 3011800 or profile['input_size'] != len(raw) or sha(raw) != INPUT_SHA):
        raise ValueError('requires the original reviewed donor CIL/hardware profile')
    if (profile['output_sha256'] != OUTPUT_SHA or profile['output_size'] != 3011871
            or profile['path'] != 'system/etc/selinux/plat_sepolicy.cil'
            or profile['install_metadata'] != METADATA or profile['added_allow'] != ALLOW
            or profile['device_cil'] != 'device/s6/sepolicy/network-stack-bpf.cil'
            or device_cil != (ALLOW + '\n').encode()):
        raise ValueError('unreviewed output or extra device permissions')
    text = raw.decode('ascii')
    # Locate from the rule's target/class/permissions, not the old donor's number.
    matches = re.findall(r'^\(neverallow (\w+) fs_bpf \(file \(read getattr\)\)\)$', text, re.M)
    if matches != ['base_typeattr_323'] or profile['source_attribute'] != matches[0]:
        raise ValueError('generic bpffs security assertion changed')
    generic_rule = f'(neverallow {matches[0]} fs_bpf (file (read getattr)))'
    if profile['generic_neverallow'] != generic_rule:
        raise ValueError('profile no longer identifies the generic assertion')
    before = f'(typeattributeset {matches[0]} (and (domain ) (not (bpfloader gpuservice lmkd netd netutils_wrapper system_server mediaprovider_app ))))'
    after = before.replace('netutils_wrapper system_server', 'netutils_wrapper network_stack system_server')
    if (profile['original_attribute'] != before or profile['replacement_attribute'] != after
            or text.count(before) != 1 or text.count(after) or ALLOW in text
            or text.count('(allow bpfdomain fs_bpf (dir (search)))') != 1
            or text.count('(allow network_stack fs_bpf_net_shared (file (read write getattr)))') != 1):
        raise ValueError('reviewed exception/domain/permission anchors differ')
    if len(re.findall(r'\b' + matches[0] + r'\b', text)) != 3:
        raise ValueError('generic assertion attribute has additional consumers')
    candidate = text.replace(before, after).encode() + device_cil
    if len(candidate) != 3011871 or sha(candidate) != OUTPUT_SHA:
        raise ValueError('unexpected donor CIL changes')
    # Keep every neverallow declaration, all original allow declarations and order.
    old_rules = re.findall(r'^\((?:neverallow|allow) .*$', text, re.M)
    new_rules = re.findall(r'^\((?:neverallow|allow) .*$', candidate.decode(), re.M)
    if new_rules != old_rules + [ALLOW]:
        raise ValueError('changed unrelated security rules')
    return candidate


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--policy', type=Path, required=True)
    p.add_argument('--boot', type=Path, required=True)
    p.add_argument('--profile', type=Path, default=ROOT / 'device/s6/network-stack-bpf-ui85.json')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out, base = a.out.resolve(), (ROOT / 'out/patch-probes').resolve()
    if out == base or not out.is_relative_to(base) or a.out.exists():
        raise ValueError('requires fresh isolated out/patch-probes output')
    if sha(a.boot.read_bytes()) != BOOT_SHA:
        raise ValueError('requires the retained reviewed BOOT')
    profile_raw = a.profile.read_bytes()
    profile = json.loads(profile_raw)
    evidence_raw = (ROOT / 'docs/audit/bpf-preserved-kernel-bpffs-labels-ui85.json').read_bytes()
    evidence = json.loads(evidence_raw)
    if (sha(evidence_raw) != profile['kernel_label_audit_sha256']
            or evidence['inputs']['boot'] != BOOT_SHA or evidence['bpf_whitelist_match'] is not False):
        raise ValueError('kernel label evidence differs')
    device_cil = (ROOT / 'device/s6/sepolicy/network-stack-bpf.cil').read_bytes()
    original = a.policy.read_bytes()
    candidate = prepare(original, profile, device_cil)
    a.out.mkdir(parents=True)
    target = a.out / profile['path']
    target.parent.mkdir(parents=True)
    target.write_bytes(candidate)
    report = {'schema': 1, 'id': profile['id'], 'status': 'PREPARED_NOT_APPLIED_NOT_RUNTIME_TESTED',
              'input_sha256': sha(original), 'output_sha256': sha(candidate),
              'profile_sha256': sha(profile_raw), 'script_sha256': sha(Path(__file__).read_bytes()),
              'device_cil_sha256': sha(device_cil), 'added_bytes': len(candidate) - len(original),
              'source_attribute': profile['source_attribute'], 'added_allow': ALLOW,
              'neverallow_declarations': 'ALL_UNCHANGED', 'changed_exception_domains': ['network_stack'],
              'reason_document': profile['reason_document'], 'rom_modified': False,
              'device_modified': False, 'runtime': 'NOT_TESTED', 'release_approved': False}
    rp = a.out / 'patch-report.json'
    rp.write_text(json.dumps(report, indent=2) + '\n')
    manifest = {'schema': 1, 'kind': 'compatibility_probe', 'id': profile['id'],
                'hardware_boot_sha256': BOOT_SHA,
                'files': [{'path': profile['path'], 'sha256': sha(candidate), 'size': len(candidate),
                           'desired_metadata': METADATA}], 'profile_sha256': sha(profile_raw),
                'patch_report_sha256': sha(rp.read_bytes()), 'runtime': 'NOT_TESTED',
                'install_metadata': 'NOT_APPLIED_OR_READ_BACK', 'flashable': False}
    (a.out / 'probe-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'added_bytes': 71, 'output_sha256': OUTPUT_SHA, 'flashable': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
