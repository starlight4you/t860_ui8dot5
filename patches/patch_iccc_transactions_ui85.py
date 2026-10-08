#!/usr/bin/env python3
"""Map two supported X710 HIDL operations onto T860 transaction numbers.

Only paired with F01-ICCC; see the reason recorded in ICCC_REBASE_AUDIT.md.
This changes new donor system code, never substitutes the T860 vendor HAL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(original: bytes, contract: dict, *, require_output_pin: bool = True) -> tuple[bytes, dict]:
    if sha(original) != contract['input_sha256']:
        raise ValueError('requires exact unchanged X710 system ICCC interface library')
    output = bytearray(original)
    allowed, changes = [], []
    for spec in contract['operations']:
        start, size = spec['function_file_offset'], spec['function_size']
        offset = spec['mov_w1_file_offset']
        if not start <= offset < start + size - 3 or sha(original[start:start + size]) != spec['code_sha256']:
            raise ValueError('proxy function hash/bounds changed')
        word = struct.unpack_from('<I', original, offset)[0]
        if word & 0xffe0001f != 0x52800001 or word != int(spec['mov_w1_word'], 16):
            raise ValueError('MOVZ W1 transact constant anchor changed')
        if (word >> 5) & 0xffff != spec['from_transaction'] or spec['to_transaction'] not in (6, 7):
            raise ValueError('unexpected transaction mapping')
        if (spec['operation'], spec['from_transaction'], spec['to_transaction']) not in (
                ('initializeMeasurement', 8, 6), ('terminate', 9, 7)):
            raise ValueError('operation/mapping outside reviewed pair')
        replacement = (word & ~(0xffff << 5)) | (spec['to_transaction'] << 5)
        struct.pack_into('<I', output, offset, replacement)
        allowed.append((offset, offset + 4))
        changes.append({'operation': spec['operation'], 'va': spec['mov_w1_va'], 'file_offset': offset,
                        'from_transaction': spec['from_transaction'], 'to_transaction': spec['to_transaction'],
                        'old_word': f'0x{word:08x}', 'new_word': f'0x{replacement:08x}'})
    if len(changes) != 2 or {c['operation'] for c in changes} != {'initializeMeasurement', 'terminate'}:
        raise ValueError('requires exactly the two reviewed operations')
    changed = [i for i, (a, b) in enumerate(zip(original, output)) if a != b]
    if len(original) != len(output) or any(not any(a <= i < b for a, b in allowed) for i in changed):
        raise ValueError('unexpected ELF changes')
    if require_output_pin and sha(output) != contract['output_sha256']:
        raise ValueError('output differs from independent disassembly pin')
    return bytes(output), {'id': contract['id'], 'status': 'PREPARED_NOT_APPLIED_NOT_RUNTIME_TESTED',
                           'input_sha256': sha(original), 'output_sha256': sha(output), 'changes': changes,
                           'changed_byte_count': len(changed), 'all_other_elf_bytes_identical': True,
                           'requires_paired_framework_patch': 'F01-ICCC', 'runtime': 'NOT_TESTED'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists() or len({p.resolve() for p in (args.input, args.output, args.report)}) != 3:
        raise ValueError('requires distinct new output and report paths')
    contract_path = ROOT / 'device/s6/iccc-transactions-ui85.json'
    output, report = prepare(args.input.read_bytes(), json.loads(contract_path.read_text()))
    for path in (args.output, args.report):
        path.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(output)
    report.update({'contract_sha256': sha(contract_path.read_bytes()), 'patcher_sha256': sha(Path(__file__).read_bytes())})
    with args.report.open('x') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
