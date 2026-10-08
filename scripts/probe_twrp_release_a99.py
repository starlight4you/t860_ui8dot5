#!/usr/bin/env python3
"""Run real ZIP tables/all payload preflight with pinned TWRP tools on Linux.

No update-binary execution, partitions, Android device, reboot or DATA access.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('zip', 'recovery-root', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    allowed_prefixes = ('/var/tmp/ui85-a45-package-native-', '/var/tmp/ui85-a71-package-native-', '/var/tmp/ui85-a74-package-native-', '/var/tmp/ui85-a99-package-native-')
    if os.uname().sysname != 'Linux' or os.geteuid() or a.out.exists() or not str(a.out).startswith(allowed_prefixes):
        raise ValueError('Linux root/fresh scoped output required')
    recovery = a.recovery_root.resolve()
    if recovery != Path('/var/tmp/t860-ui85-fixed-twrp-rootfs') or (recovery / 'dev/block').exists():
        raise ValueError('wrong recovery/no block nodes permitted')
    tools = json.loads((recovery / 'tools-manifest.json').read_text())
    if tools['recovery_sha256'] != 'cbc6e03563a9229b7034dd775964ef412af94a7074f50b519ce1ccc1fd4f2e16':
        raise ValueError('recovery basis differs')
    for row in tools['entries']:
        if not row['path'].startswith('sbin/'):
            continue
        f = recovery / row['path']
        if f.is_symlink():
            digest = hashlib.sha256(os.readlink(f).encode()).hexdigest()
        elif f.is_file():
            digest = sha(f)
        elif f.is_dir():
            continue
        else:
            raise ValueError('missing tool: ' + row['path'])
        if digest != row['sha256']:
            raise ValueError('pinned tool changed: ' + row['path'])
    a.out.mkdir()
    zip_sha = sha(a.zip)
    if a.zip.stat().st_size >= 2**32:
        raise ValueError('real archive exceeds recovery ZIP32 bound')
    if shutil.disk_usage(recovery).free < a.zip.stat().st_size + 256 * 1024**2:
        raise ValueError('insufficient space for isolated archive copy')
    with ZipFile(a.zip) as z:
        embedded = json.loads(z.read('rom/manifest.json'))
        kind = embedded['rom_manifest']['kind']
        operation = embedded.get('operation', 'upgrade')
        if kind != 'rom_candidate' and not (kind == 'source_restore_candidate' and operation == 'restore-a70'):
            raise ValueError('not complete ROM payload')
        is_a71 = embedded['rom_manifest'].get('candidate_id') == 'A71-X710-EZH3-T860-UI85-REPAIRED'
        is_a74 = embedded['rom_manifest'].get('candidate_id') == 'A74-X710-EZH3-T860-UI85-FCM4-SDK30'
        if str(a.out).startswith('/var/tmp/ui85-a71-') and not is_a71:
            raise ValueError('A71 output requires A71 full candidate')
        if str(a.out).startswith('/var/tmp/ui85-a74-') and not is_a74:
            raise ValueError('A74 output requires A74 full candidate')
        is_a99 = embedded['rom_manifest'].get('candidate_id') == 'A99-SM-T860-S9-UI85-PHASE-20261008'
        if not is_a99:
            raise ValueError('A99 exact release required')
        support = embedded.get('support_member_sha256', {})
        if is_a71 and len(support) != 5:
            raise ValueError('A71 support inventory missing')
        if (is_a74 or is_a99) and set(support) != {'rom/support/' + name for name in (
                'vendor-guard-sdk28', 'vendor-guard-sdk30', 'vendor-config-recovery-guard', 'mainline-guard',
                'vendor-before-policy', 'vendor-after-policy', 'vendor-matrix28', 'vendor-matrix30', 'apex-factory.tsv', 'fscrypt-readonly-probe')}:
            raise ValueError('A74 complete nine-member support inventory missing')
        for member, expected in support.items():
            if z.namelist().count(member) != 1 or hashlib.sha256(z.read(member)).hexdigest() != expected:
                raise ValueError('support missing/duplicate/changed: ' + member)
        texts = {name: z.read('rom/' + name) for name in ('libupgrade.sh', 'upgrade.tsv', 'system.chunks', 'product.chunks')}
        if is_a74 or is_a99:
            config = dict(line.split('\t') for line in texts['upgrade.tsv'].decode().splitlines())
            if config['format'] != '3' or config['adaptation'] != 'A74_TWO_S6_CONFIGS':
                raise ValueError('A74 format/adaptation identity differs')
        total = sum(len(texts[p + '.chunks'].splitlines()) for p in ('system', 'product'))
        last_entry = z.getinfo(texts['product.chunks'].decode().splitlines()[-1].split('\t')[-1])
    if hashlib.sha256(texts['libupgrade.sh']).hexdigest() != embedded['installer_library_sha256']:
        raise ValueError('embedded library hash differs')
    with tempfile.TemporaryDirectory(prefix='actual-a45-zip-', dir=recovery / 'tmp') as temp:
        work = Path(temp)
        copied = work / 'candidate.zip'
        shutil.copyfile(a.zip, copied)
        if sha(copied) != zip_sha:
            raise ValueError('isolated copy differs')
        for name, raw in texts.items():
            (work / name).write_bytes(raw)
        inside = '/' + str(work.relative_to(recovery))
        script = work / 'preflight.sh'
        script.write_text('set -eu\nset -o pipefail\n'
                          'PATH=/sbin\nLD_LIBRARY_PATH=/sbin\nexport PATH LD_LIBRARY_PATH\n'
                          f'WORK="{inside}"\nZIP="{inside}/candidate.zip"\n'
                          f'SOURCE_MOUNT="{inside}/source-system"\n'
                          f'. "{inside}/libupgrade.sh"\n'
                          "TAB=$(printf '\\t')\n"
                          'abort() { printf "%s\\n" "$*" >&2; exit 1; }\n'
                          'ui_print() { printf "%s\\n" "$*"; }\n' +
                          ('a71_extract_support\n' if is_a71 or is_a74 or is_a99 else '') +
                          'verify_table system 6534725632\nverify_table product 1048576000\n'
                          'verify_payload\nprintf "REAL_COMPLETE_PAYLOAD_PREFLIGHT_PASS\\n"\n')
        # Original Bionic requires /proc/self/exe; old df additionally requires
        # the chroot root to be represented as its own bind mount.
        argv = ['unshare', '--mount', '--pid', '--fork', '/bin/sh', '-c',
                'mount --bind "$1" "$1" && mount -t proc -o ro proc "$1/proc" && exec chroot "$1" /sbin/sh "$2"',
                't860-native-preflight', str(recovery), inside + '/preflight.sh']
        r = subprocess.run(argv, capture_output=True, text=True, timeout=1200,
                           env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LD_LIBRARY_PATH': '/sbin'})
        (a.out / 'stdout.txt').write_text(r.stdout)
        (a.out / 'stderr.txt').write_text(r.stderr)
        if r.returncode or 'REAL_COMPLETE_PAYLOAD_PREFLIGHT_PASS' not in r.stdout:
            raise ValueError('real TWRP payload preflight failed: ' + r.stderr[-2000:])
    if sha(a.zip) != zip_sha:
        raise ValueError('original package changed')
    result = {'schema': 1, 'kind': 'real_complete_rom_twrp_native_payload_preflight',
              'zip_sha256': zip_sha, 'zip_bytes': a.zip.stat().st_size,
              'script_sha256': sha(Path(__file__)), 'recovery_sha256': tools['recovery_sha256'],
              'tools_manifest_sha256': sha(recovery / 'tools-manifest.json'),
              'installer_library_sha256': embedded['installer_library_sha256'], 'payload_chunks_checked': total,
              'support_members_checked': sorted(support),
              'operation': operation,
              'last_payload_header_offset': last_entry.header_offset, 'process_exit': r.returncode,
              'table_sizes_checked': {'system': 6534725632, 'product': 1048576000},
              'temporary_archive_copy_removed': True, 'device_writes': False,
              'update_binary_executed': False, 'block_device_nodes_available': False,
              'hardware_runtime': 'NOT_TESTED', 'dirty_upgrade_runtime': 'NOT_TESTED',
              'limits': ['Actual TWRP sh/awk/unzip/hash tools execute on Linux kernel against every real ZIP payload block.',
                         'Only table and payload preflight functions run; mount/block/source-ROM/real flashing do not.',
                         'Linux userspace success cannot prove T860 recovery kernel or encrypted-data upgrade.']}
    (a.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('zip_sha256', 'zip_bytes', 'payload_chunks_checked', 'process_exit')}))


if __name__ == '__main__':
    main()
