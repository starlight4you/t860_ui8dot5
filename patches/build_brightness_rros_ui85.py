#!/usr/bin/env python3
"""Compile bounded S6 device XML against pinned S9 resources into fresh probes.

Uses the existing project overlay certificate; never copies old overlay APKs or
changes the stage/device. Packages are immutable framework resource overlays.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_brightness_resources_ui85 import RESOURCES, array, integer


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, cwd=None):
    r = subprocess.run([str(x) for x in argv], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise ValueError(r.stderr[-2500:])
    return r.stdout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out = a.out.resolve()
    if a.out.exists() or not a.out.is_relative_to(ROOT / 'out/patch-probes'):
        raise ValueError('fresh scoped output required')
    profile_path = ROOT / 'device/s6/brightness-ui85.json'
    profile = json.loads(profile_path.read_text())
    audit_path = ROOT / 'docs/audit/brightness-resources-ui85.json'
    if sha(audit_path) != profile['source_audit_sha256']:
        raise ValueError('resource source audit differs')
    sdk = Path(os.environ['ANDROID_SDK_ROOT']) / 'build-tools/36.0.0'
    aapt, signer = sdk / 'aapt2', sdk / 'apksigner'
    for tool, pin in [(aapt, 'aapt2_sha256'), (signer, 'apksigner_sha256')]:
        if sha(tool) != profile[pin]:
            raise ValueError('tool differs: ' + tool.name)
    framework = ROOT / 'out/audit-probes/A39-new-java-runtime-v1/framework-res.apk'
    if sha(framework) != profile['target_framework_sha256']:
        raise ValueError('new target framework differs')
    src = ROOT / 'device/s6/overlay'
    actual_sources = {str(f.relative_to(src)): sha(f) for f in src.rglob('*') if f.is_file()}
    if actual_sources != profile['source_files_sha256']:
        raise ValueError('bounded XML/manifest source set changed')
    key_dir = ROOT / 't860-ui8/keys/t860-oneui8-local'
    cert, key = key_dir / 'release-cert.x509.pem', key_dir / 'release-key.pk8'
    if not key.is_file():
        raise ValueError('existing signing key unavailable; do not generate a replacement')
    der = subprocess.check_output(['openssl', 'x509', '-in', str(cert), '-outform', 'DER'])
    if hashlib.sha256(der).hexdigest() != profile['certificate_sha256']:
        raise ValueError('existing upgrade certificate changed')
    a.out.mkdir(parents=True)
    outputs = []
    for spec in profile['packages']:
        group = spec['group']
        project = a.out / 'work' / group
        shutil.copytree(src / group, project)
        (project / 'compiled').mkdir()
        # Relative compile paths keep source labels stable across fresh replays.
        run([aapt, 'compile', '--dir', 'res', '-o', 'compiled'], cwd=project)
        flats = sorted(str(f.relative_to(project)) for f in (project / 'compiled').glob('*.flat'))
        if not flats:
            raise ValueError('no compiled resources')
        run([aapt, 'link', '-o', 'unsigned.apk', '--manifest', 'AndroidManifest.xml',
             '-I', framework, '--auto-add-overlay', '--no-resource-deduping',
             '--no-resource-removal', '--min-sdk-version', '36', '--target-sdk-version', '36',
             '--version-code', '1', '--version-name', '1.0', *flats], cwd=project)
        output = a.out / spec['stage_path']
        output.parent.mkdir(parents=True, exist_ok=True)
        run([signer, 'sign', '--key', key, '--cert', cert, '--v1-signing-enabled', 'true',
             '--v2-signing-enabled', 'true', '--v3-signing-enabled', 'true',
             '--out', output, project / 'unsigned.apk'])
        signature = run([signer, 'verify', '--verbose', '--print-certs', output])
        match = re.search(r'Signer #1 certificate SHA-256 digest: ([0-9a-f]+)', signature)
        if not match or match[1] != profile['certificate_sha256']:
            raise ValueError('output certificate differs')
        resources = run([aapt, 'dump', 'resources', output])
        manifest = run([aapt, 'dump', 'xmltree', output, '--file', 'AndroidManifest.xml'])
        (project / 'resources.txt').write_text(resources)
        (project / 'manifest.txt').write_text(manifest)
        # Keep only verification lines/cert digest; no signing key material.
        (project / 'signature.txt').write_text('\n'.join(l for l in signature.splitlines()
                                                       if 'Verified using' in l or 'SHA-256 digest:' in l) + '\n')
        for g, _, name, count in RESOURCES:
            if g != group:
                continue
            _, actual = array(resources, name)
            xml = ET.parse(src / group / 'res/values/arrays.xml').getroot()
            found = [node for node in xml if node.get('name') == name]
            if len(found) != 1:
                raise ValueError('source resource not unique: ' + name)
            values = [node.text for node in found[0]]
            if actual != values or len(actual) != count:
                raise ValueError('linked resource differs from stock XML: ' + name)
        if group == 'panel' and integer(resources, 'config_screenBrightnessExtendedMaximum')[1] != 355:
            raise ValueError('linked extended maximum differs')
        expected_resource_names = {n for g, _, n, _ in RESOURCES if g == group}
        if group == 'panel':
            expected_resource_names.add('config_screenBrightnessExtendedMaximum')
        names = set(re.findall(r'resource 0x[0-9a-f]+ (?:array|integer)/([^\s]+)', resources))
        if names != expected_resource_names:
            raise ValueError('unexpected resource scope')
        if 'package="' + spec['package'] + '"' not in manifest or 'hasCode(0x0101000c)=false' not in manifest:
            raise ValueError('manifest package/code scope differs')
        with ZipFile(output) as z:
            if z.testzip() or any(n.endswith('.dex') or n.startswith('lib/') for n in z.namelist()):
                raise ValueError('not a code-free valid RRO')
        outputs.append({**spec, 'sha256': sha(output), 'size': output.stat().st_size,
                        'certificate_sha256': match[1], 'resource_count': len(names),
                        'linked_resources_match_stock_xml': True})
    result = {
        'schema': 1, 'kind': 'compatibility_probe', 'id': 'F07-BRIGHTNESS-RRO',
        'script_sha256': sha(Path(__file__)), 'profile_sha256': sha(profile_path),
        'source_audit_sha256': sha(audit_path), 'target_framework_sha256': sha(framework),
        'files': outputs, 'total_bytes': sum(x['size'] for x in outputs),
        'old_binary_copied': False, 'firmware_stage_modified': False, 'device_writes': False,
        'idmap_runtime': 'NOT_TESTED', 'new_rom_runtime': 'NOT_TESTED',
        'status': 'PREPARED_NOT_APPLIED_NOT_RUNTIME_TESTED', 'limits': profile['limits'],
    }
    (a.out / 'probe-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'apks': len(outputs), 'total_bytes': result['total_bytes'], 'new_stage_changes': 0}))


if __name__ == '__main__':
    main()
