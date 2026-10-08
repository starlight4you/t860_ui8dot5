#!/usr/bin/env python3
"""Prepare the new JNI's exact ENOTSUPP524 iteration compatibility branch."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from elf_aarch64 import Elf

ROOT = Path(__file__).resolve().parents[1]
REPLACEMENT = bytes.fromhex('df320871c41a427aa0030054880240f9')
ORIGINAL = bytes.fromhex('df0a0071c0030054880240f91f2003d5')
NAME = 'libandroid_net_connectivity_com_android_net_module_util_jni.so'


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(raw: bytes, profile: dict) -> bytes:
    if profile['accepted_errornos'] != [2, 524] or profile['window_va'] != '0x521c' or profile['window_offset'] != 0x521c:
        raise ValueError('unreviewed errno set/window')
    if profile['original_hex'] != ORIGINAL.hex() or profile['replacement_hex'] != REPLACEMENT.hex():
        raise ValueError('unreviewed instruction window')
    if len(raw) != profile['size'] or sha(raw) != profile['input_sha256']:
        raise ValueError('requires unchanged original X710 JNI')
    elf = Elf(raw)
    if elf.function(0x5014) != profile['function'] or elf.at(0x521c, 16) != ORIGINAL:
        raise ValueError('function/context/window pin differs')
    if elf.relative_pointer(0xc008 + 3 * 24 + 16) != 0x5014:
        raise ValueError('JNI registration does not target reviewed function')
    offset = elf.offset(0x521c, 16)
    result = raw[:offset] + REPLACEMENT + raw[offset + 16:]
    if sha(result) != profile['output_sha256']:
        raise ValueError('output pin differs')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jni', type=Path, required=True)
    parser.add_argument('--profile', type=Path, default=ROOT / 'device/s6/bpf-jni-ui85.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base, output = (ROOT / 'out/patch-probes').resolve(), args.out.resolve()
    if output == base or not output.is_relative_to(base) or args.out.exists():
        raise ValueError('requires fresh output in out/patch-probes')
    profile_raw = args.profile.read_bytes()
    profile = json.loads(profile_raw)
    if profile['id'] != 'B06-JNI' or profile['hardware_boot_sha256'] != '523664a8caf6b403526efa6e3b77e8645cc6f84a7573ff7e39159fa9b36843e9' or profile['sdk_full'] != '36.1':
        raise ValueError('unreviewed hardware/platform profile')
    if sha((ROOT / 'patches/bpf-jni-next-key-ui85.S').read_bytes()) != profile['review_source_sha256']:
        raise ValueError('assembly review source changed')
    original = args.jni.read_bytes()
    candidate = prepare(original, profile)
    args.out.mkdir(parents=True)
    path = args.out / 'lib64' / NAME
    path.parent.mkdir()
    path.write_bytes(candidate)
    report = {'schema': 1, 'id': 'B06-JNI', 'status': 'PREPARED_NOT_APPLIED_NOT_RUNTIME_TESTED',
              'profile_sha256': sha(profile_raw), 'input_sha256': sha(original), 'output_sha256': sha(candidate),
              'window_va': '0x521c', 'original_hex': ORIGINAL.hex(), 'replacement_hex': REPLACEMENT.hex(),
              'accepted_errornos': [2, 524], 'instruction_changes': 4,
              'changed_bytes': [i for i, (a, b) in enumerate(zip(original, candidate)) if a != b],
              'script_sha256': sha(Path(__file__).read_bytes()),
              'elf_helper_sha256': sha((ROOT / 'patches/elf_aarch64.py').read_bytes()),
              'assembly_sha256': profile['review_source_sha256'], 'reason_document': profile['reason_document'],
              'complete_network_compatibility': False, 'runtime': 'NOT_TESTED',
              'modifications_to_donor_or_staging': [],
              'limits': 'No syscall/native execution or Java LPM cache consistency validation. Unenumerable maps return no-next-key on524; every other error remains an error. No old JNI copied, code cave or JNI table change.'}
    report_path = args.out / 'patch-report.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    manifest = {'schema': 1, 'kind': 'compatibility_probe', 'id': 'B06-JNI',
                'hardware_boot_sha256': profile['hardware_boot_sha256'], 'sdk_full': '36.1',
                'files': [{'path': 'lib64/' + NAME, 'size': len(candidate), 'sha256': sha(candidate)}],
                'profile_sha256': sha(profile_raw), 'patch_report_sha256': sha(report_path.read_bytes()),
                'complete_network_compatibility': False, 'runtime': 'NOT_TESTED',
                'install_metadata': 'NOT_APPLIED_OR_READ_BACK', 'flashable': False}
    (args.out / 'probe-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'instruction_changes': 4, 'accepted_errornos': [2, 524],
                      'output_sha256': sha(candidate), 'flashable': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
