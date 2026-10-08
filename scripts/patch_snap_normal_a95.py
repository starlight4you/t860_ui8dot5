#!/usr/bin/env python3
"""Only normal SNAP checkService-null goes to the donor's post-wait null handler."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SOURCE_SHA = '8d4d95dad671cb6be94017a11e0c9a2daf9e9089eb614be611322b14e2aa0569'
SOURCE_SIZE = 148368
EDITS = {0x1d210: (0x90ffff54, 0xaa0003f4),
         0x1d214: (0x91345694, 0x14000018)}
GUARDS = {0x1cf94: 0xd503233f, 0x1d094: 0x94000f85,
          0x1d098: 0xb5000400, 0x1d0e4: 0x1400005d,
          0x1d110: 0x94000f66, 0x1d114: 0xb40007e0,
          0x1d274: 0x90ffff41, 0x1d278: 0x91345421,
          0x1d27c: 0xb4000654, 0x1d258: 0x94000f26,
          0x1d368: 0xf9000fb4, 0x1d36c: 0x94000edb,
          0x1d428: 0x9400008b}

def sha(b): return hashlib.sha256(b).hexdigest()

def patch(data):
    if len(data) != SOURCE_SIZE or sha(data) != SOURCE_SHA:
        raise ValueError('Only the reviewed S9 UI8.5 original SNAP library is accepted')
    if data[:7] != b'\x7fELF\x02\x01\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
        raise ValueError('AArch64 ELF required')
    off = struct.unpack_from('<Q', data, 32)[0]
    entsize, count = struct.unpack_from('<HH', data, 54)
    loads = []
    for i in range(count):
        typ, flags, fileoff, va, _, filesz, memsz, align = struct.unpack_from('<IIQQQQQQ', data, off+i*entsize)
        if typ == 1 and flags == 5: loads.append((fileoff, va, filesz))
    if loads != [(0xa000, 0xa000, 0x17178)]:
        raise ValueError('Reviewed executable VA/file mapping differs')
    for va, word in {**GUARDS, **{v: old for v, (old, new) in EDITS.items()}}.items():
        if struct.unpack_from('<I', data, va)[0] != word:
            raise ValueError(f'Instruction guard differs at {va:#x}')
    out = bytearray(data)
    for va, (old, new) in EDITS.items(): struct.pack_into('<I', out, va, new)
    changed = [i for i, (a,b) in enumerate(zip(data,out)) if a != b]
    if any(i//4*4 not in EDITS for i in changed): raise ValueError('Unexpected mutation')
    return bytes(out), changed

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a=p.parse_args()
    if a.source.is_symlink() or a.out.exists(): raise ValueError('Regular original and fresh output required')
    data=a.source.read_bytes(); after, changed=patch(data)
    a.out.mkdir(parents=True)
    target=a.out/'libsnap_aidl.snap.samsung.so'; target.write_bytes(after)
    report={'id':'A95_SNAP_NORMAL_NULL_CANDIDATE','source_sha256':sha(data),
        'after_sha256':sha(after),'size':len(after),'byte_offsets_changed':changed,
        'edits':[{'va':hex(v),'before':hex(old),'after':hex(new)} for v,(old,new) in EDITS.items()],
        'normal_success_path':'UNCHANGED','secure_path':'UNCHANGED','relocations':'UNCHANGED',
        'null_binder_error_path':'DONOR_EXISTING; not inference success or CPU fallback',
        'reason':'docs/SNAP_NONBLOCKING_A95.md','generator_sha256':sha(Path(__file__).read_bytes()),
        'device_operations':'NOT_EXECUTED'}
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
