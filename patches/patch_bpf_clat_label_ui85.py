#!/usr/bin/env python3
"""Prepare the new CLAT expected label for the fixed preserved 4.14 BOOT.

Changes only one constant. All code and failing checks are retained.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from elf_aarch64 import Elf

ROOT = Path(__file__).resolve().parents[1]
BOOT_SHA = '523664a8caf6b403526efa6e3b77e8645cc6f84a7573ff7e39159fa9b36843e9'
INPUT_SHA = 'ab6457a5529a0142cd639e291482e18ade0e7368f1507a0dc49dcc5d25804aee'
OUTPUT_SHA = '245d613605e3abf8531baef93e6314af4e0210b26aa34597e32460fde400a141'
ORIGINAL = b'u:object_r:fs_bpf_net_shared:s0\0'
REPLACEMENT = b'u:object_r:fs_bpf:s0'.ljust(32, b'\0')
METADATA = {'uid': 1000, 'gid': 1000, 'mode': '0644', 'selinux': 'u:object_r:system_lib_file:s0'}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(raw: bytes, profile: dict) -> bytes:
    if profile['id'] != 'B06-CLAT' or profile['sdk_full'] != '36.1' or profile['kernel_version'] != '4.14.190' or profile['hardware_boot_sha256'] != BOOT_SHA:
        raise ValueError('unreviewed hardware/donor profile')
    if len(raw) != 85440 or profile['size'] != len(raw) or sha(raw) != INPUT_SHA or profile['input_sha256'] != INPUT_SHA:
        raise ValueError('requires exact original new CLAT library')
    if profile['output_sha256'] != OUTPUT_SHA or profile['apex_path'] != 'lib64/libservice-connectivity.so' or profile['install_metadata'] != METADATA:
        raise ValueError('unreviewed output path/metadata/digest')
    if profile['window_va'] != '0x2d3f' or profile['window_offset'] != 0x2d3f or profile['window_size'] != 32:
        raise ValueError('unreviewed constant window')
    if profile['original_hex'] != ORIGINAL.hex() or profile['replacement_hex'] != REPLACEMENT.hex() or profile['new_label'] != 'u:object_r:fs_bpf:s0' or profile['old_label'] != 'u:object_r:fs_bpf_net_shared:s0':
        raise ValueError('unreviewed expected-label replacement')
    elf = Elf(raw)
    if [elf.function(va) for va in (0xb0cc, 0xb5f8)] != profile['functions']:
        raise ValueError('complete validation functions differ')
    xrefs = [(0xb17c, 0xb180), (0xb1a4, 0xb1a8)]
    if elf.string_xrefs(0x2d3f) != xrefs or profile['xrefs'] != [[hex(a), hex(b)] for a, b in xrefs]:
        raise ValueError('context references differ')
    section = elf.by_name['.rodata']
    if not section.va <= 0x2d3f < 0x2d3f + 32 <= section.va + section.size or raw.count(ORIGINAL) != 1 or elf.at(0x2d3f, 32) != ORIGINAL:
        raise ValueError('context not uniquely in reviewed read-only data window')
    offset = elf.offset(0x2d3f, 32)
    result = raw[:offset] + REPLACEMENT + raw[offset + 32:]
    if sha(result) != OUTPUT_SHA or Elf(result).at(elf.by_name['.text'].va, elf.by_name['.text'].size) != elf.at(elf.by_name['.text'].va, elf.by_name['.text'].size):
        raise ValueError('unexpected output/code changes')
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library', type=Path, required=True)
    p.add_argument('--boot', type=Path, required=True)
    p.add_argument('--profile', type=Path, default=ROOT / 'device/s6/bpf-clat-label-ui85.json')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    base, output = (ROOT / 'out/patch-probes').resolve(), a.out.resolve()
    if output == base or not output.is_relative_to(base) or a.out.exists():
        raise ValueError('fresh output in out/patch-probes required')
    profile_raw = a.profile.read_bytes()
    profile = json.loads(profile_raw)
    if sha(a.boot.read_bytes()) != BOOT_SHA:
        raise ValueError('not the preserved reviewed BOOT')
    if profile['kernel_label_audit'] != 'docs/audit/bpf-preserved-kernel-bpffs-labels-ui85.json':
        raise ValueError('different kernel label evidence path')
    evidence_raw = (ROOT / profile['kernel_label_audit']).read_bytes()
    evidence = json.loads(evidence_raw)
    if sha(evidence_raw) != profile['kernel_label_audit_sha256'] or evidence['inputs']['boot'] != BOOT_SHA or evidence['bpf_whitelist_match'] is not False or evidence['kernel_modified'] is not False:
        raise ValueError('kernel label evidence differs')
    original = a.library.read_bytes()
    candidate = prepare(original, profile)
    a.out.mkdir(parents=True)
    path = a.out / profile['apex_path']
    path.parent.mkdir()
    path.write_bytes(candidate)
    changed = [i for i, (old, new) in enumerate(zip(original, candidate)) if old != new]
    report = {'schema': 1, 'id': 'B06-CLAT', 'status': 'PREPARED_NOT_APPLIED_NOT_RUNTIME_TESTED',
              'input_sha256': sha(original), 'output_sha256': sha(candidate),
              'profile_sha256': sha(profile_raw), 'changed_bytes': changed,
              'executable_bytes_changed': 0, 'old_label': profile['old_label'], 'new_label': profile['new_label'],
              'retained_checks': ['UID/GID/mode', 'lstat', 'lgetxattr', 'strncmp255', 'OBJ_GET', 'failure flag and abort'],
              'script_sha256': sha(Path(__file__).read_bytes()),
              'elf_helper_sha256': sha((ROOT / 'patches/elf_aarch64.py').read_bytes()),
              'kernel_label_audit_sha256': sha(evidence_raw), 'reason_document': profile['reason_document'],
              'modifications_to_donor_or_staging': [], 'runtime': 'NOT_TESTED',
              'complete_network_compatibility': False, 'limits': profile['limits']}
    rp = a.out / 'patch-report.json'
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    manifest = {'schema': 1, 'kind': 'compatibility_probe', 'id': 'B06-CLAT',
                'hardware_boot_sha256': BOOT_SHA, 'sdk_full': '36.1',
                'files': [{'path': profile['apex_path'], 'sha256': sha(candidate), 'size': len(candidate),
                           'desired_metadata': METADATA}], 'profile_sha256': sha(profile_raw),
                'patch_report_sha256': sha(rp.read_bytes()), 'runtime': 'NOT_TESTED',
                'complete_network_compatibility': False, 'install_metadata': 'NOT_APPLIED_OR_READ_BACK',
                'flashable': False}
    (a.out / 'probe-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'changed_bytes': len(changed), 'executable_bytes_changed': 0,
                      'output_sha256': sha(candidate), 'flashable': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
