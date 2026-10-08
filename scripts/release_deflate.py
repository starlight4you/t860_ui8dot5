"""Pinned standard DEFLATE payload encoding; no image or ZIP64 mutation."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile
import zlib

OPTIONS = ['-tzip', '-mm=Deflate', '-mx=9', '-mfb=258', '-mpass=1', '-mmt=1']

def encoder():
    program = os.environ.get('RELEASE_7ZZ', '7zz')
    banner = subprocess.check_output([program, 'i'], text=True)
    if '7-Zip (z) 26.01 ' not in banner:
        raise ValueError('The release payload encoder requires 7-Zip 26.01')
    return program

def compress(raw, program):
    with tempfile.TemporaryDirectory(prefix='release-deflate-') as folder:
        root = Path(folder)
        (root / 'chunk').write_bytes(raw)
        output = root / 'encoded.zip'
        subprocess.run([program, 'a', *OPTIONS, str(output), 'chunk'], cwd=root,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        with zipfile.ZipFile(output) as archive:
            infos = archive.infolist()
            if len(infos) != 1:
                raise ValueError('Unexpected encoder inventory')
            info = infos[0]
            if (info.compress_type != zipfile.ZIP_DEFLATED or info.file_size != len(raw)
                    or info.CRC != zlib.crc32(raw) or info.flag_bits & 1):
                raise ValueError('Unexpected DEFLATE encoding')
            with output.open('rb') as stream:
                stream.seek(info.header_offset)
                header = stream.read(30)
                if header[:4] != b'PK\x03\x04':
                    raise ValueError('Missing local ZIP header')
                name_size, extra_size = struct.unpack_from('<HH', header, 26)
                stream.seek(name_size + extra_size, 1)
                encoded = stream.read(info.compress_size)
        if zlib.decompress(encoded, -15) != raw:
            raise ValueError('Standard DEFLATE round trip differs')
        return encoded

def chunks(path, chunk_bytes, workers=4):
    """Bounded parallel encoding; at most four raw blocks retained."""
    program = encoder()
    def job(offset):
        with path.open('rb') as stream:
            stream.seek(offset)
            raw = stream.read(chunk_bytes)
        return offset // chunk_bytes, raw, compress(raw, program)
    offsets = iter(range(0, path.stat().st_size, chunk_bytes))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = deque()
        for _ in range(workers):
            offset = next(offsets, None)
            if offset is not None: pending.append(pool.submit(job, offset))
        while pending:
            yield pending.popleft().result()
            offset = next(offsets, None)
            if offset is not None: pending.append(pool.submit(job, offset))

class Prepared:
    # A module-level class avoids class/method closure cycles retaining every
    # 64 MiB block until a delayed cyclic-GC pass on Python 3.14.
    def __init__(self, raw, encoded):
        self.raw, self.encoded = raw, encoded
    def compress(self, data):
        if data != self.raw: raise ValueError('Prepared input differs')
        return self.encoded
    def flush(self): return b''

def write(archive, info, raw, encoded):
    """Let zipfile compute headers/CRC/ZIP32 bounds over a verified raw block."""
    original = zipfile._get_compressor
    def factory(method, level=None):
        if method != zipfile.ZIP_DEFLATED: raise ValueError('Only DEFLATE permitted')
        return Prepared(raw, encoded)
    zipfile._get_compressor = factory
    try:
        archive.writestr(info, raw)
        if archive.getinfo(info.filename).compress_size != len(encoded):
            raise ValueError('Prepared stream size differs')
    finally:
        zipfile._get_compressor = original
