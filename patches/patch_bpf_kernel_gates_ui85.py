#!/usr/bin/env python3
"""Prepare partial native BPF gate compatibility for the pinned T860 profile."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from elf_aarch64 import Elf, branch_target

ROOT = Path(__file__).resolve().parents[1]
ALLOW = {'netbpfload': ((0xce14, 0xce3c), (0xce48, 0xce74),
                      (0xce78, 0xcebc), (0x110e8, 0x111f4)),
         'libnetd_updatable.so': ((0x4e48, 0x4e68), (0x4e70, 0x4f28))}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(raw: bytes, record: dict) -> tuple[bytes, dict]:
    if len(raw) != record['size'] or sha(raw) != record['input_sha256']:
        raise ValueError('requires exact unpatched donor input')
    elf = Elf(raw)
    allowed = ALLOW[record['name']]
    if [(int(p['va'], 0), int(p['target_va'], 0)) for p in record['patches']] != list(allowed):
        raise ValueError('unreviewed gate set or continuation')
    for fn in record['functions']:
        if elf.function(fn['va']) != fn:
            raise ValueError('full function/context digest differs')
    output, edits = bytearray(raw), []
    for patch, (va, target) in zip(record['patches'], allowed):
        old, new = int(patch['original_word'], 0), int(patch['replacement_word'], 0)
        offset = elf.offset(va, 4)
        if offset != patch['file_offset'] or elf.word(va) != old:
            raise ValueError('original gate word/offset differs')
        if old & 0xff000010 != 0x54000000 or branch_target(old, va) != target:
            raise ValueError('original continuation no longer matches conditional branch')
        expected = 0x14000000 | (((target - va) // 4) & 0x3ffffff)
        if new != expected:
            raise ValueError('unreviewed replacement instruction')
        struct.pack_into('<I', output, offset, new)
        edits.append({'va': hex(va), 'offset': offset, 'original_word': hex(old),
                      'replacement_word': hex(new), 'existing_target': hex(target)})
    result = bytes(output)
    if sha(result) != record['output_sha256']:
        raise ValueError('prepared output digest differs')
    touched = {i for p in record['patches'] for i in range(p['file_offset'], p['file_offset'] + 4)}
    changes = [i for i, (a, b) in enumerate(zip(raw, result)) if a != b]
    if not set(changes) <= touched:
        raise ValueError('unreviewed byte changes')
    return result, {'name': record['name'], 'input_sha256': sha(raw), 'output_sha256': sha(result),
                    'size': len(raw), 'edits': edits, 'changed_bytes': changes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loader', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--profile', type=Path, default=ROOT / 'device/s6/bpf-gates-ui85.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base = (ROOT / 'out/patch-probes').resolve()
    destination = args.out.resolve()
    if destination == base or not destination.is_relative_to(base) or args.out.exists():
        raise ValueError('requires fresh directory inside out/patch-probes')
    profile_raw = args.profile.read_bytes()
    profile = json.loads(profile_raw)
    if profile['id'] != 'B06-GATES' or profile['sdk_full'] != '36.1' or profile['kernel_version'] != '4.14.190' or profile['hardware_boot_sha256'] != '523664a8caf6b403526efa6e3b77e8645cc6f84a7573ff7e39159fa9b36843e9':
        raise ValueError('unreviewed hardware/platform profile')
    if [f['name'] for f in profile['files']] != list(ALLOW):
        raise ValueError('requires paired reviewed native files')
    inputs = {'netbpfload': args.loader, 'libnetd_updatable.so': args.library}
    prepared = [prepare(inputs[f['name']].read_bytes(), f) for f in profile['files']]
    args.out.mkdir(parents=True)
    reports, manifest_files = [], []
    for spec, (raw, report) in zip(profile['files'], prepared):
        path = args.out / spec['apex_path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        reports.append(report)
        manifest_files.append({'path': spec['apex_path'], 'sha256': sha(raw), 'size': len(raw)})
    report = {'schema': 1, 'id': profile['id'], 'status': 'PREPARED_NOT_APPLIED_NOT_RUNTIME_TESTED',
              'profile_sha256': sha(profile_raw), 'script_sha256': sha(Path(__file__).read_bytes()),
              'elf_helper_sha256': sha((ROOT / 'patches/elf_aarch64.py').read_bytes()), 'files': reports,
              'reason_document': profile['reason_document'], 'complete_network_compatibility': False,
              'limits': 'Partial gate candidate only. Modern loader/maps/JNI/namespace/SELinux and runtime remain unverified. Original U+4.14 requirement, runtime SDK/flags, syscall and map/init failures stay unchanged. No status wrapper.',
              'runtime': 'NOT_TESTED', 'modifications_to_donor_or_staging': []}
    (args.out / 'patch-report.json').write_text(json.dumps(report, indent=2) + '\n')
    manifest = {'schema': 1, 'kind': 'compatibility_probe', 'id': 'B06-GATES',
                'hardware_boot_sha256': profile['hardware_boot_sha256'], 'sdk_full': '36.1',
                'files': manifest_files, 'profile_sha256': sha(profile_raw),
                'patch_report_sha256': sha((args.out / 'patch-report.json').read_bytes()),
                'runtime': 'NOT_TESTED', 'complete_network_compatibility': False,
                'install_metadata': 'NOT_APPLIED_OR_READ_BACK', 'flashable': False}
    (args.out / 'probe-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'prepared': [r['name'] for r in reports], 'instruction_changes': 6,
                      'complete_network_compatibility': False, 'flashable': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
