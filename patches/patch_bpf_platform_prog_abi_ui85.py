"""A54 pinned new-donor PROG_LOAD name compatibility; no status bypass."""
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
        raise ValueError('Must be program-name copy call')
    expected = {0x65cc:0xd503201f, 0x77e8:0x6f00e400, 0x7814:0x3d810be0,
                0x781c:0xad1f83e0, 0x7854:0xb9041be9, 0x7860:0x910fc3eb,
                0x7868:0x9100c160, 0x7884:0x3c82c160,
                0x78a0:0x910fc3e2, 0x78a4:0x52802300,
                0x78a8:0x528000a1, 0x78ac:0x52801303, 0x78b0:0x9400178a}
    if any(e.word(k) != v for k,v in expected.items()) or e.plt_import(0xd6d8) != 'syscall':
        raise ValueError('A53 fix / zero initialization / attr48 / real PROG_LOAD differs')
    if c['patch']['after_word'] != 'd503201f':
        raise ValueError('Only NOP of name copy permitted')
    result = bytearray(raw)
    struct.pack_into('<I', result, e.offset(va, 4), 0xd503201f)
    if hashlib.sha256(result).hexdigest() != c['output_sha256']:
        raise ValueError('Output SHA differs')
    return bytes(result)
