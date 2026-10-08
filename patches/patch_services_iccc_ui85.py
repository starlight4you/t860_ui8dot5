#!/usr/bin/env python3
"""Prepare three ICCC call-site degradations; preserve new donor permissions.

Rationale recorded before editing in docs/ICCC_REBASE_AUDIT.md. Probe only.
"""
from __future__ import annotations

import argparse
import binascii
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import dex041 as dex

ROOT = Path(__file__).resolve().parents[1]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(original: bytes, contract: dict, *, require_output_pin: bool = True) -> tuple[bytes, dict]:
    profiles = [name for name, digest in contract['inputs'].items() if digest == sha(original)]
    if len(profiles) != 1:
        raise ValueError('requires exact X710 stock or independently verified F02 input')
    profile = profiles[0]
    member = dex.find_stored_member(original, 'classes.dex')
    payload = original[member.data_off:member.data_off + member.size]
    if binascii.crc32(payload) & 0xffffffff != member.crc:
        raise ValueError('input ZIP CRC mismatch')
    container = dex.DexContainer(payload)
    klass = contract['target_class']
    permission = (klass, contract['permission_method'], contract['permission_descriptor'])
    ranges, changes = [], []
    for spec in contract['methods']:
        method = container.find_method(klass, spec['name'], spec['descriptor'])
        units = method.units()
        code = payload[method.insns_off:method.insns_off + method.insns_size * 2]
        if sha(code) != spec['code_sha256'] or method.registers_size != spec['registers']:
            raise ValueError(f"{spec['name']}: instruction hash/register count changed")
        native = (klass, spec['native_name'], spec['descriptor'])
        # Whole method hashes pin instruction boundaries as well as try/catch offsets.
        calls = [(i, method.section.method_id(units[i + 1])) for i in range(len(units) - 2)
                 if units[i] & 0xff == 0x71]
        native_sites = [i for i, target in calls if target == native]
        permissions = [i for i, target in calls if target == permission]
        if len(native_sites) != 1 or len(permissions) != 1 or permissions[0] >= native_sites[0]:
            raise ValueError(f"{spec['name']}: native/preceding permission anchor mismatch")
        index = native_sites[0]
        register = spec['result_register']
        expected = [spec['invoke_word'], units[index + 1], spec['argument_word'], register << 8 | 0x0c]
        if units[index:index + 4] != expected or not 0 <= register < min(16, method.registers_size):
            raise ValueError(f"{spec['name']}: native invoke/result register shape mismatch")
        array_type = method.section.type_index('[B')
        if array_type > 0xffff:
            raise ValueError('array type does not fit instruction')
        replacement = [register << 8 | 0x12, register << 12 | register << 8 | 0x23, array_type, 0]
        absolute = method.insns_off + index * 2
        for delta, word in enumerate(replacement):
            dex.put_u16(container.data, absolute + delta * 2, word)
        ranges.append((absolute, absolute + 8))
        after = bytes(container.data[method.insns_off:method.insns_off + method.insns_size * 2])
        changes.append({'method': method.label(), 'logical_dex': method.section.index,
                        'instruction_index': index, 'result_register': register,
                        'permission_instruction_index': permissions[0],
                        'old_units': expected, 'new_units': replacement,
                        'before_code_sha256': sha(code), 'after_code_sha256': sha(after),
                        'tries_size_unchanged': method.tries_size})
    for section in container.sections:
        section.update_signature_and_checksum()
        section.verify_signature_and_checksum()
    allowed = ranges + [(section.base + 8, section.base + 32) for section in container.sections]
    patched = bytes(container.data)
    differences = [i for i, pair in enumerate(zip(payload, patched)) if pair[0] != pair[1]]
    if len(payload) != len(patched) or any(not any(a <= i < b for a, b in allowed) for i in differences):
        raise ValueError('unexpected DEX changes outside three call sites/checksums')
    output = bytearray(original)
    output[member.data_off:member.data_off + member.size] = patched
    crc = binascii.crc32(patched) & 0xffffffff
    dex.put_u32(output, member.local_crc_off, crc)
    dex.put_u32(output, member.central_crc_off, crc)
    permitted = [(member.data_off + a, member.data_off + b) for a, b in allowed]
    permitted += [(member.local_crc_off, member.local_crc_off + 4), (member.central_crc_off, member.central_crc_off + 4)]
    if any(a != b and not any(start <= i < end for start, end in permitted)
           for i, (a, b) in enumerate(zip(original, output))):
        raise ValueError('unexpected JAR changes')
    if require_output_pin and sha(output) != contract['outputs'].get(profile):
        raise ValueError('output differs from independently disassembled candidate')
    report = {'id': contract['id'], 'status': 'PREPARED_NOT_APPLIED_NOT_RUNTIME_TESTED',
              'input_profile': profile, 'input_jar_sha256': sha(original), 'output_jar_sha256': sha(output),
              'logical_dex_count': len(container.sections), 'methods': changes,
              'changed_dex_bytes_including_checksums': len(differences),
              'all_other_jar_bytes_identical': True, 'runtime': 'NOT_TESTED'}
    return bytes(output), report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists() or len({p.resolve() for p in (args.input, args.output, args.report)}) != 3:
        raise ValueError('requires distinct new output and report paths')
    contract_path = ROOT / 'device/s6/iccc-ui85.json'
    output, report = prepare(args.input.read_bytes(), json.loads(contract_path.read_text()))
    for path in (args.output, args.report):
        path.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(output)
    with ZipFile(args.output) as archive:
        if archive.testzip():
            raise ValueError('output ZIP integrity failed')
    report.update({'contract_sha256': sha(contract_path.read_bytes()),
                   'patcher_sha256': sha(Path(__file__).read_bytes()),
                   'generic_parser_sha256': sha((ROOT / 'patches/dex041.py').read_bytes())})
    with args.report.open('x') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
