#!/usr/bin/env python3
"""Prepare F02 on the new donor JAR; never edit a staging tree or old ROM.

The CE secret and credential verification are retained. See CE_UPGRADE_AUDIT.md.
Input hash and new StorageManagerInternalImpl call shape must both match.
"""
from __future__ import annotations

import argparse
import binascii
import hashlib
import json
from pathlib import Path
import struct
from zipfile import ZipFile

import dex041 as dex

ROOT = Path(__file__).resolve().parents[1]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(original: bytes, contract: dict) -> tuple[bytes, dict]:
    if sha(original) != contract['input_sha256']:
        raise ValueError('requires exact unchanged X710 donor services.jar')
    member = dex.find_stored_member(original, 'classes.dex')
    payload = original[member.data_off:member.data_off + member.size]
    if binascii.crc32(payload) & 0xffffffff != member.crc:
        raise ValueError('input ZIP CRC mismatch')
    container = dex.DexContainer(payload)
    method = container.find_method(contract['target_class'], contract['target_method'], contract['target_descriptor'])
    units = method.units()
    hat_call = ('Lcom/android/internal/widget/VerifyCredentialResponse;', 'getGatekeeperHAT', '()[B')
    storage_call = (contract['storage_class'], contract['storage_method'], contract['storage_descriptor'])
    field = (contract['target_class'], 'mStorageManagerInternal', contract['storage_class'])
    candidates = []
    for index in range(len(units) - 13):
        if units[index] & 0xff != 0x38 or units[index + 2] & 0xff != 0x6e:
            continue
        if method.section.method_id(units[index + 3]) != hat_call:
            continue
        response = units[index] >> 8
        if units[index + 2] != 0x106e or units[index + 4] != response:
            continue
        if units[index + 5] != (response << 8 | 0x0c) or units[index + 6] != (response << 8 | 0x38):
            continue
        target = index + struct.unpack('<h', struct.pack('<H', units[index + 1]))[0]
        if target <= index or target + 5 >= len(units):
            continue
        if units[index + 8] & 0xff != 0x54 or units[target] & 0xff != 0x54:
            continue
        if method.section.field_id(units[index + 9]) != field or method.section.field_id(units[target + 1]) != field:
            continue
        if units[target:target + 2] != units[index + 8:index + 10]:
            continue
        if units[target + 2] != (response << 8 | 0x12):
            continue
        if units[target + 3] != 0x406e or units[index + 10] != 0x406e:
            continue
        if method.section.method_id(units[target + 4]) != storage_call:
            continue
        if units[target + 3:target + 6] != units[index + 10:index + 13]:
            continue
        # Both paths call the same receiver, user, HAT register and secret.
        if ((units[target + 5] >> 8) & 0xf) != response:
            continue
        candidates.append((index, target))
    if len(candidates) != 1:
        raise ValueError(f'expected one new-donor HAT branch, found {len(candidates)}')
    index, target = candidates[0]
    before_code = payload[method.insns_off:method.insns_off + method.insns_size * 2]
    absolute = method.insns_off + index * 2
    old_word = units[index]
    dex.put_u16(container.data, absolute, 0x0029)
    for section in container.sections:
        section.update_signature_and_checksum()
        section.verify_signature_and_checksum()
    patched = bytes(container.data)
    allowed = [(absolute, absolute + 2)] + [(s.base + 8, s.base + 32) for s in container.sections]
    differences = [i for i, pair in enumerate(zip(payload, patched)) if pair[0] != pair[1]]
    if len(patched) != len(payload) or any(not any(a <= i < b for a, b in allowed) for i in differences):
        raise ValueError('unexpected DEX changes')
    after_code = patched[method.insns_off:method.insns_off + method.insns_size * 2]
    if before_code[:index*2] != after_code[:index*2] or before_code[index*2+2:] != after_code[index*2+2:]:
        raise ValueError('changed other instructions or branch delta')
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
    verify = dex.DexContainer(patched)
    checked = verify.find_method(contract['target_class'], contract['target_method'], contract['target_descriptor'])
    if checked.units()[index:index + 2] != [0x0029, units[index + 1]]:
        raise ValueError('output semantic verification failed')
    if sha(bytes(output)) != contract['output_sha256']:
        raise ValueError('output hash differs from independently disassembled candidate')
    report = {'id': 'F02', 'status': 'PREPARED_NOT_APPLIED_NOT_RUNTIME_TESTED',
              'input_jar_sha256': sha(original), 'output_jar_sha256': sha(bytes(output)),
              'input_dex_sha256': sha(payload), 'output_dex_sha256': sha(patched),
              'logical_dex_count': len(container.sections), 'target_dex': method.section.index,
              'target_method': method.label(), 'instruction_index': index, 'null_hat_target': target,
              'old_instruction': hex(old_word), 'new_instruction': '0x0029',
              'before_method_code_sha256': sha(before_code), 'after_method_code_sha256': sha(after_code),
              'one_instruction_changed': True, 'user_and_secret_registers_unchanged': True,
              'all_other_jar_bytes_identical': True, 'method_and_exception_offsets_unchanged': True,
              'changed_dex_byte_count_including_checksums': len(differences),
              'dirty_upgrade_runtime': 'NOT_TESTED'}
    return bytes(output), report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists() or args.input.resolve() in (args.output.resolve(), args.report.resolve()) or args.output.resolve() == args.report.resolve():
        raise ValueError('requires distinct new output and report paths')
    contract = json.loads((ROOT / 'device/s6/ce-unlock-ui85.json').read_text())
    output, report = prepare(args.input.read_bytes(), contract)
    for path in (args.output, args.report):
        path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation, never overwrite a donor/reference.
    with args.output.open('xb') as stream:
        stream.write(output)
    with ZipFile(args.output) as archive:
        if archive.testzip():
            raise ValueError('output ZIP integrity failed')
    report['contract_sha256'] = sha((ROOT / 'device/s6/ce-unlock-ui85.json').read_bytes())
    report['patcher_sha256'] = sha(Path(__file__).read_bytes())
    report['generic_parser_sha256'] = sha((ROOT / 'patches/dex041.py').read_bytes())
    with args.report.open('x') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
