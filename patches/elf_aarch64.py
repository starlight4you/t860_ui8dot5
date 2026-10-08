"""Read-only ELF/AArch64 helpers for pinned new-donor patches.

Contains no display/ICCC policy. Unsupported encodings fail explicitly.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
import hashlib
import struct


@dataclass(frozen=True)
class Section:
    name: str
    kind: int
    flags: int
    va: int
    offset: int
    size: int
    link: int
    entry_size: int


def signed(value: int, width: int) -> int:
    return value - (1 << width) if value & (1 << (width - 1)) else value


def adrp_page(word: int, pc: int) -> tuple[int, int]:
    if word & 0x9f000000 != 0x90000000:
        raise ValueError('not ADRP')
    immediate = ((word >> 5 & 0x7ffff) << 2) | (word >> 29 & 3)
    return word & 31, (pc & ~4095) + (signed(immediate, 21) << 12)


def branch_target(word: int, pc: int) -> int:
    if word & 0x7c000000 == 0x14000000:  # B/BL
        return pc + (signed(word & 0x3ffffff, 26) << 2)
    if word & 0xff000010 == 0x54000000:  # B.cond
        return pc + (signed(word >> 5 & 0x7ffff, 19) << 2)
    if word & 0x7e000000 == 0x36000000:  # TBZ/TBNZ
        return pc + (signed(word >> 5 & 0x3fff, 14) << 2)
    raise ValueError('unsupported branch instruction')


class Elf:
    def __init__(self, raw: bytes):
        self.raw = raw
        if raw[:7] != b'\x7fELF\x02\x01\x01' or struct.unpack_from('<H', raw, 18)[0] != 183:
            raise ValueError('requires ELF64 little-endian AArch64')
        shoff = struct.unpack_from('<Q', raw, 40)[0]
        stride, count, strings_index = struct.unpack_from('<HHH', raw, 58)
        if stride != 64 or not 0 < strings_index < count or shoff + stride * count > len(raw):
            raise ValueError('invalid section table')
        headers = [struct.unpack_from('<IIQQQQIIQQ', raw, shoff + stride * i) for i in range(count)]
        string_header = headers[strings_index]
        strings = raw[string_header[4]:string_header[4] + string_header[5]]
        self.sections = []
        for name, kind, flags, va, offset, size, link, _, _, entry_size in headers:
            end = strings.find(b'\0', name)
            if end < name or kind != 8 and offset + size > len(raw):
                raise ValueError('invalid section/name bounds')
            self.sections.append(Section(strings[name:end].decode('ascii'), kind, flags, va, offset, size, link, entry_size))
        self.by_name = {section.name: section for section in self.sections}
        self._relr_locations = None

    def offset(self, va: int, size: int = 1) -> int:
        hits = [section.offset + va - section.va for section in self.sections
                if section.flags & 2 and section.kind != 8 and section.va <= va and va + size <= section.va + section.size]
        if len(hits) != 1:
            raise ValueError(f'VA 0x{va:x} is not uniquely file-backed')
        return hits[0]

    def at(self, va: int, size: int) -> bytes:
        offset = self.offset(va, size)
        return self.raw[offset:offset + size]

    def word(self, va: int) -> int:
        return struct.unpack('<I', self.at(va, 4))[0]

    def symbol(self, index: int) -> str:
        section = self.by_name['.dynsym']
        if section.entry_size != 24 or index * 24 >= section.size:
            raise ValueError('invalid dynsym index/stride')
        name = struct.unpack_from('<I', self.raw, section.offset + index * 24)[0]
        strings = self.sections[section.link]
        table = self.raw[strings.offset:strings.offset + strings.size]
        end = table.find(b'\0', name)
        if end < name:
            raise ValueError('invalid symbol string')
        return table[name:end].decode('ascii')

    def relocations(self, section_name: str):
        section = self.by_name[section_name]
        if section.entry_size != 24 or section.size % 24:
            raise ValueError('unsupported relocation stride')
        for offset in range(section.offset, section.offset + section.size, 24):
            va, info, addend = struct.unpack_from('<QQq', self.raw, offset)
            yield va, info & 0xffffffff, info >> 32, addend

    def relative_pointer(self, va: int) -> int:
        # ELF64 RELR: even entry is an address, odd entry is a 63-word bitmap.
        # Read the in-file addend only when this location is actually relocated.
        # Encoding reference: AOSP bionic linker relocate_relr, not raw-pointer guessing.
        if self._relr_locations is None:
            self._relr_locations = set()
            section = self.by_name.get('.relr.dyn')
            if section:
                if section.entry_size != 8 or section.size % 8:
                    raise ValueError('unsupported RELR encoding')
                base = None
                for (entry,) in struct.iter_unpack('<Q', self.raw[section.offset:section.offset + section.size]):
                    if not entry & 1:
                        if entry % 8:
                            raise ValueError('unaligned RELR address')
                        self._relr_locations.add(entry)
                        base = entry + 8
                    else:
                        if base is None:
                            raise ValueError('RELR bitmap without address')
                        for bit in range(63):
                            if entry >> (bit + 1) & 1:
                                self._relr_locations.add(base + bit * 8)
                        base += 63 * 8
        if va in self._relr_locations:
            return struct.unpack('<Q', self.at(va, 8))[0]
        # APS2 has a separate format; do not treat its byte stream as Elf64_Rela.
        if self.by_name['.rela.dyn'].kind != 4:
            raise ValueError('pointer is not in RELR and packed RELA is outside helper scope')
        hits = [addend for target, kind, _, addend in self.relocations('.rela.dyn') if target == va and kind == 1027]
        if len(hits) != 1:
            raise ValueError('relative pointer relocation not unique')
        return hits[0]

    def plt_import(self, va: int) -> str:
        words = struct.unpack('<IIII', self.at(va, 16))
        register, page = adrp_page(words[0], va)
        if register != 16 or words[1] & 0xffc003ff != 0xf9400211 or words[2] & 0xffc003ff != 0x91000210 or words[3] != 0xd61f0220:
            raise ValueError('unsupported pinned PLT slot')
        got = page + (words[1] >> 10 & 4095) * 8
        if got != page + (words[2] >> 10 & 4095):
            raise ValueError('PLT LDR/ADD disagree')
        hits = [index for target, kind, index, _ in self.relocations('.rela.plt') if target == got and kind == 1026]
        if len(hits) != 1:
            raise ValueError('PLT relocation not unique')
        return self.symbol(hits[0])

    def string_va(self, value: bytes) -> int:
        section = self.by_name['.rodata']
        raw = self.raw[section.offset:section.offset + section.size]
        matches, start = [], 0
        while (position := raw.find(value + b'\0', start)) >= 0:
            matches.append(section.va + position)
            start = position + 1
        if len(matches) != 1:
            raise ValueError(f'expected unique rodata string: {value!r}')
        return matches[0]

    def string_xrefs(self, target: int) -> list[tuple[int, int]]:
        section = self.by_name['.text']
        words = struct.unpack_from('<' + 'I' * (section.size // 4), self.raw, section.offset)
        matches = []
        for index, word in enumerate(words):
            if word & 0x9f000000 != 0x90000000:
                continue
            pc = section.va + index * 4
            register, page = adrp_page(word, pc)
            if page != target & ~4095:
                continue
            for other in range(index + 1, min(index + 9, len(words))):
                instruction = words[other]
                if instruction & 0xff000000 != 0x91000000 or instruction >> 5 & 31 != register:
                    continue
                immediate = (instruction >> 10 & 4095) << (12 if instruction >> 22 & 1 else 0)
                if page + immediate == target:
                    matches.append((pc, section.va + other * 4))
        return matches

    def function(self, va: int) -> dict:
        header = self.by_name['.eh_frame_hdr']
        if self.raw[header.offset:header.offset + 4] != b'\x01\x1b\x03\x3b':
            raise ValueError('unsupported eh_frame_hdr encoding')
        count = struct.unpack_from('<I', self.raw, header.offset + 8)[0]
        if 12 + count * 8 != header.size:
            raise ValueError('eh_frame_hdr table bounds mismatch')
        table = [(header.va + pc, header.va + fde) for pc, fde in
                 struct.iter_unpack('<ii', self.raw[header.offset + 12:header.offset + header.size])]
        starts = [pc for pc, _ in table]
        if starts != sorted(set(starts)):
            raise ValueError('eh_frame_hdr starts are not unique and sorted')
        index = bisect.bisect_right(starts, va) - 1
        if index < 0:
            raise ValueError('no FDE for address')
        start, fde = table[index]
        length, cie_pointer, relative, size = struct.unpack('<IIiI', self.at(fde, 16))
        # These FDEs use DW_EH_PE_pcrel|sdata4. Pin and verify their CIE too.
        cie = fde + 4 - cie_pointer
        cie_data = self.at(cie, struct.unpack('<I', self.at(cie, 4))[0] + 4)
        if cie_data != bytes.fromhex('1000000000000000017a5200017c1e011b0c1f00'):
            raise ValueError('unsupported pinned CIE encoding')
        if length < 12 or fde + 8 + relative != start or not start <= va < start + size:
            raise ValueError('FDE function bounds do not match table')
        code = self.at(start, size)
        return {'va': start, 'file_offset': self.offset(start, size), 'size': size,
                'sha256': hashlib.sha256(code).hexdigest(), 'fde_va': fde,
                'cie_va': cie, 'cie_hex': cie_data.hex()}
