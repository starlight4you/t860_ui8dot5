"""Generic size-preserving DEX 041/stored-JAR helpers.

Extracted from the reviewed old-project parser; contains no KG/ICCC/CE patches.
Provenance: t860-ui8/scripts/patch-services-jar-v0.15-knox-iccc.py
Source SHA256: d94fc4fe80a30afcb7e54ae5e600d85f02a570518f5ab8f789fae3ba2480987c
"""
from __future__ import annotations
import hashlib
import struct
import zlib
from dataclasses import dataclass

def fail(message: str) -> "None":
    raise ValueError(message)


def u16(data: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def u32(data: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def put_u16(data: bytearray, off: int, value: int) -> None:
    struct.pack_into("<H", data, off, value)


def put_u32(data: bytearray, off: int, value: int) -> None:
    struct.pack_into("<I", data, off, value)


def read_uleb(data: bytes | bytearray, off: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 35, 7):
        byte = data[off]
        off += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, off
    fail("invalid ULEB128")


def decode_mutf8(raw: bytes) -> str:
    """Decode DEX string_data_item modified UTF-8 into a Python string."""
    units: list[int] = []
    off = 0
    while off < len(raw):
        first = raw[off]
        off += 1
        if first < 0x80:
            units.append(first)
            continue
        if first & 0xE0 == 0xC0:
            if off >= len(raw):
                fail("truncated two-byte MUTF-8 sequence")
            second = raw[off]
            off += 1
            if second & 0xC0 != 0x80:
                fail("invalid two-byte MUTF-8 continuation")
            units.append(((first & 0x1F) << 6) | (second & 0x3F))
            continue
        if first & 0xF0 == 0xE0:
            if off + 1 >= len(raw):
                fail("truncated three-byte MUTF-8 sequence")
            second, third = raw[off], raw[off + 1]
            off += 2
            if second & 0xC0 != 0x80 or third & 0xC0 != 0x80:
                fail("invalid three-byte MUTF-8 continuation")
            units.append(
                ((first & 0x0F) << 12) | ((second & 0x3F) << 6) | (third & 0x3F)
            )
            continue
        fail(f"invalid MUTF-8 lead byte 0x{first:02x}")
    encoded = b"".join(struct.pack("<H", unit) for unit in units)
    return encoded.decode("utf-16-le", errors="surrogatepass")


@dataclass(frozen=True)
class Method:
    section: "DexSection"
    method_idx: int
    class_desc: str
    name: str
    descriptor: str
    access_flags: int
    code_off: int

    @property
    def registers_size(self) -> int:
        return u16(self.section.data, self.code_off)

    @property
    def tries_size(self) -> int:
        return u16(self.section.data, self.code_off + 6)

    @property
    def insns_size(self) -> int:
        return u32(self.section.data, self.code_off + 12)

    @property
    def insns_off(self) -> int:
        return self.code_off + 16

    def units(self) -> list[int]:
        return [u16(self.section.data, self.insns_off + i * 2) for i in range(self.insns_size)]

    def label(self) -> str:
        return f"{self.class_desc}->{self.name}{self.descriptor}"


class DexSection:
    def __init__(self, data: bytearray, base: int, index: int):
        self.data = data
        self.base = base
        self.index = index
        if data[base : base + 8] != b"dex\n041\0":
            fail(f"logical DEX {index} is not dex 041 at 0x{base:x}")
        self.file_size = u32(data, base + 0x20)
        if self.file_size < 0x78:
            fail(f"logical DEX {index} has invalid file size")
        self.header_size = u32(data, base + 0x24)
        self.container_size = u32(data, base + 0x70)
        self.header_offset = u32(data, base + 0x74)
        if self.header_size != 0x78:
            fail(f"logical DEX {index} header size is 0x{self.header_size:x}, expected 0x78")
        if self.header_offset != base:
            fail(
                f"logical DEX {index} header_offset is 0x{self.header_offset:x}, "
                f"expected 0x{base:x}"
            )
        if base + self.file_size > len(data):
            fail(f"logical DEX {index} exceeds container")

        self.string_count = u32(data, base + 0x38)
        self.string_off = u32(data, base + 0x3C)
        self.type_count = u32(data, base + 0x40)
        self.type_off = u32(data, base + 0x44)
        self.proto_count = u32(data, base + 0x48)
        self.proto_off = u32(data, base + 0x4C)
        self.method_count = u32(data, base + 0x58)
        self.method_off = u32(data, base + 0x5C)
        self.field_count = u32(data, base + 0x50)
        self.field_off = u32(data, base + 0x54)
        self.class_count = u32(data, base + 0x60)
        self.class_off = u32(data, base + 0x64)
        self._strings: dict[int, str] = {}
        self._types: dict[int, str] = {}
        self._protos: dict[int, str] = {}
        self._methods_by_class: dict[str, list[Method]] = {}

    def string(self, index: int) -> str:
        if not 0 <= index < self.string_count:
            fail(f"DEX {self.index}: string index {index} out of range")
        if index not in self._strings:
            off = u32(self.data, self.string_off + index * 4)
            _utf16_size, off = read_uleb(self.data, off)
            end = self.data.index(0, off)
            raw = bytes(self.data[off:end])
            self._strings[index] = decode_mutf8(raw)
        return self._strings[index]

    def type(self, index: int) -> str:
        if not 0 <= index < self.type_count:
            fail(f"DEX {self.index}: type index {index} out of range")
        if index not in self._types:
            self._types[index] = self.string(u32(self.data, self.type_off + index * 4))
        return self._types[index]

    def type_index(self, descriptor: str) -> int:
        matches = [i for i in range(self.type_count) if self.type(i) == descriptor]
        if len(matches) != 1:
            fail(f"DEX {self.index}: expected one type {descriptor}, found {len(matches)}")
        return matches[0]

    def string_index(self, value: str) -> int:
        matches = [i for i in range(self.string_count) if self.string(i) == value]
        if len(matches) != 1:
            fail(f"DEX {self.index}: expected one string {value!r}, found {len(matches)}")
        return matches[0]

    def proto(self, index: int) -> str:
        if not 0 <= index < self.proto_count:
            fail(f"DEX {self.index}: proto index {index} out of range")
        if index not in self._protos:
            off = self.proto_off + index * 12
            return_type = self.type(u32(self.data, off + 4))
            params_off = u32(self.data, off + 8)
            params: list[str] = []
            if params_off:
                size = u32(self.data, params_off)
                params = [self.type(u16(self.data, params_off + 4 + i * 2)) for i in range(size)]
            self._protos[index] = "(" + "".join(params) + ")" + return_type
        return self._protos[index]

    def method_id(self, index: int) -> tuple[str, str, str]:
        if not 0 <= index < self.method_count:
            fail(f"DEX {self.index}: method index {index} out of range")
        off = self.method_off + index * 8
        return (
            self.type(u16(self.data, off)),
            self.string(u32(self.data, off + 4)),
            self.proto(u16(self.data, off + 2)),
        )

    def field_id(self, index: int) -> tuple[str, str, str]:
        if not 0 <= index < self.field_count:
            fail(f"DEX {self.index}: field index {index} out of range")
        off = self.field_off + index * 8
        return (self.type(u16(self.data, off)), self.string(u32(self.data, off + 4)),
                self.type(u16(self.data, off + 2)))

    def _parse_class_data(self, class_desc: str, class_data_off: int) -> list[Method]:
        off = class_data_off
        static_count, off = read_uleb(self.data, off)
        instance_count, off = read_uleb(self.data, off)
        direct_count, off = read_uleb(self.data, off)
        virtual_count, off = read_uleb(self.data, off)
        for _ in range(static_count + instance_count):
            _field_diff, off = read_uleb(self.data, off)
            _access, off = read_uleb(self.data, off)

        methods: list[Method] = []
        for count in (direct_count, virtual_count):
            method_idx = 0
            for _ in range(count):
                diff, off = read_uleb(self.data, off)
                method_idx += diff
                access, off = read_uleb(self.data, off)
                code_off, off = read_uleb(self.data, off)
                owner, name, descriptor = self.method_id(method_idx)
                if owner != class_desc:
                    fail(
                        f"DEX {self.index}: class_data owner mismatch for method {method_idx}: "
                        f"{owner} != {class_desc}"
                    )
                methods.append(
                    Method(self, method_idx, owner, name, descriptor, access, code_off)
                )
        return methods

    def methods_for_class(self, descriptor: str) -> list[Method]:
        if descriptor in self._methods_by_class:
            return self._methods_by_class[descriptor]
        matches: list[list[Method]] = []
        for i in range(self.class_count):
            off = self.class_off + i * 32
            if self.type(u32(self.data, off)) != descriptor:
                continue
            class_data_off = u32(self.data, off + 24)
            if not class_data_off:
                fail(f"DEX {self.index}: {descriptor} has no class_data")
            matches.append(self._parse_class_data(descriptor, class_data_off))
        if len(matches) > 1:
            fail(f"DEX {self.index}: duplicate class {descriptor}")
        result = matches[0] if matches else []
        self._methods_by_class[descriptor] = result
        return result

    def method(self, class_desc: str, name: str, descriptor: str) -> Method | None:
        matches = [
            method
            for method in self.methods_for_class(class_desc)
            if method.name == name and method.descriptor == descriptor
        ]
        if len(matches) > 1:
            fail(f"DEX {self.index}: duplicate method {class_desc}->{name}{descriptor}")
        return matches[0] if matches else None

    def update_signature_and_checksum(self) -> None:
        start = self.base
        end = start + self.file_size
        signature = hashlib.sha1(self.data[start + 32 : end]).digest()
        self.data[start + 12 : start + 32] = signature
        checksum = zlib.adler32(self.data[start + 12 : end]) & 0xFFFFFFFF
        put_u32(self.data, start + 8, checksum)

    def verify_signature_and_checksum(self) -> None:
        start = self.base
        end = start + self.file_size
        expected_signature = hashlib.sha1(self.data[start + 32 : end]).digest()
        if bytes(self.data[start + 12 : start + 32]) != expected_signature:
            fail(f"DEX {self.index}: SHA-1 signature mismatch")
        expected_checksum = zlib.adler32(self.data[start + 12 : end]) & 0xFFFFFFFF
        if u32(self.data, start + 8) != expected_checksum:
            fail(f"DEX {self.index}: Adler32 checksum mismatch")


class DexContainer:
    def __init__(self, payload: bytes):
        self.data = bytearray(payload)
        self.sections: list[DexSection] = []
        base = 0
        while base < len(self.data):
            section = DexSection(self.data, base, len(self.sections))
            self.sections.append(section)
            base += section.file_size
        if base != len(self.data):
            fail(f"logical DEX sections end at {base}, container is {len(self.data)} bytes")
        if len(self.sections) != 2:
            fail(f"expected two logical DEX files, found {len(self.sections)}")
        for section in self.sections:
            if section.container_size != len(self.data):
                fail(
                    f"DEX {section.index}: container_size {section.container_size} "
                    f"!= {len(self.data)}"
                )
            section.verify_signature_and_checksum()

    def find_method(self, class_desc: str, name: str, descriptor: str) -> Method:
        matches = [
            method
            for section in self.sections
            if (method := section.method(class_desc, name, descriptor)) is not None
        ]
        if len(matches) != 1:
            fail(f"expected one method {class_desc}->{name}{descriptor}, found {len(matches)}")
        method = matches[0]
        if not method.code_off:
            fail(f"target method has no code: {method.label()}")
        return method



@dataclass(frozen=True)
class StoredZipMember:
    name: str
    local_off: int
    data_off: int
    size: int
    local_crc_off: int
    central_crc_off: int
    crc: int


def find_stored_member(jar: bytes | bytearray, target: str) -> StoredZipMember:
    eocd = bytes(jar).rfind(b"PK\x05\x06")
    if eocd < 0 or eocd + 22 > len(jar):
        fail("ZIP end-of-central-directory not found")
    entries = u16(jar, eocd + 10)
    central_size = u32(jar, eocd + 12)
    central_off = u32(jar, eocd + 16)
    if central_off + central_size != eocd:
        fail("unexpected ZIP central-directory placement")

    off = central_off
    matches: list[StoredZipMember] = []
    for _ in range(entries):
        if jar[off : off + 4] != b"PK\x01\x02":
            fail(f"invalid ZIP central header at 0x{off:x}")
        flags = u16(jar, off + 8)
        method = u16(jar, off + 10)
        crc = u32(jar, off + 16)
        compressed = u32(jar, off + 20)
        uncompressed = u32(jar, off + 24)
        name_len = u16(jar, off + 28)
        extra_len = u16(jar, off + 30)
        comment_len = u16(jar, off + 32)
        local_off = u32(jar, off + 42)
        name = bytes(jar[off + 46 : off + 46 + name_len]).decode("utf-8")
        if name == target:
            if flags & 0x08:
                fail(f"{target} unexpectedly uses a data descriptor")
            if method != 0 or compressed != uncompressed:
                fail(f"{target} must be a stored, size-preserving member")
            if jar[local_off : local_off + 4] != b"PK\x03\x04":
                fail(f"invalid local header for {target}")
            local_name_len = u16(jar, local_off + 26)
            local_extra_len = u16(jar, local_off + 28)
            local_name = bytes(
                jar[local_off + 30 : local_off + 30 + local_name_len]
            ).decode("utf-8")
            if local_name != target:
                fail(f"local/central name mismatch for {target}")
            data_off = local_off + 30 + local_name_len + local_extra_len
            matches.append(
                StoredZipMember(
                    target,
                    local_off,
                    data_off,
                    uncompressed,
                    local_off + 14,
                    off + 16,
                    crc,
                )
            )
        off += 46 + name_len + extra_len + comment_len
    if off != eocd:
        fail("ZIP central-directory length mismatch")
    if len(matches) != 1:
        fail(f"expected one ZIP member {target}, found {len(matches)}")
    return matches[0]
