#!/usr/bin/env python3
"""A61: exact S6 Codec2 policy transformation, preserving every other rule."""
import argparse, hashlib, json
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('profile', 'input', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    c = json.loads(a.profile.read_text())
    if c['id'] != 'A61' or c['path'] != 'etc/seccomp_policy/samsung.software.media.c2-base-policy' or a.output.exists():
        raise ValueError('Reviewed profile and fresh output required')
    b = a.input.read_bytes()
    if hashlib.sha256(b).hexdigest() != c['before_sha256'] or len(b) != c['before_bytes']:
        raise ValueError('Original S6 policy differs')
    old = b'\nmremap: arg3 == 3\n'
    if b.count(old) != 1:
        raise ValueError('Original rule differs')
    after = b.replace(old, b'\nmremap: arg3 == 3 || arg3 == 1\n')
    if hashlib.sha256(after).hexdigest() != c['after_sha256'] or len(after) != c['after_bytes']:
        raise ValueError('Reviewed output differs')
    with a.output.open('xb') as f:
        f.write(after)
    print(json.dumps({'id': 'A61', 'after_sha256': c['after_sha256'], 'changed_rules': 1, 'runtime': 'NOT_TESTED'}))

if __name__ == '__main__':
    main()
