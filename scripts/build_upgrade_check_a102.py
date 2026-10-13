#!/usr/bin/env python3
"""Build a small read-only TWRP diagnosis ZIP without changing release assets."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
def sha(data): return hashlib.sha256(data).hexdigest()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndk', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=ROOT/'out/releases/v1.0.1-A100/TabS6-OneUI8.5-v1.0.1-A100-Upgrade-TWRP.zip')
    parser.add_argument('--guard', type=Path, default=ROOT/'out/patch-probes/A99-release-tools-v3/mainline-guard')
    args = parser.parse_args()
    if args.out.exists(): raise ValueError('Fresh output required')
    args.out.mkdir(parents=True)
    cc = args.ndk/'toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang'
    if '27.3.13750724' not in (args.ndk/'source.properties').read_text() or sha(cc.read_bytes()) != 'c0e2e0373d192a8f9339e3148b2c56d41f60286ea5ff6ed3920c767be8090857':
        raise ValueError('Reviewed NDK/compiler required')
    probe = args.out/'upgrade-access-probe'
    subprocess.run([str(cc), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-fno-emulated-tls', str(ROOT/'device/s6/native/upgrade_access_probe_a102.c'), '-o', str(probe)], check=True)
    source_zip = args.source
    # Only the embedded support hashes are used; no partition payload is copied.
    with zipfile.ZipFile(source_zip) as archive:
        manifest = json.loads(archive.read('rom/manifest.json'))
        if manifest['rom_manifest']['candidate_id'] != 'A100-SM-T860-S9-UI85-20261012': raise ValueError('Wrong source package')
        support = {name: archive.read('rom/support/'+name) for name in ('mainline-guard', 'apex-factory.tsv')}
        for name, data in support.items():
            if sha(data) != manifest['support_member_sha256']['rom/support/'+name]: raise ValueError('Support differs')
        pins={'mainline-guard':'f0b671505a818808adc788d2524974b8fe3fd6c7365602d6b4a8443394335c66',
              'apex-factory.tsv':'3db9c6be68d3310e1cad7af3848a675dfef9a225504ad93c830e3ecbffb3c02a'}
        if any(sha(support[name])!=pin for name,pin in pins.items()):raise ValueError('Released A100 support identity differs')
    support['upgrade-access-probe'] = probe.read_bytes()
    support['mainline-guard-a100'] = support['mainline-guard']
    support['mainline-guard'] = args.guard.read_bytes()
    if sha(support['mainline-guard']) != '4f3f04af10250a0522b4bf2805fe0567fef975da1aea9e24024d86eba8ca8176':
        raise ValueError('Upgrade-capable guard differs')
    extract = []
    for name, data in support.items():
        extract.extend([f'unzip -p "$ZIP" support/{name} > "$WORK/{name}" || exit 1',
                        f'[ "$(sha256sum "$WORK/{name}" | awk \'{{print $1}}\')" = {sha(data)} ] || {{ say \'Support hash differs\'; exit 1; }}'])
        if name != 'apex-factory.tsv': extract.append(f'chmod 0700 "$WORK/{name}"')
    template = (ROOT/'installer/upgrade-check-a102.sh').read_text()
    if template.count('@@EXTRACT@@') != 1: raise ValueError('Ambiguous template')
    updater = template.replace('@@EXTRACT@@', '\n'.join(extract)).encode()
    target = args.out/'TabS6-Upgrade-Check-A102.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=False) as archive:
        for name, data in {'META-INF/com/google/android/update-binary': updater,
                           'META-INF/com/google/android/updater-script': b'# Read-only diagnosis, no ROM payload.\n',
                           **{'support/'+name: data for name, data in support.items()}}.items():
            info = zipfile.ZipInfo(name, (2026, 10, 13, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if name.endswith('update-binary') else 0o100644) << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip(): raise ValueError('CRC failed')
    report = {'id':'A102_READ_ONLY_UPGRADE_DIAGNOSIS', 'zip_sha256':sha(target.read_bytes()),
              'zip_bytes':target.stat().st_size, 'updater_sha256':sha(updater),
              'support_sha256':{name:sha(data) for name,data in support.items()},
              'source_library_sha256':manifest['installer_library_sha256'],
              'partition_payloads':False, 'data_mutations':False, 'release_modified':False,
              'runtime':'NOT_TESTED'}
    (args.out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
if __name__ == '__main__': main()
