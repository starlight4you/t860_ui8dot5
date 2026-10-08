#!/usr/bin/env python3
"""Reimplement the new donor's process-free context/attach pair for fixed S6 BOOT."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'patches'))
sys.path.insert(0, str(ROOT / 'scripts'))
from elf_aarch64 import Elf
from audit_platform_bpf_ui85 import Object, Btf

OBJECT_SHA = '78b9006398a3f52d7ecca3509b7b0015d98575ebe0f6075212edd06e9d1aca28'
LIBRARY_SHA = '76bc0c26bef19856990b5b345a117c50687516b0c725270718355943121cb20c'
BOOT_SHA = '523664a8caf6b403526efa6e3b77e8645cc6f84a7573ff7e39159fa9b36843e9'
FORMAT_SHA = 'cdda6388a380831302eecc2dad8729116a9a13c20d61844cd177c41015feb61b'
OLD_SECTION = 'raw_tp/sched_process_free'
NEW_SECTION = 'tracepoint/sched/sched_process_free'


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def bpf_instruction(code: int, registers: int = 0, offset: int = 0, immediate: int = 0) -> bytes:
    return struct.pack('<BBhi', code, registers, offset, immediate)


def prepare_object(raw: bytes) -> tuple[bytes, dict]:
    if sha(raw) != OBJECT_SHA:
        raise ValueError('requires original reviewed S9 BPF object')
    obj = Object(raw)
    program = obj.named[OLD_SECTION]
    if program['size'] != 1216 or program['offset'] != 7392:
        raise ValueError('original process-free section differs')
    code = obj.data(program)
    prefix = b''.join([
        bpf_instruction(0xb7, 2, 0, 0), bpf_instruction(0x79, 0x13),
        bpf_instruction(0x0f, 0x23), bpf_instruction(0xbf, 0xa1),
        bpf_instruction(0x07, 1, 0, -8), bpf_instruction(0xb7, 2, 0, 4),
        bpf_instruction(0x85, 0, 0, 113),
    ])
    if code[:56] != prefix:
        raise ValueError('raw-context/helper prefix differs')
    # No existing branch may enter an overwritten instruction.
    for offset in range(56, len(code), 8):
        opcode, _, relative, _ = struct.unpack_from('<BBhi', code, offset)
        if opcode & 7 in (5, 6) and opcode & 0xf0 not in (0x80, 0x90):
            if offset + 8 + relative * 8 < 56:
                raise ValueError('body jumps into replaced prefix')
    bridge = (bpf_instruction(0x61, 0x16, 24) + bpf_instruction(0x63, 0x6a, -8) +
              bpf_instruction(0x05) * 5)

    btf_raw = obj.data(obj.named['.BTF'])
    magic, version, flags, header, type_off, type_len, string_off, string_len = struct.unpack_from('<HBB5I', btf_raw)
    if (magic, version, flags, header) != (0xeb9f, 1, 0, 24) or header + string_off + string_len != len(btf_raw):
        raise ValueError('BTF layout differs')
    btf = Btf(btf_raw)
    context = btf.types[102]
    if context['name'] != 'bpf_raw_tracepoint_args' or context['kind'] != 4 or context['count'] != 1 or context['value'] != 0:
        raise ValueError('original BTF context differs')
    if btf.sizeof(43) != 4 or btf.strings[515:519] != b'pid\0':
        raise ValueError('BTF PID member/type differs')
    new_section_off = string_len
    new_context_off = string_len + len(NEW_SECTION) + 1
    added_strings = NEW_SECTION.encode() + b'\0s6_sched_process_free_args\0'
    changed_btf = bytearray(btf_raw + added_strings)
    struct.pack_into('<I', changed_btf, 20, string_len + len(added_strings))
    context_off = header + type_off + sum(12 + len(t['extra']) for t in btf.types[1:102])
    # Keep type IDs and record size; implicit padding up to pid at byte24.
    struct.pack_into('<6I', changed_btf, context_off, new_context_off, 0x04000001, 32, 515, 43, 192)

    ext = obj.data(obj.named['.BTF.ext'])
    ext_header = struct.unpack_from('<HBB7I', ext)
    if ext_header != (0xeb9f, 1, 0, 32, 0, 52, 52, 5308, 5360, 28):
        raise ValueError('BTF.ext layout differs')
    old_section_off = btf.strings.find(OLD_SECTION.encode() + b'\0')
    if old_section_off != 5260:
        raise ValueError('BTF section string differs')
    core = ext[32 + 5360:]
    if core != struct.pack('<7I', 16, 5260, 1, 0, 107, 5298, 0) or btf.strings[5298:5302] != b'0:0\0':
        raise ValueError('unique raw task.pid CO-RE relocation differs')

    removed_lines = []

    def ext_records(start: int, size: int, line_info: bool) -> bytes:
        block = ext[32 + start:32 + start + size]
        stride = struct.unpack_from('<I', block)[0]
        if stride != (16 if line_info else 8):
            raise ValueError('BTF.ext record stride differs')
        result = bytearray(block[:4])
        position = 4
        while position < len(block):
            section_off, count = struct.unpack_from('<II', block, position)
            position += 8
            records = []
            for _ in range(count):
                record = block[position:position + stride]
                if len(record) != stride:
                    raise ValueError('truncated BTF.ext records')
                instruction_off = struct.unpack_from('<I', record)[0]
                if line_info and section_off == old_section_off and instruction_off < 56:
                    removed_lines.append(instruction_off)
                else:
                    records.append(record)
                position += stride
            result += struct.pack('<II', new_section_off if section_off == old_section_off else section_off, len(records))
            result += b''.join(records)
        if position != len(block):
            raise ValueError('BTF.ext block bounds differ')
        return bytes(result)

    functions = ext_records(0, 52, False)
    lines = ext_records(52, 5308, True)
    changed_ext = (struct.pack('<HBB7I', 0xeb9f, 1, 0, 32, 0, len(functions), len(functions),
                               len(lines), len(functions) + len(lines), 0) + functions + lines)
    strings = obj.data(obj.named['.strtab'])
    new_program_name_off = len(strings)
    new_relocation_name_off = len(strings) + len(NEW_SECTION) + 1
    changed_strings = strings + NEW_SECTION.encode() + b'\0.rel' + NEW_SECTION.encode() + b'\0'
    output = bytearray(raw)
    output[program['offset']:program['offset'] + 56] = bridge
    shoff = struct.unpack_from('<Q', raw, 40)[0]
    new_locations = {}
    for name, data in [('.strtab', changed_strings), ('.BTF', changed_btf), ('.BTF.ext', changed_ext)]:
        section = obj.named[name]
        section_header = shoff + section['index'] * 64
        alignment = struct.unpack_from('<Q', raw, section_header + 48)[0]
        if alignment not in (1, 4, 8):
            raise ValueError('unexpected table alignment')
        output += b'\0' * (-len(output) % alignment)
        location = len(output)
        output += data
        struct.pack_into('<QQ', output, section_header + 24, location, len(data))
        new_locations[name] = {'offset': location, 'size': len(data)}
    struct.pack_into('<I', output, shoff + program['index'] * 64, new_program_name_off)
    rel = obj.named['.rel' + OLD_SECTION]
    struct.pack_into('<I', output, shoff + rel['index'] * 64, new_relocation_name_off)
    verified = Object(bytes(output))
    new_btf = Btf(verified.data(verified.named['.BTF']))
    if len(new_btf.types) != len(btf.types) or verified.data(verified.named[NEW_SECTION])[56:] != code[56:]:
        raise ValueError('context reconstruction changed body/type IDs')
    return bytes(output), {'original_prefix': prefix.hex(), 'replacement_prefix': bridge.hex(),
                           'body_offset': 56, 'body_sha256': sha(code[56:]),
                           'tables': new_locations, 'removed_line_info_offsets': removed_lines,
                           'removed_core_relocations': 1, 'btf_context_type_id': 102}


def prepare_library(raw: bytes) -> bytes:
    if sha(raw) != LIBRARY_SHA:
        raise ValueError('requires original reviewed S9 library')
    elf = Elf(raw)
    if elf.at(0x3d44, 4) != bytes.fromhex('ed040094'):
        raise ValueError('original raw attach call differs')
    for va, size, digest in [
        (0x5094, 100, '87fb913ea6ac35a202f3a4bb48381d2842dff0641f00fa038f4733e625db7a85'),
        (0x50f8, 80, 'ca5a90795b08185e90d1032bcd8b77b1eb2e46187cee1b6ff5202b26cc4b7294'),
    ]:
        fn = elf.function(va)
        if fn['va'] != va or fn['size'] != size or fn['sha256'] != digest:
            raise ValueError('paired attach helper differs')
    if elf.plt_import(0xaec0) != 'bpf_attach_tracepoint' or elf.plt_import(0xaed8) != 'bpf_attach_raw_tracepoint':
        raise ValueError('attach helper imports differ')
    output = bytearray(raw)
    output[elf.offset(0x3d44, 4):elf.offset(0x3d44, 4) + 4] = bytes.fromhex('d4040094')
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object', required=True, type=Path)
    parser.add_argument('--library', required=True, type=Path)
    parser.add_argument('--boot', required=True, type=Path)
    parser.add_argument('--format', required=True, type=Path)
    parser.add_argument('--profile', type=Path, default=ROOT / 'device/s6/bpf-cpu-ui85.json')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to((ROOT / 'out/patch-probes').resolve()) or out.exists():
        raise ValueError('requires fresh workspace compatibility probe directory')
    if sha(args.boot.read_bytes()) != BOOT_SHA or sha(args.format.read_bytes()) != FORMAT_SHA:
        raise ValueError('preserved BOOT/live event format differs')
    profile = json.loads(args.profile.read_text())
    if profile['boot_sha256'] != BOOT_SHA or profile['event_format_sha256'] != FORMAT_SHA:
        raise ValueError('profile baseline differs')
    if profile['event'] != {'name': 'sched/sched_process_free', 'pid_offset': 24, 'pid_bytes': 4,
                            'context_bytes': 32, 'hardcoded_event_id': False}:
        raise ValueError('profile event ABI differs')
    if profile['native'] != {'caller_va': '0x3710', 'caller_size': 2164,
                            'caller_sha256': 'fb5d18cfe2112e312ac08c0c9791a625d2f1d39acce423780a19efb054e2857c',
                            'call_va': '0x3d44', 'old_target': '0x50f8', 'new_target': '0x5094',
                            'old_instruction': 'ed040094', 'new_instruction': 'd4040094'}:
        raise ValueError('profile attach contract differs')
    for path, digest, label in [
        ('system/etc/bpf/cputimeinstate/timeInState.bpf', OBJECT_SHA, 'u:object_r:system_file:s0'),
        ('system/lib64/libtimeinstate.so', LIBRARY_SHA, 'u:object_r:system_lib_file:s0'),
    ]:
        item = profile['files'][path]
        if item['input_sha256'] != digest or [item[k] for k in ('uid', 'gid', 'mode', 'selinux')] != [0, 0, '0644', label]:
            raise ValueError('profile source/metadata differs')
    caller = Elf(args.library.read_bytes()).function(0x3710)
    if [caller[k] for k in ('va', 'size', 'sha256')] != [0x3710, 2164, 'fb5d18cfe2112e312ac08c0c9791a625d2f1d39acce423780a19efb054e2857c']:
        raise ValueError('complete attach caller differs')
    object_output, changes = prepare_object(args.object.read_bytes())
    library_output = prepare_library(args.library.read_bytes())
    products = {'system/etc/bpf/cputimeinstate/timeInState.bpf': object_output,
                'system/lib64/libtimeinstate.so': library_output}
    for path, data in products.items():
        if sha(data) != profile['files'][path]['output_sha256']:
            raise ValueError('fixed output hash differs')
    out.mkdir(parents=True)
    for path, data in products.items():
        target = out / 'files' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest = {'schema': 1, 'kind': 'compatibility_probe', 'patch': 'B06-CPU',
                'flashable': False, 'complete_cpu_compatibility': False,
                'files': {path: {**profile['files'][path], 'size': len(data)} for path, data in products.items()},
                'changes': changes, 'boot_sha256': BOOT_SHA, 'event_format_sha256': FORMAT_SHA,
                'profile_sha256': sha(args.profile.read_bytes()), 'patcher_sha256': sha(Path(__file__).read_bytes()),
                'elf_helper_sha256': sha((ROOT / 'patches/elf_aarch64.py').read_bytes()),
                'bpf_reader_sha256': sha((ROOT / 'scripts/audit_platform_bpf_ui85.py').read_bytes()),
                'runtime': 'NOT_TESTED', 'limits': profile['limits']}
    (out / 'probe-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'files': {path: sha(data) for path, data in products.items()},
                      'removed_line_records': len(changes['removed_line_info_offsets']), 'flashable': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
