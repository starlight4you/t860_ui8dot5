#!/usr/bin/env python3
"""Integrate cumulative SYSTEM and A107v2 VENDOR into the verified A109 Odin AP.

Run on the host after the image-conversion VM stops. This avoids VirtioFS
retaining deleted round-trip files. All other compressed members are reused.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tarfile
from reclaim_raw_caches_20261011 import Image

BASE = '79826b3b6679c24e967d754b4767a10dfd31c7bff48f2f95bdd72b478f2f6d86'
NAMES = ['boot.img.lz4', 'recovery.img.lz4', 'system.img.ext4.lz4', 'vendor.img.ext4.lz4',
         'product.img.ext4.lz4', 'dtbo.img.lz4', 'vbmeta.img.lz4']


def sha(path, method='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, method).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'source-audit', 'system-sparse', 'closure', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--lz4', default='/opt/homebrew/bin/lz4')
    parser.add_argument('--discard-generated-sparse', action='store_true')
    args = parser.parse_args()
    target = args.out / 'AP_TabS6_OneUI8.5_v1.0.3_A111_Clean_Odin.tar.md5'
    compressed_files = {part: args.out / (part+'.img.ext4.lz4.partial') for part in ['system']}
    if target.exists() or any(p.exists() for p in compressed_files.values()) or sha(args.source) != BASE or args.system_sparse.is_symlink():
        raise ValueError('Exact source and fresh output required')
    original = json.loads(args.source_audit.read_text())
    closure = json.loads(args.closure.read_text())
    if original['sha256'] != BASE or closure['id'] != 'A111_CUMULATIVE_IMAGE_CLOSURE':
        raise ValueError('Wrong provenance')
    new_members = {}
    for part,sparse in [('system',args.system_sparse)]:
        compressed = compressed_files[part]
        reader = Image(sparse)
        h = hashlib.sha256()
        try:
            for block in reader.blocks(None):
                h.update(block)
            if reader.size != closure['partitions'][part]['bytes'] or h.hexdigest() != closure['partitions'][part]['sha256']:
                raise ValueError('Full sparse expansion differs')
        finally:
            reader.close()
        transfer_sha = sha(sparse)
        print(part+': complete sparse expansion matches cumulative image',flush=True)
        with (args.out / ('odin-'+part+'-lz4.txt')).open('wb') as log:
            subprocess.run([args.lz4, '-12', '-B6', '--content-size', '-q', str(sparse), str(compressed)],
                           stderr=log, check=True)
        with compressed.open('rb') as stream:
            header = stream.read(16)
        if (header[:4] != bytes.fromhex('04224d18') or not header[4] & 8
                or struct.unpack_from('<Q', header, 6)[0] != sparse.stat().st_size
                or compressed.stat().st_size >= 2**32):
            raise ValueError('Samsung LZ4 frame/size mismatch')
        process = subprocess.Popen([args.lz4, '-d', '-q', '-c', str(compressed)], stdout=subprocess.PIPE)
        h = hashlib.sha256()
        length = 0
        with process.stdout as stream:
            for block in iter(lambda: stream.read(8 * 1024**2), b''):
                h.update(block)
                length += len(block)
        if process.wait() or h.hexdigest() != transfer_sha or length != sparse.stat().st_size:
            raise ValueError('LZ4 full expansion differs')
        print('Samsung LZ4 full round trip verified', flush=True)
        if args.discard_generated_sparse:
            if sparse.name != part+'.img.ext4.sparse' or sparse.stat().st_nlink != 1:
                raise ValueError('Refuse to discard unexpected sparse input')
            sparse.unlink()
        new_members[part+'.img.ext4.lz4'] = {'compressed': compressed,'raw_sha256':closure['partitions'][part]['sha256'],'transfer_bytes':length,'transfer_sha256':transfer_sha}
    proofs = []
    partial = target.with_suffix('.partial')
    with tarfile.open(args.source, 'r') as src, tarfile.open(partial, 'w', format=tarfile.USTAR_FORMAT) as dst:
        members = src.getmembers()
        if [m.name for m in members] != NAMES or any(not m.isfile() for m in members):
            raise ValueError('Source member list differs')
        for member, baseline in zip(members, original['members']):
            with src.extractfile(member) as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != baseline['lz4_sha256']:
                    raise ValueError('Source member hash differs')
            row = dict(baseline)
            info = tarfile.TarInfo(member.name)
            info.mode = 0o644
            info.uid = info.gid = 0
            info.mtime = 1640995200
            info.uname = info.gname = 'root'
            if member.name in new_members:
                replacement = new_members[member.name]
                compressed = replacement['compressed']
                info.size = compressed.stat().st_size
                with compressed.open('rb') as stream:
                    dst.addfile(info, stream)
                row.update(raw_sha256=replacement['raw_sha256'],transfer_bytes=replacement['transfer_bytes'],
                           transfer_sha256=replacement['transfer_sha256'],lz4_bytes=info.size,
                           lz4_sha256=sha(compressed),roundtrip_pass=True)
            else:
                info.size = member.size
                with src.extractfile(member) as stream:
                    dst.addfile(info, stream)
            proofs.append(row)
    tar_bytes = partial.stat().st_size
    md5 = sha(partial, 'md5')
    footer = (md5 + '  ' + target.name.removesuffix('.md5') + '\n').encode()
    with partial.open('ab') as stream:
        stream.write(footer)
    with partial.open('rb') as stream:
        h = hashlib.md5()
        remaining = tar_bytes
        while remaining:
            block = stream.read(min(8 * 1024**2, remaining))
            if not block:
                raise ValueError('Short TAR')
            h.update(block)
            remaining -= len(block)
        if h.hexdigest() != md5 or stream.read() != footer:
            raise ValueError('MD5 footer readback differs')
    with tarfile.open(partial, 'r') as check:
        if [m.name for m in check.getmembers()] != NAMES:
            raise ValueError('Output member list differs')
        for row in proofs:
            with check.extractfile(row['member']) as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != row['lz4_sha256']:
                    raise ValueError('Output member readback differs')
    partial.rename(target)
    report = {**original, 'version': 'v1.0.3-A111', 'bytes': target.stat().st_size,
              'sha256': sha(target), 'tar_bytes': tar_bytes, 'odin_md5': md5, 'members': proofs,
              'source_archive_sha256': BASE, 'changed_partition_payloads': ['system'],
              'cumulative_change_closure_sha256': sha(args.closure),
              'sparse_expansion_sha256': {p: closure['partitions'][p]['sha256'] for p in ['system','vendor']},
              'all_member_readback_verified': True, 'builder_sha256': sha(Path(__file__))}
    (args.out / 'odin-package-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    with (args.out / 'SHA256SUMS').open('a') as stream:
        stream.write(report['sha256'] + '  ' + target.name + '\n')
    for compressed in compressed_files.values(): compressed.unlink()
    print(json.dumps({k: report[k] for k in ['version', 'bytes', 'sha256', 'changed_partition_payloads']}), flush=True)


if __name__ == '__main__':
    main()
