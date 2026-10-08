#!/usr/bin/env python3
"""Prepare a bounded S9 HIDL-only Null extension; no staging/device writes.

No old binary/code-cave, appended segment or unwind alteration. This backend
candidate does not yet route the FP root window into output mask dispatch.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import capstone

from elf_aarch64 import Elf, branch_target, adrp_page

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'device/s6/fingerprint-hidl-ui85.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(e, va, size):
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    return [(i.address, i.mnemonic, i.op_str) for i in md.disasm(e.at(va, size), va)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out = a.out.resolve()
    if a.out.exists() or not a.out.is_relative_to(ROOT / 'out/patch-probes'):
        raise ValueError('fresh scoped output required')
    c = json.loads(PROFILE.read_text())
    if c['object_size'] != 536 or c['install_to_stage'] or c['fingerprint_dispatch'] != 'NOT_IMPLEMENTED':
        raise ValueError('candidate scope differs')
    raw = (ROOT / c['input']).read_bytes()
    if sha(raw) != c['input_sha256'] or len(raw) != c['input_size']:
        raise ValueError('not current B05 S9 input')
    e = Elf(raw)
    for f in c['functions']:
        if e.function(f['va']) != f:
            raise ValueError('reviewed function differs')
    if e.relative_pointer(0x8f9f80) + 16 != c['null_address_point'] or e.relative_pointer(0x8f9fe0) + 16 != c['real_address_point']:
        raise ValueError('constructor/vtable relocation changed')
    # Restrict the manifest to the actually reviewed instruction and RELR slots.
    if [(x['va'], len(bytes.fromhex(x['after_hex']))) for x in c['code_changes']] != [
        (0x568e0c, 4), (0x568e14, 24), (0x56b200, 4),
        (0x56b550, 4), (0x56b8bc, 4), (0x56bab4, 4),
    ] or [x['slot'] for x in c['relative_pointer_changes']] != [0, 8, 0x10, 0x18, 0x130]:
        raise ValueError('patch scope changed')
    patched = bytearray(raw)
    allowed = set()
    for x in c['code_changes']:
        before, after = bytes.fromhex(x['before_hex']), bytes.fromhex(x['after_hex'])
        if len(before) != len(after) or e.at(x['va'], len(before)) != before:
            raise ValueError('instruction anchor changed')
        off = e.offset(x['va'], len(before))
        patched[off:off + len(after)] = after
        allowed.update(range(off, off + len(after)))
    for x in c['relative_pointer_changes']:
        if e.relative_pointer(x['va']) != x['before'] or e.relative_pointer(x['source_va']) != x['after']:
            raise ValueError('vtable target differs')
        # A RELR location has its addend in-file. Do not overwrite packed RELA.
        if x['va'] not in e._relr_locations or x['source_va'] not in e._relr_locations:
            raise ValueError('vtable is not a reviewed RELR addend')
        off = e.offset(x['va'], 8)
        if struct.unpack_from('<Q', raw, off)[0] != x['before']:
            raise ValueError('in-file RELR addend differs')
        struct.pack_into('<Q', patched, off, x['after'])
        allowed.update(range(off, off + 8))
    result = bytes(patched)
    changed = [i for i, (x, y) in enumerate(zip(raw, result)) if x != y]
    if len(result) != len(raw) or not changed or not set(changed) <= allowed:
        raise ValueError('unexpected firmware difference')
    after = Elf(result)
    # Independently resolve new instructions and relocations, not just byte hashes.
    if adrp_page(after.word(0x568e1c), 0x568e1c) != (8, 0x8c8000):
        raise ValueError('new Null address page differs')
    expected = {
        0x568e0c: ('mov', 'w0, #0x218'), 0x568e14: ('mov', 'x20, x0'),
        0x568e18: ('bl', '#0x56afe0'), 0x568e20: ('add', 'x8, x8, #0x770'),
        0x568e24: ('str', 'x8, [x20]'), 0x568e28: ('b', '#0x568ddc'),
    }
    for va, instruction in expected.items():
        if decode(after, va, 4)[0][1:] != instruction:
            raise ValueError('decoded candidate instruction differs')
    for va, target in [(0x56b200, 0x56b3bc), (0x56b550, 0x56b85c),
                       (0x56b8bc, 0x56b904), (0x56bab4, 0x56b904)]:
        if after.word(va) & 0xfc000000 != 0x14000000 or branch_target(after.word(va), va) != target:
            raise ValueError('new branch is not the reviewed unconditional path')
    for x in c['relative_pointer_changes']:
        if after.relative_pointer(x['va']) != x['after']:
            raise ValueError('candidate relocation does not resolve')
    # ELF headers, unwind/BTI/PAC infrastructure and every unrelated section retain
    # exact bytes. Only the reviewed .text and .data.rel.ro ranges can differ.
    sections_unchanged = []
    for s in e.sections:
        if s.kind == 8 or not s.size or s.name in ('.text', '.data.rel.ro'):
            continue
        if raw[s.offset:s.offset + s.size] != result[s.offset:s.offset + s.size]:
            raise ValueError('unrelated ELF section changed: ' + s.name)
        sections_unchanged.append(s.name)
    a.out.mkdir(parents=True)
    target = a.out / c['metadata']['path']
    target.parent.mkdir(parents=True)
    target.write_bytes(result)
    target.chmod(0o755)
    lines = []
    for f in c['functions']:
        for label, elf in [('before', e), ('after', after)]:
            lines.append(f'{label} function 0x{f["va"]:x}\n')
            lines.extend(f'{va:x}: {mnemonic} {operands}\n' for va, mnemonic, operands in
                         decode(elf, f['va'], f['size']))
    listing = a.out / 'functions.txt'
    listing.write_text(''.join(lines))
    report = {'schema': 1, 'kind': 'compatibility_probe', 'component': 'F04_HIDL_MASK_BACKEND',
              'device': c['device'], 'input_sha256': sha(raw), 'output_sha256': sha(result),
              'profile_sha256': sha(PROFILE.read_bytes()), 'script_sha256': sha(Path(__file__).read_bytes()),
              'elf_helper_sha256': sha((ROOT / 'patches/elf_aarch64.py').read_bytes()),
              'changed_bytes': len(changed), 'allowed_bytes': len(allowed),
              'changes': c['code_changes'], 'vtable_changes': c['relative_pointer_changes'],
              'unchanged_sections': sections_unchanged, 'function_listing_sha256': sha(listing.read_bytes()),
              'metadata_required': c['metadata'], 'actual_image_metadata': 'NOT_APPLIED',
              'new_rom_runtime': 'NOT_TESTED', 'fp_window_dispatch': 'NOT_IMPLEMENTED',
              'stage_modified': False, 'device_writes': False, 'flashable': False,
              'limits': ['Existing new S9 constructor/HIDL client/mask bridge only.',
                         'Physical ET713, linker/CFI/SELinux and failure/lifecycle paths still need runtime verification.',
                         'Shared real init/post-init bodies are specialized for the T860 Null profile; no all-QTI mode certification.']}
    (a.out / 'patch-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'changed_bytes': len(changed), 'backend_candidate': str(target), 'flashable': False}))


if __name__ == '__main__':
    main()
