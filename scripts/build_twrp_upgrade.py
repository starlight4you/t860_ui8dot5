#!/usr/bin/env python3
"""Build a TWRP SYSTEM/PRODUCT upgrade ZIP from audited UI8.5 raw ext4 images.

Capacity probes are not ROM inputs. Filesystem, identity, VNDK30 and physical
layout checks are run here; boot/dirty-upgrade runtime remains a separate gate.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
CHUNK_BYTES = 64 * 1024 * 1024
SIZES = {'system': 6534725632, 'product': 1048576000}
MIN_FREE = {'system': 256 * 1024 * 1024, 'product': 100 * 1024 * 1024}
PROFILE = ROOT / 'device/s6/twrp-upgrade-ui85.json'
FIXED_TIME = (2008, 1, 1, 0, 0, 0)
ZIP32_LIMIT = 2**32 - 1


@contextmanager
def zip32_archive(path: Path):
    # Python conservatively emits ZIP64 above 2 GiB; pinned TWRP unzip rejects
    # ZIP64. This single-threaded builder uses the actual unsigned ZIP32 limit
    # and rejects files/offsets beyond it. Restore the module limit for callers.
    previous_limit = zipfile.ZIP64_LIMIT
    zipfile.ZIP64_LIMIT = ZIP32_LIMIT
    try:
        with ZipFile(path, 'w', compression=ZIP_DEFLATED, compresslevel=6,
                     allowZip64=False) as archive:
            yield archive
    finally:
        zipfile.ZIP64_LIMIT = previous_limit


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def command(*args: str) -> str:
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(f'{args[0]} failed ({result.returncode}): {result.stderr[-2000:]}')
    return result.stdout


def properties(text: str, identical_duplicates: list | None = None) -> dict[str, str]:
    output = {}
    for line in text.splitlines():
        if line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key in output:
            if output[key] != value:
                raise ValueError(f'conflicting duplicate property: {key}')
            # The untouched Samsung donor repeats ro.kernel.qemu=0. Identical
            # assignments have one unambiguous value; keep the donor intact.
            if identical_duplicates is not None:
                identical_duplicates.append({'key': key, 'value': value})
        output[key] = value
    return output


def image_audit(name: str, path: Path, wanted_sha: str) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size != SIZES[name]:
        raise ValueError(f'{name}: requires exact-size regular raw image')
    with path.open('rb') as stream:
        stream.seek(1080)
        if stream.read(2) != b'\x53\xef':
            raise ValueError(f'{name}: raw ext4 required, sparse/EROFS not accepted')
    print(f'Auditing {name} filesystem and SHA...', flush=True)
    actual_sha = sha_file(path)
    if actual_sha != wanted_sha:
        raise ValueError(f'{name}: input SHA does not match ROM manifest')
    fsck = subprocess.run(['e2fsck', '-fn', str(path)], text=True, capture_output=True)
    if fsck.returncode:
        raise ValueError(f'{name}: e2fsck failed ({fsck.returncode})')
    header = command('dumpe2fs', '-h', str(path))
    fields = dict(line.split(':', 1) for line in header.splitlines() if ':' in line)
    blocks = int(fields['Block count'])
    block_size = int(fields['Block size'])
    free = (int(fields['Free blocks']) - int(fields['Reserved block count'])) * block_size
    if block_size != 4096 or blocks * block_size != SIZES[name] or free < MIN_FREE[name]:
        raise ValueError(f'{name}: physical layout/free-space gate failed (free={free})')
    features = fields['Filesystem features'].split()
    forbidden = {'64bit', 'metadata_csum', 'metadata_csum_seed', 'orphan_file', 'bigalloc'}
    if forbidden.intersection(features):
        raise ValueError(f'{name}: unvalidated T860 ext4 features: {forbidden.intersection(features)}')
    return {'bytes': path.stat().st_size, 'sha256': actual_sha, 'free_bytes': free,
            'minimum_free_bytes': MIN_FREE[name], 'ext4_features': features,
            'e2fsck_exit': fsck.returncode, 'e2fsck_log': fsck.stdout + fsck.stderr}


def check_device_layer(system: Path) -> dict:
    duplicates = []
    build = properties(command('debugfs', '-R', 'cat /system/build.prop', str(system)), duplicates)
    wanted = {'ro.product.system.model': 'SM-T860',
              'ro.build.version.sdk': '36', 'ro.build.version.oneui': '80500',
              'ro.build.version.incremental': 'X710XXS6EZH3'}
    for key, value in wanted.items():
        if build.get(key) != value:
            raise ValueError(f'target identity missing/mismatched: {key}')
    if 'ro.product.model' in build and build['ro.product.model'] != 'SM-T860':
        raise ValueError('conflicting global model property')
    b04 = json.loads((ROOT / 'device/s6/vndk30-ui85.json').read_text())
    checks = {'/system_ext/apex/com.android.vndk.v30.apex': b04['apex_sha256'],
              '/system_ext/etc/selinux/mapping/30.0.cil': b04['mapping_output_sha256']}
    with tempfile.TemporaryDirectory(prefix='t860-ui85-package-audit-') as temporary:
        for index, (source, wanted_sha) in enumerate(checks.items()):
            destination = Path(temporary) / f'extract-{index}'
            # Temp paths have no whitespace; debugfs does not use shell quoting.
            command('debugfs', '-R', f'dump {source} {destination}', str(system))
            if not destination.is_file() or sha_file(destination) != wanted_sha:
                raise ValueError(f'B04 content missing/mismatched: {source}')
    return {'target_properties': wanted, 'b04_checked_files': checks,
            'identical_duplicate_properties': duplicates}


def zip_entry(name: str, executable: bool = False) -> ZipInfo:
    info = ZipInfo(name, date_time=FIXED_TIME)
    info.create_system = 3
    info.external_attr = (0o100755 if executable else 0o100644) << 16
    info.compress_type = ZIP_DEFLATED
    return info


def a71_support(manifest: dict, operation: str = 'upgrade') -> tuple[bytes, dict[str, bytes], dict | None]:
    if operation not in ('upgrade', 'restore-a70'):
        raise ValueError('unsupported installer operation')
    common = (ROOT / 'installer/libupgrade.sh').read_bytes()
    candidate = manifest.get('candidate_id', '')
    if not candidate.startswith('A71') and 'vendor_adaptation' not in manifest and operation == 'upgrade':
        return common, {}, None
    profile = json.loads((ROOT / 'device/s6/twrp-installer-a71.json').read_text())
    if (candidate != 'A71-X710-EZH3-T860-UI85-REPAIRED'
            or profile['candidate_id'] != candidate
            or profile['id'] != 'A71_INSTALLER_SUPPORT_V2'
            or manifest['source_inventory_sha256' if operation == 'upgrade' else 'support_stage_reference_sha256'] != profile['source_inventory_sha256']
            or profile['source_system_raw_sha256'] != json.loads(PROFILE.read_text())['source_system_raw_sha256']
            or profile['mainline_policy'] != 'REFUSE_ALL_UNVERIFIED_ACTIVE_APEX_OR_STAGED_SESSIONS'):
        raise ValueError('A71 support/source identity mismatch; re-audit required')
    wanted = {
        'vendor-guard': (2693984, 'eb740a25e0e70f2304656fc5e6b6ddc9e269bd07b3fcf3de58026cf629ee89e4'),
        'mainline-guard': (2237192, '402e84d1c6e60087db2c78ab6869581e51dd3bdf7a5adcca3a521d57dd7b4081'),
        'vendor-before-policy': (1869, 'e529d80729976c2ef41f6831820da5f387b7cdbd44f8b1b33d0e7cf9cd1462b8'),
        'vendor-after-policy': (1882, 'efae1217c1fd598fb80f390a510c857d7adc3ff8018dc3a2571c7d32e7e3bfcc'),
        'apex-factory.tsv': (1349, '3db9c6be68d3310e1cad7af3848a675dfef9a225504ad93c830e3ecbffb3c02a'),
    }
    if set(profile['support']) != set(wanted):
        raise ValueError('unexpected A71 support members')
    snapshot = profile['audited_source_snapshot']
    snapshot_file = ROOT / snapshot['report']
    if (snapshot['report'] != 'docs/audit/live-twrp-readonly-preflight-a46.json'
            or snapshot['report_sha256'] != '5d5eeefa088a9b3c15c7c084fe3bb07f24bbf1faebbbf549f7248ba7ccb30cfb'
            or sha_file(snapshot_file) != snapshot['report_sha256']
            or snapshot['system_sha256'] != 'b086ec97a5180832b033934e8fe2ac7c5972feec38580e7bb8b244526105dab3'
            or json.loads(snapshot_file.read_text())['partitions']['system']['sha256'] != snapshot['system_sha256']):
        raise ValueError('A46 audited source snapshot identity changed')
    experimental = profile['audited_experimental_source']
    wanted_reports = {
        'current-stable-source-readonly-ui85-a71.json': '1a8d508713d9258ea9ea929e9971e62e1e96492456ab31d392cb62393e5361a8',
        'current-stable-source-vs-stage-ui85-a71.json': '5a50a0b9c19e6fc6855b3e3995c84cef61bb3d1e5ef8dcc23e39b70b892a17d1',
        'current-stable-source-fsck-ui85-a71.json': 'fcd1f9bd9e9726bbc13e96285ed0594dc6e928f2077144c7bf6ffd0751936e54',
        'twrp-real-readonly-guards-ui85-a71.json': 'ca047b7f7cd1cb8ed8ec715a871c6b3e1f998b96397fba1c8da5d8abc0533cd9',
    }
    if (experimental['reports'] != wanted_reports
            or experimental['system_sha256'] != '226ac43e6d2bb9b504c1459ee074a31eb7f0ea752772793d099e6f1c9db1817b'
            or experimental['product_sha256'] != '3131ac9d1d7080731952d47d7abb11ee2feaeb63a3446858313917caaf1e4b29'):
        raise ValueError('experimental source scope changed')
    for name, digest in wanted_reports.items():
        if sha_file(ROOT / 'docs/audit' / name) != digest:
            raise ValueError('experimental source evidence changed: ' + name)
    payloads = {}
    rows = []
    for name, (size, digest) in wanted.items():
        row = profile['support'][name]
        source = ROOT / row['path']
        if (source.is_symlink() or not source.is_file()
                or source.resolve().parent != (ROOT / 'device/s6/prebuilts/installer-a71').resolve()
                or row['bytes'] != size or row['sha256'] != digest):
            raise ValueError('unsupported Recovery payload path/identity: ' + name)
        data = source.read_bytes()
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Recovery payload content changed: ' + name)
        payloads[name] = data
        rows.append(f'{name}\t{size}\t{digest}')
    fragment = (ROOT / 'installer/libupgrade-a71.sh').read_text()
    replacements = {'@@SOURCE_SYSTEM_SHA@@': profile['source_system_raw_sha256'],
                    '@@SOURCE_A46_SHA@@': snapshot['system_sha256'],
                    '@@SOURCE_A70_SHA@@': experimental['system_sha256'],
                    '@@SUPPORT_ROWS@@': '\n'.join(rows)}
    for marker, value in replacements.items():
        if fragment.count(marker) != 1:
            raise ValueError('missing/duplicate A71 library marker: ' + marker)
        fragment = fragment.replace(marker, value)
    if '@@' in fragment:
        raise ValueError('unresolved A71 library marker')
    if operation == 'restore-a70':
        if fragment.count('\nupgrade_main() {') != 1:
            raise ValueError('A71 transaction entry is ambiguous')
        fragment = fragment.replace('\nupgrade_main() {', '\na71_upgrade_transaction() {')
        restore = (ROOT / 'installer/librestore-a70.sh').read_text()
        for part in ('system', 'product'):
            marker = '@@RESTORE_' + part.upper() + '_SHA@@'
            if restore.count(marker) != 1:
                raise ValueError('missing/duplicate restore SHA marker')
            restore = restore.replace(marker, experimental[part + '_sha256'])
        if '@@' in restore:
            raise ValueError('unresolved restore SHA marker')
        fragment += '\n' + restore
    library = common + b'\n' + (ROOT / 'installer/libvendor.sh').read_bytes() + b'\n' + fragment.encode()
    return library, payloads, profile


def write_package(output: Path, images: dict[str, Path], manifest: dict,
                  audits: dict, chunk_bytes: int = CHUNK_BYTES, operation: str = 'upgrade',
                  support_provider=None) -> dict:
    """Writer also used with small file fixtures; production CLI uses 64 MiB."""
    if output.exists() or output.with_suffix('.zip.partial').exists():
        raise ValueError('output already exists')
    if chunk_bytes % 4096:
        raise ValueError('chunk size must be block-aligned')
    library, support, adaptation_profile = (support_provider or a71_support)(manifest, operation)
    library_sha = hashlib.sha256(library).hexdigest()
    installer = (ROOT / 'installer/update-binary').read_text()
    if installer.count('@@LIBRARY_SHA@@') != 1:
        raise ValueError('expected one library SHA marker')
    installer = installer.replace('@@LIBRARY_SHA@@', library_sha)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix('.zip.partial')
    tables = {}
    try:
        with zip32_archive(partial) as archive:
            archive.writestr(zip_entry('META-INF/com/google/android/update-binary', True), installer)
            archive.writestr(zip_entry('META-INF/com/google/android/updater-script'),
                             '# Installation uses the bundled TWRP API 3 shell updater.\n')
            archive.writestr(zip_entry('rom/libupgrade.sh'), library)
            for name, data in support.items():
                archive.writestr(zip_entry('rom/support/' + name, name.endswith('guard')), data)
            for part in ('system', 'product'):
                path = images[part]
                rows = []
                digest = hashlib.sha256()
                offset = 0
                with path.open('rb') as stream:
                    while data := stream.read(chunk_bytes):
                        index = len(rows)
                        member = f'payload/{part}/{index:04d}.img'
                        block_sha = hashlib.sha256(data).hexdigest()
                        rows.append((index, offset // 4096, len(data), block_sha, member))
                        archive.writestr(zip_entry(member), data)
                        digest.update(data)
                        offset += len(data)
                if digest.hexdigest() != audits[part]['sha256'] or offset != audits[part]['bytes']:
                    raise ValueError(f'{part}: source image changed during packaging')
                tables[part] = rows
                table = ''.join('\t'.join(map(str, row)) + '\n' for row in rows)
                archive.writestr(zip_entry(f'rom/{part}.chunks'), table)
            config = {'format': '1', 'target': 'SM-T860', 'target_sdk': '36',
                      'target_oneui': '80500', 'donor_build': 'X710XXS6EZH3',
                      'data_policy': 'PRESERVE'}
            if adaptation_profile:
                config['format'] = adaptation_profile.get('format', '2')
                if config['format'] not in ('2', '3'):
                    raise ValueError('unreviewed adaptation format')
                config['adaptation'] = adaptation_profile['adaptation']
            if operation == 'restore-a70':
                config['mode'] = 'A70_STABLE_SNAPSHOT'
            for part in tables:
                config[f'{part}.sha256'] = audits[part]['sha256']
                config[f'{part}.chunk_count'] = str(len(tables[part]))
            archive.writestr(zip_entry('rom/upgrade.tsv'),
                             ''.join(f'{key}\t{value}\n' for key, value in config.items()))
            embedded = {'rom_manifest': manifest, 'image_audits': audits,
                        'profile': json.loads(PROFILE.read_text()), 'chunk_bytes': chunk_bytes,
                        'dirty_upgrade_runtime': 'NOT_TESTED', 'hardware_runtime': 'NOT_TESTED',
                        'installer_library_sha256': library_sha}
            embedded['operation'] = operation
            if adaptation_profile:
                embedded['installer_adaptation_profile'] = adaptation_profile
                embedded['support_member_sha256'] = {
                    'rom/support/' + name: hashlib.sha256(data).hexdigest()
                    for name, data in support.items()}
                if support_provider is None:
                    embedded['common_library_sha256'] = sha_file(ROOT / 'installer/libupgrade.sh')
                    embedded['vendor_library_sha256'] = sha_file(ROOT / 'installer/libvendor.sh')
                    embedded['a71_library_template_sha256'] = sha_file(ROOT / 'installer/libupgrade-a71.sh')
                else:
                    embedded['library_sources'] = adaptation_profile['library_sources']
            archive.writestr(zip_entry('rom/manifest.json'), json.dumps(embedded, indent=2) + '\n')
        if partial.stat().st_size > ZIP32_LIMIT:
            raise ValueError('ZIP exceeds pinned TWRP ZIP32 limit; payload/capacity plan required')
        # Check CRC and exact member inventory, not just ZIP central-directory size.
        with ZipFile(partial) as archive:
            failed = archive.testzip()
            if failed:
                raise ValueError(f'ZIP integrity failed: {failed}')
            members = archive.namelist()
            expected = {'META-INF/com/google/android/update-binary',
                        'META-INF/com/google/android/updater-script', 'rom/libupgrade.sh',
                        'rom/system.chunks', 'rom/product.chunks', 'rom/upgrade.tsv', 'rom/manifest.json'}
            expected.update(row[4] for rows in tables.values() for row in rows)
            expected.update('rom/support/' + name for name in support)
            if set(members) != expected or len(members) != len(expected):
                raise ValueError('unexpected or duplicate ZIP entries')
        os.replace(partial, output)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return {'zip_bytes': output.stat().st_size, 'zip_sha256': sha_file(output),
            'chunk_count': {part: len(rows) for part, rows in tables.items()},
            'zip_format': 'ZIP32_NO_ZIP64', 'contains_userdata_payload': False, 'runtime': 'NOT_TESTED',
            'installer_format': adaptation_profile.get('format', '2') if adaptation_profile else '1',
            'installer_library_sha256': library_sha,
            'support_members': sorted('rom/support/' + name for name in support)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom-manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.suffix != '.zip' or args.out.exists() or args.out.with_suffix('.audit.json').exists():
        raise ValueError('requires a new .zip output')
    for tool in ('e2fsck', 'dumpe2fs', 'debugfs'):
        if not shutil.which(tool):
            raise ValueError(f'build requires Linux filesystem tool: {tool}')
    manifest = json.loads(args.rom_manifest.read_text())
    if (manifest.get('schema') != 1 or manifest.get('kind') != 'rom_candidate'
            or manifest.get('target') != 'SM-T860' or manifest.get('donor_build') != 'X710XXS6EZH3'
            or set(manifest.get('partitions', {})) != set(SIZES)):
        raise ValueError('requires a complete X710-based T860 ROM manifest; not a capacity probe')
    profile = json.loads(PROFILE.read_text())
    if {name: value['bytes'] for name, value in profile['partitions'].items()} != SIZES:
        raise ValueError('profile physical sizes mismatch')
    images = {}
    audits = {}
    for name in SIZES:
        entry = manifest['partitions'][name]
        if not re.fullmatch('[0-9a-f]{64}', entry['sha256']):
            raise ValueError('invalid image SHA')
        images[name] = (args.rom_manifest.resolve().parent / entry['path']).resolve(strict=True)
        audits[name] = image_audit(name, images[name], entry['sha256'])
    device_layer = check_device_layer(images['system'])
    result = write_package(args.out, images, manifest, audits)
    result['device_layer'] = device_layer
    result['rom_manifest_sha256'] = sha_file(args.rom_manifest)
    result['profile_sha256'] = sha_file(PROFILE)
    result['builder_sha256'] = sha_file(Path(__file__))
    args.out.with_suffix('.audit.json').write_text(json.dumps(result, indent=2) + '\n')
    args.out.with_suffix('.zip.sha256').write_text(f"{result['zip_sha256']}  {args.out.name}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
