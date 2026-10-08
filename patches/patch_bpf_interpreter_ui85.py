"""A52: skip only JIT sysctl setup for the pinned S6 interpreter BOOT."""
import hashlib
import struct
from elf_aarch64 import Elf, branch_target


def prepare(raw, profile):
    if len(raw) != profile['bytes'] or hashlib.sha256(raw).hexdigest() != profile['input_sha256']:
        raise ValueError('Unreviewed donor/B06 loader')
    elf = Elf(raw)
    p = profile['patch']
    if elf.function(p['va']) != profile['function']:
        raise ValueError('Loader function differs')
    old, new = int(p['before_word'], 16), int(p['after_word'], 16)
    if elf.word(p['va']) != old or branch_target(old, p['va']) != p['target_va']:
        raise ValueError('JIT branch differs')
    if new & 0xfc000000 != 0x14000000 or branch_target(new, p['va']) != p['target_va']:
        raise ValueError('Patch must reach existing pin/load continuation')
    # Pin both exact path arguments and the two checked callsites.
    if elf.at(0xd204, 0x40).hex() != (
        '683244391f050071a1010054a0ffffb0006c2091a1ffffb021102c91'
        '31110094600c0036a0ffffd000c41c91a1ffffb021102c912b110094'
        '000e0036a0ffffd0'):
        raise ValueError('JIT setup/next instruction differs')
    if elf.string_va(b'/proc/sys/net/core/bpf_jit_enable') != 0x281b or elf.string_va(b'/proc/sys/net/core/bpf_jit_kallsyms') != 0x3731:
        raise ValueError('JIT path layout differs')
    result = bytearray(raw)
    struct.pack_into('<I', result, elf.offset(p['va'], 4), new)
    if hashlib.sha256(result).hexdigest() != profile['output_sha256']:
        raise ValueError('Output SHA differs')
    return bytes(result)
