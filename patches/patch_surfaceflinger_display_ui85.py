#!/usr/bin/env python3
"""Prepare the new-donor T860 Null-extension gate; never edit a donor tree."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_surfaceflinger_display_ui85 import selector


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(original: bytes, contract: dict, *, require_output_pin: bool = True) -> tuple[bytes, dict]:
    if len(original) != contract['input_bytes'] or sha(original) != contract['input_sha256']:
        raise ValueError('requires exact unchanged X710 SurfaceFlinger')
    if (contract['old_threshold'], contract['new_threshold']) != (34, 28):
        raise ValueError('unreviewed threshold change')
    inspected = selector(original, 34)
    if inspected['function'] != contract['function'] or inspected['comparison_va'] != contract['comparison_va']:
        raise ValueError('new donor selector function/semantic anchor differs')
    offset = inspected['comparison_file_offset']
    if offset != contract['comparison_file_offset'] or inspected['comparison_word'] != contract['original_word']:
        raise ValueError('comparison instruction anchor differs')
    output = bytearray(original)
    struct.pack_into('<I', output, offset, 0x7100729f)
    changed = [i for i, pair in enumerate(zip(original, output)) if pair[0] != pair[1]]
    if changed != [offset + 1] or len(original) != len(output):
        raise ValueError('unexpected ELF changes')
    after = selector(bytes(output), 28)
    if after['comparison_va'] != inspected['comparison_va'] or after['other_api_consumers'] != inspected['other_api_consumers']:
        raise ValueError('output selector/neighbor validation differs')
    if require_output_pin and sha(output) != contract['output_sha256']:
        raise ValueError('output differs from independently decoded candidate')
    return bytes(output), {'id': contract['id'], 'status': 'PREPARED_NOT_APPLIED_NOT_RUNTIME_TESTED',
                           'input_sha256': sha(original), 'output_sha256': sha(output),
                           'comparison_va': inspected['comparison_va'], 'comparison_file_offset': offset,
                           'before_word': contract['original_word'], 'after_word': '0x7100729f',
                           'before_function_sha256': inspected['function']['sha256'],
                           'after_function_sha256': after['function']['sha256'],
                           'changed_byte_count': 1, 'all_other_elf_bytes_identical': True,
                           'requires_paired_init': contract['init']['path'], 'runtime': 'NOT_TESTED'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='new probe directory')
    args = parser.parse_args()
    if args.output.exists() or not args.output.resolve().is_relative_to(ROOT / 'out/patch-probes'):
        raise ValueError('requires new directory under out/patch-probes; never a donor/staging tree')
    contract_path = ROOT / 'device/s6/surfaceflinger-ui85.json'
    contract = json.loads(contract_path.read_text())
    binary, report = prepare(args.input.read_bytes(), contract)
    init_path = ROOT / contract['init']['source']
    init = init_path.read_bytes()
    if sha(init) != contract['init']['sha256']:
        raise ValueError('paired init source hash differs')
    args.output.mkdir(parents=True)
    files = []
    for relative, raw, metadata in ((contract['path'], binary, contract),
                                    (contract['init']['path'], init, contract['init'])):
        path = args.output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        files.append({'path': relative, 'sha256': sha(raw), 'size': len(raw),
                      'image_metadata_required': {key: metadata[key] for key in ('owner', 'group', 'mode', 'selinux')}})
    report.update({'contract_sha256': sha(contract_path.read_bytes()), 'patcher_sha256': sha(Path(__file__).read_bytes()),
                   'elf_helper_sha256': sha((ROOT / 'patches/elf_aarch64.py').read_bytes()),
                   'selector_reader_sha256': sha((ROOT / 'scripts/audit_surfaceflinger_display_ui85.py').read_bytes())})
    (args.output / 'patch-report.json').write_text(json.dumps(report, indent=2) + '\n')
    manifest = {'schema': 1, 'kind': 'compatibility_probe', 'status': report['status'],
                'donor_build': contract['donor_build'], 'files': files, 'report': report,
                'runtime': 'NOT_TESTED', 'limitations': 'Selector and paired property init only; not a complete display or ROM adaptation.'}
    (args.output / 'probe-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
