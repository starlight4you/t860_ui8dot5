#!/usr/bin/env python3
"""Prepare six physical identity values on the three exact new donor prop files."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'profile', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    spec = json.loads(a.profile.read_text())
    if a.out.exists() or a.out.resolve().is_relative_to(a.inputs.resolve()):
        raise ValueError('fresh separate output required')
    if spec['kind'] != 'reviewed_split_identity' or spec['flashable'] is not False or len(spec['files']) != 3:
        raise ValueError('wrong identity contract')
    outputs = []
    allowed = {'system/system/build.prop': 'system',
               'system/system_ext/etc/build.prop': 'system_ext', 'product/etc/build.prop': 'product'}
    if {e['path'] for e in spec['files']} != set(allowed):
        raise ValueError('unexpected prop paths')
    for e in spec['files']:
        src = a.inputs / e['path']
        if src.is_symlink() or sha(src) != e['input_sha256']:
            raise ValueError('donor identity input changed')
        before = src.read_bytes()
        text = before.decode()
        prefix = allowed[e['path']]
        expected = {f'ro.product.{prefix}.model', f'ro.product.{prefix}.name'}
        if set(e['changes']) != expected:
            raise ValueError('unexpected identity keys')
        changed = []
        for key, v in e['changes'].items():
            matches = [l for l in text.splitlines() if l.startswith(key + '=')]
            old, new = key + '=' + v['from'], key + '=' + v['to']
            if matches != [old] or text.count(old + '\n') != 1:
                raise ValueError('identity key/value is not unique')
            if v['to'] != ('SM-T860' if key.endswith('.model') else 'gts6lwifixx'):
                raise ValueError('wrong physical identity')
            text = text.replace(old + '\n', new + '\n', 1)
            changed.append({'key': key, 'from': v['from'], 'to': v['to']})
        left, right = before.decode().splitlines(keepends=True), text.splitlines(keepends=True)
        if len(left) != len(right) or sum(l != r for l, r in zip(left, right)) != 2:
            raise ValueError('more than two property lines changed')
        for l, r in zip(left, right):
            if l != r and not any(l == x['key'] + '=' + x['from'] + '\n' and
                                  r == x['key'] + '=' + x['to'] + '\n' for x in changed):
                raise ValueError('unreviewed property change')
        outputs.append((e, text.encode(), changed))
    a.out.mkdir(parents=True)
    records = []
    for e, data, changed in outputs:
        dst = a.out / 'files' / e['path']
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        records.append({'path': e['path'], 'input_sha256': e['input_sha256'],
                        'sha256': sha(dst), 'size': len(data), 'metadata': e['metadata'],
                        'changes': changed})
    report = {'schema': 1, 'kind': 'compatibility_probe', 'id': spec['id'], 'flashable': False,
              'runtime': 'NOT_TESTED', 'files': records, 'profile_sha256': sha(a.profile),
              'script_sha256': sha(Path(__file__)), 'only_six_identity_lines_changed': True,
              'limits': ['No hardware/import/VINTF or Android runtime execution.',
                         'New donor software fingerprints and generic qssi stay unchanged.']}
    (a.out / 'probe-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'SIX_IDENTITY_LINES_PREPARED', 'files': 3, 'flashable': False}))


if __name__ == '__main__':
    main()
