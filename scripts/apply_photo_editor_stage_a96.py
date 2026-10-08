#!/usr/bin/env python3
"""Add the reviewed app bundle to a NEW A96 Linux staging tree.

Never apply to frozen A84 or donor mounts. Requires an independently captured
full source inventory and its digest; exact-size image capacity is a later gate.
"""
import argparse
import json
import os
from pathlib import Path
from apply_device_stage_integration_ui85 import checked, inventory, sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('stage', 'baseline', 'bundle', 'profile', 'out'):
        p.add_argument('--' + n, type=Path, required=True)
    p.add_argument('--baseline-sha256', required=True)
    a = p.parse_args()
    if os.uname().sysname != 'Linux' or os.geteuid():
        raise ValueError('Linux root required for native filesystem metadata')
    if not str(a.stage).startswith('/var/tmp/ui85-a96-') or not a.stage.is_dir() or a.stage.is_symlink():
        raise ValueError('NEW A96 native scratch stage required')
    if a.out.exists() or a.out.resolve().is_relative_to(a.stage):
        raise ValueError('Fresh external evidence output required')
    if len(a.baseline_sha256) != 64 or sha(a.baseline) != a.baseline_sha256:
        raise ValueError('Reviewed inventory digest differs')
    before = inventory(a.stage)
    if before != json.loads(a.baseline.read_text()):
        raise ValueError('Whole source inventory differs')
    spec = json.loads(a.profile.read_text())
    if spec['id'] != 'A96_S9_PHOTO_EDITOR_CORE_RESTORE' or spec['net_regular_bytes'] != 156507644:
        raise ValueError('Reviewed app profile differs')
    rel = spec['stage_dir']
    if rel != 'system/system/priv-app/PhotoEditor_AIFull' or checked(a.stage, rel).exists():
        raise ValueError('Exact missing app destination required')
    prop = checked(a.stage, 'system/system/build.prop').read_text().splitlines()
    if any(t not in prop for t in ('ro.build.version.sdk=36', 'ro.build.version.oneui=80500')):
        raise ValueError('Wrong donor version; UI9 needs a new reviewed profile')
    allowlist = checked(a.stage, 'system/system/etc/permissions/privapp-permissions-com.sec.android.mimage.photoretouching.xml')
    if sha(allowlist) != '5fd4a7d1089e9ef17d1acbab2c06a969d7af9e5d09864900bb28add24f7ffe87':
        raise ValueError('Original donor privilege allowlist differs')
    wanted = {'PhotoEditor_AIFull.apk': {'size': spec['apk_size'], 'sha256': spec['apk_sha256']}}
    wanted.update({'lib/arm64/' + n: m for n, m in spec['native_libraries'].items()})
    if len(wanted) != 69:
        raise ValueError('Private native closure differs')
    for n, meta in wanted.items():
        f = checked(a.bundle, 'files/system/' + spec['system_relative_dir'] + '/' + n)
        if f.stat().st_size != meta['size'] or sha(f) != meta['sha256']:
            raise ValueError('Prepared bundle differs')
    expected = json.loads(json.dumps(before))
    label = b'u:object_r:system_file:s0'
    dirs = ['', '/lib', '/lib/arm64']
    for n in dirs:
        expected[rel + n] = {'uid': 0, 'gid': 0, 'mode': 0o40755,
                             'xattrs': {'security.selinux': label.hex()}}
    for n, meta in wanted.items():
        expected[rel + '/' + n] = {'uid': 0, 'gid': 0, 'mode': 0o100644,
                                  'xattrs': {'security.selinux': label.hex()}, **meta}
    a.out.mkdir(parents=True)
    (a.out / 'before.json').write_bytes(a.baseline.read_bytes())
    made = []
    try:
        for n in dirs:
            d = checked(a.stage, rel + n)
            d.mkdir(mode=0o755)
            made.append(d)
        for n in wanted:
            f = checked(a.stage, rel + '/' + n)
            with f.open('xb') as stream:
                made.append(f)
                stream.write(checked(a.bundle, 'files/system/' + spec['system_relative_dir'] + '/' + n).read_bytes())
        for f in made:
            os.chown(f, 0, 0)
            os.chmod(f, 0o755 if f.is_dir() else 0o644)
            for name in os.listxattr(f):
                os.removexattr(f, name)
            os.setxattr(f, 'security.selinux', label)
        after = inventory(a.stage)
        if after != expected:
            raise ValueError('Unapproved whole stage change')
    except BaseException:
        for f in reversed(made):
            if f.is_dir():
                f.rmdir()
            else:
                f.unlink()
        if inventory(a.stage) != before:
            raise ValueError('Rollback inventory differs')
        raise
    (a.out / 'after.json').write_text(json.dumps(after, indent=2, sort_keys=True) + '\n')
    (a.out / 'result.json').write_text(json.dumps({'id': spec['id'], 'added_files': 69,
        'net_regular_bytes': spec['net_regular_bytes'], 'all_other_content_attributes_identical': True,
        'capacity': 'EXACT_IMAGE_REMEASUREMENT_REQUIRED', 'device_writes': False}) + '\n')
    print('A96 new scratch stage restored; image capacity gate still required')


if __name__ == '__main__':
    main()
