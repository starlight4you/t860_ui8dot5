#!/usr/bin/env python3
"""Build an isolated A72 trial JAR; never apply it to a ROM or device partition."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile

INPUT_SHA = '461262da101bb6ccb5e840c79e5d0b8f88050a9638b073fa04b082fd525c3268'
METHOD_SHA = '81065ff99dd0b2c9e4db8f6d9dec04376338d978f114e21de2def232c7c426be'
CLASS = 'com/samsung/security/fabric/crypto/FabricCrypto.smali'
METHOD = '.method private handleRemoteExceptionWithRetry'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'tools', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    source = args.input.resolve(strict=True)
    if sha(source.read_bytes()) != INPUT_SHA or args.out.exists():
        raise ValueError('Exact reviewed input and fresh output required')
    root = Path(__file__).resolve().parents[1]
    output = args.out.resolve()
    if not output.is_relative_to(root / 'out/audit-probes'):
        raise ValueError('Trial output must be in out/audit-probes, never a ROM tree')
    output.mkdir(parents=True, mode=0o700)
    baksmali = args.tools / 'baksmali-3.0.6-fat.jar'
    smali = args.tools / 'smali-3.0.6-fat.jar'

    def run(command):
        result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=90)
        with (output / 'tool-log.txt').open('a') as log:
            log.write(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('Assembly/disassembly failed; inspect tool-log.txt')

    with ZipFile(source) as jar:
        if set(jar.namelist()) != {'classes.dex', 'META-INF/MANIFEST.MF'} or jar.testzip():
            raise ValueError('Unexpected archive members or CRC')
        (output / 'original.dex').write_bytes(jar.read('classes.dex'))
        manifest = jar.read('META-INF/MANIFEST.MF')
    # Match the source DEX039 format. This changes no firmware SDK property.
    run(['java', '-jar', baksmali, 'disassemble', '--api', '28', output / 'original.dex', '-o', output / 'original-smali'])
    import shutil
    shutil.copytree(output / 'original-smali', output / 'trial-smali')
    target = output / 'trial-smali' / CLASS
    before = target.read_text()
    start = before.index(METHOD)
    end = before.index('.end method', start) + len('.end method')
    body = before[start:end]
    if sha(body.encode()) != METHOD_SHA:
        raise ValueError('Reviewed method body differs')
    anchor = '    :goto_6\n    :try_start_6\n'
    guard = '''    :goto_6
    if-nez v0, :s6_fabric_service_present

    new-instance v2, Lcom/samsung/security/fabric/crypto/FabricCryptoException;
    const/4 v3, -0x4
    const-string v4, "Fabric crypto service unavailable"
    invoke-direct {v2, v3, v4}, Lcom/samsung/security/fabric/crypto/FabricCryptoException;-><init>(ILjava/lang/String;)V
    throw v2

    :s6_fabric_service_present
    :try_start_6
'''
    if body.count(anchor) != 1 or '.registers 8' not in body:
        raise ValueError('Loop entry/register contract differs')
    changed = body.replace(anchor, guard)
    target.write_text(before[:start] + changed + before[end:])
    run(['java', '-jar', smali, 'assemble', '--api', '28', output / 'trial-smali', '-o', output / 'trial.dex'])
    if (output / 'trial.dex').read_bytes()[:8] != b'dex\n039\x00':
        raise ValueError('Source DEX039 encoding must be retained')
    run(['java', '-jar', baksmali, 'disassemble', '--api', '28', output / 'trial.dex', '-o', output / 'verified-smali'])
    original = {p.relative_to(output / 'original-smali'): p.read_text() for p in (output / 'original-smali').rglob('*.smali')}
    verified = {p.relative_to(output / 'verified-smali'): p.read_text() for p in (output / 'verified-smali').rglob('*.smali')}
    if original.keys() != verified.keys():
        raise ValueError('Class set differs after round trip')
    changed_classes = [str(p) for p in original if original[p] != verified[p]]
    if changed_classes != [CLASS]:
        raise ValueError('Unexpected class changes: ' + repr(changed_classes))
    checked = verified[Path(CLASS)]
    cs = checked.index(METHOD)
    ce = checked.index('.end method', cs) + len('.end method')
    if before[:start] != checked[:cs] or before[end:] != checked[ce:]:
        raise ValueError('Other methods/fields in target class changed')
    trial = output / 'FabricCryptoLib-trial.jar'
    with ZipFile(source) as original_jar, ZipFile(trial, 'x') as trial_jar:
        for item in original_jar.infolist():
            payload = (output / 'trial.dex').read_bytes() if item.filename == 'classes.dex' else original_jar.read(item.filename)
            trial_jar.writestr(item, payload)
    with ZipFile(trial) as jar:
        if jar.testzip() or jar.read('META-INF/MANIFEST.MF') != manifest:
            raise ValueError('Trial archive integrity failed')
    report = {
        'schema': 1, 'status': 'ISOLATED_TRIAL_NOT_DEPLOYED',
        'input_jar_sha256': INPUT_SHA, 'input_method_sha256': METHOD_SHA,
        'trial_jar_sha256': sha(trial.read_bytes()), 'class_count': len(original),
        'changed_classes': changed_classes, 'other_methods_fields_smali_identical': True,
        'missing_service_error': -4, 'callback_not_executed_when_service_null': True,
        'guard_at_retry_loop_entry': True,
        'tools_sha256': {p.name: sha(p.read_bytes()) for p in (baksmali, smali)},
        'builder_sha256': sha(Path(__file__).read_bytes()),
        'rom_stage_modified': False, 'device_partition_modified': False,
        'runtime': 'NOT_TESTED', 'release': 'NOT_PASSED',
        'limits': ['DEX reassembled; byte layout/signature/checksum change.',
                   'Only one method differs in independently disassembled output.',
                   'Kmx containsKey error overwrite and native daemon loop unresolved.',
                   'Not suitable for deployment without caller and service lifecycle validation.']}
    (output / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
