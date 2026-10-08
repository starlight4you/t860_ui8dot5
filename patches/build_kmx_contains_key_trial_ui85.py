#!/usr/bin/env python3
"""Generate isolated selected-method fixtures; never rebuild/sign an APK."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile, ZipInfo

CLASS_SHA = '5c4d921e730aec1146061a8e2706800fac35b23837d232a706302ba25f5df043'
METHOD_SHA = '55f81c2484a383969053733cb0f52c14f28e9e30fe75ac1f1962e85be25264b0'
CLASS = 'Lcom/samsung/android/kmxservice/e2ee/E2eeServiceInternal;'
STORE = 'Lcom/samsung/android/kmxservice/fabrickeystore/FabricKeyStore;'
ERROR = 'Lcom/samsung/security/fabric/crypto/FabricCryptoException;'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def patch_method(method):
    if sha(method.encode()) != METHOD_SHA:
        raise ValueError('Exact reviewed method required')
    old = '    invoke-virtual {p1}, Ljava/lang/Throwable;->printStackTrace()V\n\n    move p0, v2\n'
    new = '    invoke-virtual {p1}, Ljava/lang/Throwable;->printStackTrace()V\n\n    return-object v0\n'
    if method.count(old) != 1:
        raise ValueError('Catch tail differs')
    return method.replace(old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'tools', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.out.exists() or not args.out.resolve().is_relative_to(root / 'out/audit-probes'):
        raise ValueError('Fresh isolated audit output required')
    original = args.input.read_text()
    if sha(args.input.read_bytes()) != CLASS_SHA:
        raise ValueError('Pinned original Kmx class differs')
    method = re.search(r'^\.method public containsKey\(Landroid/os/Bundle;\)Landroid/os/Bundle;.*?^\.end method', original, re.M | re.S).group()
    trial = patch_method(method)
    args.out.mkdir(parents=True, mode=0o700)
    skeleton = f''' .class public {CLASS}
.super Ljava/lang/Object;
.field private TAG:Ljava/lang/String;
.field private mFabricKeyStore:{STORE}
.method public constructor <init>()V
    .registers 2
    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V
    const-string v0, "A72-ISOLATED-KMX"
    iput-object v0, p0, {CLASS}->TAG:Ljava/lang/String;
    new-instance v0, {STORE}
    invoke-direct {{v0}}, {STORE}-><init>()V
    iput-object v0, p0, {CLASS}->mFabricKeyStore:{STORE}
    return-void
.end method
.method private ensureFabricKeyStore()Z
    .registers 1
    const/4 p0, 0x0
    return p0
.end method
'''.lstrip()
    stub = f'''.class public {STORE}
.super Ljava/lang/Object;
.field public static mode:I
.field public static calls:I
.method public constructor <init>()V
    .registers 1
    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V
    return-void
.end method
.method public containsKey(Ljava/lang/String;Ljava/lang/String;)Z
    .registers 4
    sget v0, {STORE}->calls:I
    add-int/lit8 v0, v0, 0x1
    sput v0, {STORE}->calls:I
    sget v0, {STORE}->mode:I
    if-eqz v0, :exists
    const/4 p0, 0x1
    if-ne v0, p0, :error
    const/4 p0, 0x0
    return p0
    :exists
    const/4 p0, 0x1
    return p0
    :error
    const/4 p0, 0x2
    if-ne v0, p0, :key_missing
    const/4 p1, -0x4
    goto :throw_error
    :key_missing
    const/4 p0, 0x3
    if-ne v0, p0, :unknown
    const/4 p1, -0x7
    goto :throw_error
    :unknown
    const/16 p1, -0x3e8
    :throw_error
    new-instance p0, {ERROR}
    const-string p2, "Synthetic store failure; no real key operation"
    invoke-direct {{p0, p1, p2}}, {ERROR}-><init>(ILjava/lang/String;)V
    throw p0
.end method
'''
    jar_hashes = {}
    for label, selected in (('original', method), ('trial', trial)):
        folder = args.out / label
        folder.mkdir()
        (folder / 'Target.smali').write_text(skeleton + '\n' + selected + '\n')
        (folder / 'SyntheticStore.smali').write_text(stub)
        dex = args.out / (label + '.dex')
        result = subprocess.run(['java', '-jar', str(args.tools / 'smali-3.0.6-fat.jar'), 'assemble', '--api', '28', str(folder), '-o', str(dex)], capture_output=True, text=True, check=True)
        (args.out / (label + '-assembly.log')).write_text(result.stdout + result.stderr)
        if dex.read_bytes()[:8] != b'dex\n039\x00':
            raise ValueError('Fixture encoding mismatch')
        with ZipFile(args.out / (label + '.jar'), 'x') as archive:
            archive.writestr(ZipInfo('classes.dex', (1980, 1, 1, 0, 0, 0)), dex.read_bytes())
        jar_hashes[label] = sha((args.out / (label + '.jar')).read_bytes())
    report = {'schema': 1, 'status': 'SELECTED_METHOD_FIXTURES_NOT_APK_PATCH',
              'original_class_sha256': CLASS_SHA, 'original_method_sha256': METHOD_SHA,
              'trial_method_sha256': sha(trial.encode()), 'fixture_jars_sha256': jar_hashes,
              'builder_sha256': sha(Path(__file__).read_bytes()),
              'smali_tool_sha256': sha((args.tools / 'smali-3.0.6-fat.jar').read_bytes()),
              'reason': 'Return the existing error6 Bundle directly from the typed exception handler, without overwrite by105.',
              'scaffolding': ['Test constructor sets a synthetic store; no Context/DB.',
                              'Test ensureFabricKeyStore does not allocate.',
                              'Test store returns booleans or throws -4/-7/-1000; no crypto operations.'],
              'apk_signature_modified': False, 'rom_modified': False, 'release': 'NOT_PASSED'}
    (args.out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
