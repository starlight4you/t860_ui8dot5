#!/usr/bin/env python3
"""Build one code-free SM-T860 rounded-corner RRO against pinned new S9 resources."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / 'out/patch-probes'):
        raise ValueError('fresh scoped output required')
    profile = json.loads((ROOT / 'device/s6/rounded-corners-ui85.json').read_text())
    framework = ROOT / 'out/audit-probes/A39-new-java-runtime-v1/framework-res.apk'
    src = ROOT / 'device/s6/rounded-corners-overlay'
    systemui = ROOT / 'out/audit-probes/A70-rounded-corners/s9-systemui.apk'
    if sha(systemui) != profile['target_systemui_sha256']:
        raise ValueError('target new SystemUI differs')
    if sha(framework) != profile['target_framework_sha256']:
        raise ValueError('target new donor differs')
    if {str(f.relative_to(src)): sha(f) for f in src.rglob('*') if f.is_file()} != profile['sources']:
        raise ValueError('reviewed source scope differs')
    sdk = Path(os.environ['ANDROID_SDK_ROOT']) / 'build-tools/36.0.0'
    for name in ('aapt2', 'apksigner'):
        if sha(sdk / name) != profile[name + '_sha256']:
            raise ValueError('tool differs')
    keys = ROOT / 't860-ui8/keys/t860-oneui8-local'
    cert, key = keys / 'release-cert.x509.pem', keys / 'release-key.pk8'
    der = subprocess.check_output(['openssl', 'x509', '-in', str(cert), '-outform', 'DER'])
    if hashlib.sha256(der).hexdigest() != profile['certificate_sha256']:
        raise ValueError('existing certificate differs')
    out.mkdir(parents=True)
    work = out / 'work'
    shutil.copytree(src, work)
    (work / 'compiled').mkdir()

    def run(argv):
        return subprocess.check_output([str(x) for x in argv], cwd=work, stderr=subprocess.STDOUT, text=True)

    run([sdk / 'aapt2', 'compile', '--dir', 'res', '-o', 'compiled'])
    flats = sorted(str(f.relative_to(work)) for f in (work / 'compiled').glob('*.flat'))
    run([sdk / 'aapt2', 'link', '-o', 'unsigned.apk', '--manifest', 'AndroidManifest.xml',
         '-I', framework, '-I', systemui, '--auto-add-overlay', '--min-sdk-version', '36',
         '--target-sdk-version', '36', '--version-code', '1', '--version-name', '1.0', *flats])
    output = out / profile['stage_path']
    output.parent.mkdir(parents=True)
    run([sdk / 'apksigner', 'sign', '--key', key, '--cert', cert,
         '--out', output, 'unsigned.apk'])
    signature = run([sdk / 'apksigner', 'verify', '--verbose', '--print-certs', output])
    if 'Signer #1 certificate SHA-256 digest: ' + profile['certificate_sha256'] not in signature:
        raise ValueError('signature differs')
    resources = run([sdk / 'aapt2', 'dump', 'resources', output])
    names = re.findall(r'resource 0x[0-9a-f]+ (\w+/\S+)', resources)
    if set(names) != {'bool/config_enableRoundedCorner', 'drawable/rounded_corner'} or not re.search(r'bool/config_enableRoundedCorner\n\s*\(\) true', resources):
        raise ValueError('resource scope/value differs')
    (out / 'resources.txt').write_text(resources)
    with ZipFile(output) as z:
        if z.testzip() or any(n.endswith('.dex') or n.startswith('lib/') for n in z.namelist()):
            raise ValueError('invalid or code-bearing overlay')
    manifest = {'schema': 1, 'id': 'A70-ROUNDED-CORNERS-RRO',
                'target_framework_sha256': sha(framework), 'target_systemui_sha256': sha(systemui), 'old_binary_copied': False,
                'files': [{'group': 'rounded-corners', 'stage_path': profile['stage_path'],
                           'sha256': sha(output), 'size': output.stat().st_size}],
                'total_bytes': output.stat().st_size, 'device_writes': False,
                'runtime': 'NOT_TESTED', 'reason': profile['reason_record']}
    (out / 'probe-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
