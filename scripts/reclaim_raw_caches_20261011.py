"""Read-only raw/Android-sparse reader used by the A111 Odin recipe."""
import bisect,hashlib,struct
BLOCK=8*1024**2
SPARSE=0xED26FF3A

class Image:
    """Bounded random reader for raw or Android sparse images."""
    def __init__(self, path):
        self.stream = path.open('rb')
        self.file_size = path.stat().st_size
        header = self.stream.read(28)
        self.chunks = []
        if len(header) < 4 or struct.unpack_from('<I', header)[0] != SPARSE:
            self.size = self.file_size
            self.chunks = [(0, self.size, 0xCAC1, 0)]
        else:
            if len(header) != 28:
                raise ValueError('Truncated sparse header')
            _, major, _, file_h, chunk_h, block, blocks, count, _ = struct.unpack('<IHHHHIIII', header)
            if major != 1 or file_h < 28 or chunk_h < 12 or not block or block % 4:
                raise ValueError('Unsupported sparse format')
            self.size = blocks * block
            self.stream.seek(file_h)
            expanded = 0
            for _ in range(count):
                head = self.stream.read(chunk_h)
                if len(head) != chunk_h:
                    raise ValueError('Truncated sparse chunk')
                kind, _, nblocks, total = struct.unpack_from('<HHII', head)
                payload = total - chunk_h
                length = nblocks * block
                at = self.stream.tell()
                if total < chunk_h or at + payload > self.file_size:
                    raise ValueError('Sparse chunk outside source')
                if kind == 0xCAC1 and payload == length:
                    value = at
                elif kind == 0xCAC2 and payload == 4:
                    value = self.stream.read(4)
                elif kind == 0xCAC3 and payload == 0:
                    value = None
                elif kind == 0xCAC4 and payload == 4 and length == 0:
                    self.stream.seek(at + payload)
                    continue
                else:
                    raise ValueError('Unsupported or malformed sparse chunk')
                if length:
                    self.chunks.append((expanded, length, kind, value))
                expanded += length
                self.stream.seek(at + payload)
            if expanded != self.size or self.stream.tell() != self.file_size:
                raise ValueError('Sparse size or trailing bytes differ')
        self.starts = [c[0] for c in self.chunks]

    def readat(self, offset, length):
        if offset < 0 or length < 0 or offset + length > self.size:
            raise ValueError('Read outside image')
        result = []
        while length:
            idx = bisect.bisect_right(self.starts, offset) - 1
            start, size, kind, value = self.chunks[idx]
            within = offset - start
            n = min(length, size - within)
            if n <= 0:
                raise ValueError('Sparse gap')
            if kind == 0xCAC1:
                self.stream.seek(value + within)
                b = self.stream.read(n)
                if len(b) != n:
                    raise ValueError('Truncated raw data')
            elif kind == 0xCAC2:
                shift = within % 4
                b = (value * ((n + shift + 3) // 4))[shift:shift + n]
            else:
                b = bytes(n)
            result.append(b)
            offset += n
            length -= n
        return b''.join(result)

    def extents(self, part):
        if part is None:
            return [(self.size, 0)]
        prefix = self.readat(0, min(4 * 1024**2, self.size))
        base = prefix.find(struct.pack('<I', 0x414C5030))
        if base < 0:
            raise ValueError('No liblp metadata')
        magic, major, minor, header_size = struct.unpack_from('<IHHI', prefix, base)
        if major > 10 or header_size < 128 or base + header_size > len(prefix):
            raise ValueError('Unsupported liblp header')
        header = bytearray(prefix[base:base + header_size])
        expected_header = bytes(header[12:44])
        header[12:44] = bytes(32)
        if hashlib.sha256(header).digest() != expected_header:
            raise ValueError('liblp header checksum differs')
        table_size = struct.unpack_from('<I', header, 44)[0]
        table_start = base + header_size
        if table_start + table_size > len(prefix):
            raise ValueError('liblp tables outside prefix')
        tables = prefix[table_start:table_start + table_size]
        if hashlib.sha256(tables).digest() != bytes(header[48:80]):
            raise ValueError('liblp tables checksum differs')
        po, pc, ps = struct.unpack_from('<III', header, 80)
        eo, ec, es = struct.unpack_from('<III', header, 92)
        if ps < 52 or es < 24 or po + pc * ps > len(tables) or eo + ec * es > len(tables):
            raise ValueError('Malformed liblp descriptors')
        entries = [struct.unpack_from('<QIQI', tables, eo + i * es) for i in range(ec)]
        for i in range(pc):
            entry = tables[po + i * ps:po + (i + 1) * ps]
            name = entry[:36].split(b'\0', 1)[0].decode()
            if name != part:
                continue
            _, first, count, _ = struct.unpack_from('<IIII', entry, 36)
            if first + count > ec:
                raise ValueError('Partition extents outside table')
            result = []
            for sectors, kind, data, source in entries[first:first + count]:
                if kind == 0 and source == 0 and data * 512 + sectors * 512 <= self.size:
                    result.append((sectors * 512, data * 512))
                elif kind == 1:
                    result.append((sectors * 512, None))
                else:
                    raise ValueError('Unsupported liblp extent')
            return result
        raise ValueError('Partition not found: ' + part)

    def blocks(self, part):
        for length, start in self.extents(part):
            at = 0
            while at < length:
                size = min(BLOCK, length - at)
                yield bytes(size) if start is None else self.readat(start + at, size)
                at += size

    def close(self):
        self.stream.close()
