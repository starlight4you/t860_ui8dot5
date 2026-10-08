#!/usr/bin/env python3
"""Build two pinned S9 FP dispatch trampolines; do not modify the ROM stage."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

from elf_aarch64 import Elf, branch_target

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'device/s6/fingerprint-output-ui85.json'
NDK = Path(os.environ['ANDROID_SDK_ROOT']) / 'ndk/27.3.13750724/toolchains/llvm/prebuilt/darwin-x86_64/bin'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def align(n, multiple):
    return (n + multiple - 1) & -multiple


def uleb(n):
    result = bytearray()
    while True:
        value = n & 127
        n >>= 7
        result.append(value | (128 if n else 0))
        if not n:
            return bytes(result)


def fde(va, start, size, c):
    # Freeze the parent's actual callsite row, including PAC state. The helper
    # never changes SP, FP, saved slots or their contents.
    cfi = bytearray(b'\x2d\x0c' + uleb(c['cfa_register']) + uleb(c['cfa_offset']))
    for reg, offset in sorted(c['saved_register_offsets'].items(), key=lambda x: int(x[0])):
        if not -128 <= offset < 0 or offset % -4 or int(reg) >= 32:
            raise ValueError('unsupported saved-register rule')
        cfi.extend(bytes([0x80 | int(reg)]) + uleb(offset // -4))
    body = struct.pack('<IiI', va + 4 - 1017376, start - (va + 8), size) + b'\0' + cfi
    body += bytes(align(len(body) + 4, 4) - (len(body) + 4))
    return struct.pack('<I', len(body)) + body


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / 'out/patch-probes'):
        raise ValueError('fresh scoped output required')
    c = json.loads(PROFILE.read_text())
    raw = (ROOT / c['input']).read_bytes()
    if sha(raw) != c['input_sha256'] or len(raw) != c['input_size'] or c['install_to_stage']:
        raise ValueError('not reviewed backend input/candidate scope')
    if [(x['callsite'], x['mask_setup']) for x in c['calls']] != [(0x57a1b0, 0x57a208), (0x57c898, 0x57c8d4)]:
        raise ValueError('unreviewed output entries')
    e = Elf(raw)
    for call in c['calls']:
        if any(e.function(call['va'])[key] != call[key] for key in e.function(call['va'])):
            raise ValueError('parent function differs')
        if e.at(call['callsite'], 4).hex() != call['call_before_hex'] or branch_target(e.word(call['callsite']), call['callsite']) != c['strncmp_plt']:
            raise ValueError('callsite differs')
        if e.at(call['mask_setup'], 16).hex() != call['mask_setup_before_hex']:
            raise ValueError('parameter setup differs')
    if e.plt_import(c['strncmp_plt']) != 'strncmp' or c['prefix'] != 'FP Maskview' or c['cie'] != 1017376:
        raise ValueError('prefix/PLT/CIE differs')
    phoff = struct.unpack_from('<Q', raw, 32)[0]
    phsize, phnum = struct.unpack_from('<HH', raw, 54)
    ph = [list(struct.unpack_from('<IIQQQQQQ', raw, phoff + i * phsize)) for i in range(phnum)]
    if phoff != 64 or phsize != 56 or phnum != 14:
        raise ValueError('program-header layout differs')
    note = ph[13]
    if note != [4, 4, 0x3a0, 0x3a0, 0x3a0, 32, 32, 8] or ph[11] != [0x6474e553, *note[1:]] or ph[9][0] != 0x6474e550:
        raise ValueError('not duplicate GNU property NOTE with retained dedicated header')
    base = align(len(raw), 4096)
    if base < max(p[3] + p[6] for p in ph if p[0] == 1):
        raise ValueError('new LOAD would overlap mapped memory')
    out.mkdir(parents=True)
    linker_script = f'SECTIONS {{ . = 0x{base:x}; .text : {{ *(.text) }} /DISCARD/ : {{ *(.note*) *(.comment*) }} }}\n'
    for call in c['calls']:
        n = call['id']
        linker_script += f't860_resume_{n} = 0x{call["callsite"] + 4:x}; t860_mask_{n} = 0x{call["mask_setup"]:x};\n'
    linker_script += f't860_strncmp = 0x{c["strncmp_plt"]:x};\n'
    (out / 'dispatch.ld').write_text(linker_script)
    source = ROOT / 'patches/t860-fp-output-ui85.S'
    subprocess.run([str(NDK / 'clang'), '--target=aarch64-linux-android36', '-c', str(source), '-o', str(out / 'dispatch.o')], check=True)
    subprocess.run([str(NDK / 'ld.lld'), '--build-id=none', '-T', str(out / 'dispatch.ld'), str(out / 'dispatch.o'), '-o', str(out / 'dispatch.elf'), '-e', 't860_fp_output_1'], check=True)
    compiled_raw = (out / 'dispatch.elf').read_bytes()
    compiled = Elf(compiled_raw)
    text = compiled.by_name['.text']
    if text.va != base:
        raise ValueError('link address differs')
    sym = compiled.by_name['.symtab']
    strings_section = compiled.sections[sym.link]
    strings = compiled_raw[strings_section.offset:strings_section.offset + strings_section.size]
    helpers = {}
    for i in range(sym.size // 24):
        name, _, _, _, value, size = struct.unpack_from('<IBBHQQ', compiled_raw, sym.offset + i * 24)
        name = strings[name:strings.index(b'\0', name)].decode()
        if name.startswith('t860_fp_output_'):
            helpers[name] = (value, size)
    if sorted(helpers) != ['t860_fp_output_1', 't860_fp_output_2']:
        raise ValueError('helper symbol scope differs')
    code = compiled_raw[text.offset:text.offset + text.size]
    result = bytearray(raw + bytes(base - len(raw)) + code)
    fde_base = align(len(result), 4)
    result.extend(bytes(fde_base - len(result)))
    entries = []
    for call in c['calls']:
        start, size = helpers[f't860_fp_output_{call["id"]}']
        fde_va = len(result)
        new_fde = fde(fde_va, start, size, call)
        result.extend(new_fde)
        entries.append((start, fde_va))
        call.update({'helper_va': start, 'helper_size': size, 'new_fde_va': fde_va})
        delta = start - call['callsite']
        if delta % 4 or not -(1 << 27) <= delta < 1 << 27:
            raise ValueError('direct B out of range')
        struct.pack_into('<I', result, call['callsite'], 0x14000000 | ((delta // 4) & 0x3ffffff))
    fde_size = len(result) - fde_base
    hdr = e.by_name['.eh_frame_hdr']
    if e.at(hdr.va, 4) != b'\x01\x1b\x03\x3b':
        raise ValueError('unreviewed header encoding')
    count = struct.unpack_from('<I', raw, hdr.offset + 8)[0]
    if hdr.size != 12 + 8 * count:
        raise ValueError('header bounds differ')
    old_entries = [(hdr.va + x, hdr.va + y) for x, y in struct.iter_unpack('<ii', raw[hdr.offset + 12:hdr.offset + hdr.size])]
    all_entries = sorted(old_entries + entries)
    if len(set(x for x, _ in all_entries)) != len(all_entries):
        raise ValueError('duplicate header start')
    hdr_base = align(len(result), 4)
    result.extend(bytes(hdr_base - len(result)))
    header = b'\x01\x1b\x03\x3b' + struct.pack('<iI', e.by_name['.eh_frame'].va - (hdr_base + 4), len(all_entries))
    header += b''.join(struct.pack('<ii', x - hdr_base, y - hdr_base) for x, y in all_entries)
    result.extend(header)
    load_size = len(result) - base
    ph[13] = [1, 5, base, base, base, load_size, load_size, 4096]
    ph[9] = [0x6474e550, 4, hdr_base, hdr_base, hdr_base, len(header), len(header), 4]
    for index in (9, 13):
        struct.pack_into('<IIQQQQQQ', result, phoff + index * phsize, *ph[index])
    shoff = struct.unpack_from('<Q', raw, 40)[0]
    shsize, shnum, shstr = struct.unpack_from('<HHH', raw, 58)
    if shsize != 64:
        raise ValueError('unreviewed section headers')
    sections = [list(struct.unpack_from('<IIQQQQIIQQ', raw, shoff + i * 64)) for i in range(shnum)]
    string_header = sections[shstr]
    section_names = bytearray(raw[string_header[4]:string_header[4] + string_header[5]])
    for name, flags, va, size in [('.t860.fp_dispatch', 6, base, len(code)), ('.t860.fp_unwind', 2, fde_base, fde_size)]:
        offset = len(section_names)
        section_names.extend(name.encode() + b'\0')
        sections.append([offset, 1, flags, va, va, size, 0, 0, 4, 0])
    sections[e.sections.index(hdr)][3:6] = [hdr_base, hdr_base, len(header)]
    string_header[4:6] = [len(result), len(section_names)]
    result.extend(section_names)
    new_shoff = align(len(result), 8)
    result.extend(bytes(new_shoff - len(result)))
    result.extend(b''.join(struct.pack('<IIQQQQIIQQ', *s) for s in sections))
    struct.pack_into('<Q', result, 40, new_shoff)
    struct.pack_into('<H', result, 60, len(sections))
    # Before EOF only the two instructions, EH_FRAME/duplicate NOTE descriptors,
    # and e_shoff/e_shnum may differ. All original payloads remain intact.
    allowed = set(range(40, 48)) | set(range(60, 62))
    for index in (9, 13):
        allowed.update(range(phoff + index * phsize, phoff + (index + 1) * phsize))
    for call in c['calls']:
        allowed.update(range(call['callsite'], call['callsite'] + 4))
    changed = [i for i, (a, b) in enumerate(zip(raw, result)) if a != b]
    if not set(changed) <= allowed:
        raise ValueError('unapproved original-file changes')
    new = Elf(bytes(result))
    for call in c['calls']:
        if new.function(call['helper_va'])['size'] != call['helper_size']:
            raise ValueError('helper not described by new EH header/FDE')
    target = out / 'system/bin/surfaceflinger'
    target.parent.mkdir(parents=True)
    target.write_bytes(result)
    target.chmod(0o755)
    report = {'schema': 1, 'kind': 'compatibility_probe', 'component': 'F04_HIDL_AND_FP_DISPATCH',
              'input_sha256': sha(raw), 'output_sha256': sha(result), 'output_size': len(result),
              'append_bytes': len(result) - len(raw), 'old_file_changed_bytes': len(changed),
              'calls': c['calls'], 'old_eh_entries': count, 'new_eh_entries': len(all_entries),
              'new_rx_load': ph[13], 'new_eh_header': ph[9],
              'retained_program_headers': [i for i in range(phnum) if i not in (9, 13)],
              'source_sha256': sha(source.read_bytes()), 'profile_sha256': sha(PROFILE.read_bytes()),
              'script_sha256': sha(Path(__file__).read_bytes()),
              'tools': {n: sha((NDK / n).read_bytes()) for n in ('clang', 'ld.lld')},
              'flashable': False, 'stage_modified': False, 'device_writes': False,
              'runtime': 'NOT_TESTED', 'unwind_runtime': 'NOT_TESTED'}
    (out / 'patch-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('output_sha256', 'append_bytes', 'old_file_changed_bytes', 'new_eh_entries', 'runtime')}))


if __name__ == '__main__':
    main()
