#!/usr/bin/env python3
"""Prepare an immutable S9 PhotoEditor APK and its own arm64 libraries.

No global library replacement, firmware writes, APK edits, or device changes.
UI9 requires a newly reviewed profile; this script deliberately rejects it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apk', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    spec = json.loads((ROOT / 'device/s6/photo-editor-ui85-a96.json').read_text())
    if a.out.exists() or not a.out.resolve().is_relative_to(ROOT / 'out/patch-probes'):
        raise ValueError('Fresh project patch-probes output required')
    data = a.apk.read_bytes()
    if len(data) != spec['apk_size'] or sha(data) != spec['apk_sha256']:
        raise ValueError('Reviewed new donor APK differs')
    sdk = Path('${ANDROID_SDK_ROOT}/build-tools/37.0.0')
    cert = subprocess.check_output([sdk / 'apksigner', 'verify', '--print-certs', a.apk], text=True)
    if 'certificate SHA-256 digest: ' + spec['certificate_sha256'] not in cert:
        raise ValueError('Original Samsung certificate differs')
    badging = subprocess.check_output([sdk / 'aapt2', 'dump', 'badging', a.apk], text=True)
    for token in ("name='" + spec['package'] + "'", "versionCode='382420100'", "minSdkVersion:'35'"):
        if token not in badging:
            raise ValueError('Reviewed manifest differs')
    files = {'PhotoEditor_AIFull.apk': data}
    with ZipFile(a.apk) as z:
        if len(z.namelist()) != len(set(z.namelist())) or z.testzip():
            raise ValueError('Invalid or duplicate ZIP members')
        native = {Path(n).name: {'size': z.getinfo(n).file_size, 'sha256': sha(z.read(n))}
                  for n in z.namelist() if n.startswith('lib/arm64-v8a/')}
        if native != spec['native_libraries'] or len(native) != 68:
            raise ValueError('Reviewed private native closure differs')
        for name in native:
            if Path(name).name != name or not name.endswith('.so'):
                raise ValueError('Unsafe library name')
            files['lib/arm64/' + name] = z.read('lib/arm64-v8a/' + name)
    if sum(map(len, files.values())) != spec['net_regular_bytes']:
        raise ValueError('Capacity cost differs')
    a.out.mkdir(parents=True)
    entries = []
    for name, content in files.items():
        rel = spec['system_relative_dir'] + '/' + name
        dest = a.out / 'files/system' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        entries.append({'relative_path': rel, 'sha256': sha(content), 'size': len(content),
                        'uid': 0, 'gid': 0, 'mode': '644', 'selinux': 'u:object_r:system_file:s0'})
    report = {'id': spec['id'], 'files': entries, 'net_regular_bytes': spec['net_regular_bytes'],
              'signed_apk_unchanged': True, 'old_rom_binary_used': False,
              'device_writes': False, 'source_stage_writes': False}
    (a.out / 'bundle.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'files': len(entries), 'net_bytes': spec['net_regular_bytes']}))


if __name__ == '__main__':
    main()
