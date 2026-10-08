"""A53 pinned new-donor MAP_CREATE name compatibility; no status bypass."""
import hashlib
import struct
from elf_aarch64 import Elf, branch_target


def prepare(raw, c):
    if len(raw) != c['bytes'] or hashlib.sha256(raw).hexdigest() != c['input_sha256']:
        raise ValueError('Unreviewed platform library')
    e = Elf(raw)
    va = c['patch']['va']
    if e.function(va) != c['function'] or e.word(va) != int(c['patch']['before_word'], 16):
        raise ValueError('Original function/call differs')
    if e.plt_import(branch_target(e.word(va), va)) != '__strlcpy_chk':
        raise ValueError('Must be map-name copy call')
    expected = {0x6558: 0x6f00e400, 0x658c: 0xad1f83e0, 0x6590: 0xb903f3e9,
                0x65c8: 0x91007100, 0x65d0: 0x910fc3e2, 0x65d4: 0x52802300,
                0x65d8: 0x2a1f03e1, 0x65dc: 0x52801303, 0x65e0: 0x94001c3e}
    if any(e.word(k) != v for k, v in expected.items()) or e.plt_import(0xd6d8) != 'syscall':
        raise ValueError('Zero initialization / attr28 / real syscall differs')
    if c['patch']['after_word'] != 'd503201f':
        raise ValueError('Only NOP of name copy permitted')
    result = bytearray(raw)
    struct.pack_into('<I', result, e.offset(va, 4), 0xd503201f)
    if hashlib.sha256(result).hexdigest() != c['output_sha256']:
        raise ValueError('Output SHA differs')
    return bytes(result)
