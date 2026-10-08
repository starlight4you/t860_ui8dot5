#!/usr/bin/env python3
"""A99 strict first-install and identical-reinstall refusal tests in pinned TWRP ARM64 userspace.

Only temporary regular-file fixtures are used. No real Android partitions,
DATA mounts, APEX signature assertions, or device reboots are involved.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

RECOVERY_SHA = 'cbc6e03563a9229b7034dd775964ef412af94a7074f50b519ce1ccc1fd4f2e16'
BINARY_SHA = '4f3f04af10250a0522b4bf2805fe0567fef975da1aea9e24024d86eba8ca8176'
TABLE_SHA = '3db9c6be68d3310e1cad7af3848a675dfef9a225504ad93c830e3ecbffb3c02a'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root):
    result = {}
    for p in [root, *sorted(root.rglob('*'))]:
        s = p.lstat()
        item = [s.st_mode, s.st_uid, s.st_gid, s.st_ino, s.st_nlink,
                s.st_size, s.st_mtime_ns, s.st_ctime_ns]
        if stat.S_ISREG(s.st_mode):
            item.append(sha(p))
        elif stat.S_ISLNK(s.st_mode):
            item.append(os.readlink(p))
        result[str(p.relative_to(root))] = item
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recovery-root', type=Path, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--factory-table', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    recovery = args.recovery_root.resolve(strict=True)
    chroot = shutil.which('chroot')
    if os.geteuid() or not chroot or (recovery / 'dev/block').exists():
        raise ValueError('isolated root chroot without block devices required')
    manifest = json.loads((recovery / 'tools-manifest.json').read_text())
    if manifest['recovery_sha256'] != RECOVERY_SHA:
        raise ValueError('original fixed TWRP root required')
    for path, expected in [(args.binary, BINARY_SHA), (args.factory_table, TABLE_SHA)]:
        if path.is_symlink() or not path.is_file() or sha(path) != expected:
            raise ValueError('reviewed input identity mismatch')
    if args.out.exists():
        raise ValueError('fresh report required')
    cases = []
    with tempfile.TemporaryDirectory(prefix='a71-mainline-test-', dir=recovery / 'tmp') as temporary:
        work = Path(temporary)
        binary = work / 'mainline-guard'
        shutil.copyfile(args.binary, binary)
        binary.chmod(0o755)

        def inside(path):
            return '/' + path.relative_to(recovery).as_posix()

        def run(name, setup=lambda root: None, expected=1, extra_sessions=False, preserve=False, upgrade=False, apply=False):
            root = work / name
            root.mkdir()
            (root / 'active').mkdir()
            (root / 'sessions').mkdir()
            shutil.copyfile(args.factory_table, root / 'factory.tsv')
            setup(root)
            before = snapshot(root)
            argv = [chroot, str(recovery), inside(binary), inside(root / 'factory.tsv'),
                    inside(root / 'active'), inside(root / 'sessions')]
            if upgrade:
                argv.insert(3, '--upgrade-hold' if apply else '--upgrade-preflight')
            if preserve:
                argv.insert(3, '--identical-system-reinstall')
            if extra_sessions:
                argv.append(inside(root / 'sessions2'))
            r = subprocess.run(argv, capture_output=True, text=True, timeout=5)
            after=snapshot(root)
            readonly=not apply or expected!=0
            if apply and expected==0:
                preserved={k+('.A99-held' if k.startswith('active/') and k.endswith('.apex') else ''):v for k,v in before.items()}
                if set(preserved)!=set(after):raise AssertionError('Unexpected backup members')
                for name,old in preserved.items():
                    now=after[name]
                    if stat.S_ISREG(old[0]) and (old[:7]!=now[:7] or old[8:]!=now[8:]):raise AssertionError('Encrypted inode/content/owner/mode/size changed')
            if r.returncode != expected or (readonly and after != before):
                raise AssertionError(f'{name}: return={r.returncode}, expected={expected}, '
                                     f'output={r.stdout!r} {r.stderr!r}; readonly={snapshot(root) == before}')
            cases.append({'case': name, 'pass': True, 'expected_exit': expected,
                          'actual_exit': r.returncode, 'fixture_unchanged': readonly, 'inode_preserving_module_backup':apply and expected==0,
                          'stdout': r.stdout.strip(), 'stderr': r.stderr.strip()})

        def session(root, data, kind='regular'):
            p = root / 'sessions/123'
            p.mkdir()
            if kind == 'fifo':
                os.mkfifo(p / 'state')
            elif kind == 'symlink':
                (root / 'valid-state').write_bytes(data)
                (p / 'state').symlink_to('../../valid-state')
            else:
                (p / 'state').write_bytes(data)

        run('empty-active-and-sessions', expected=0)
        for value in (1, 3, 4, 5, 7):
            run(f'terminal-or-non-staged-state-{value}',
                lambda r, v=value: session(r, bytes([8, 123, 16, v])), expected=0)
        for value in (0, 2, 6, 8, 9):
            run(f'unknown-staged-or-unresolved-state-{value}',
                lambda r, v=value: session(r, bytes([8, 123, 16, v])))
        for name, data in [
            ('missing-state-field', b'\x08\x7b'),
            ('duplicate-state-field', b'\x10\x03\x10\x03'),
            ('truncated-varint', b'\x10\x80'),
            ('overflow-varint', b'\x10' + b'\xff' * 10),
            ('wrong-state-wire', b'\x12\x01\x03'),
            ('unsupported-wire', b'\x13'),
            ('truncated-unknown-field', b'\x10\x03\x22\x04\x00'),
            ('empty-state', b''),
            ('oversized-state', b'\x10\x03' + b'\x00' * 1048576),
        ]:
            run(name, lambda r, b=data: session(r, b))
        run('unknown-fields-skipped', lambda r: session(r, b'\x08\x7b\x10\x03\x22\x02ok'), expected=0)
        run('fifo-state-refused-without-blocking', lambda r: session(r, b'', 'fifo'))
        run('symlink-state', lambda r: session(r, b'\x10\x03', 'symlink'))
        run('symlink-session', lambda r: (r / 'sessions/123').symlink_to('../active'))
        run('non-numeric-session', lambda r: (r / 'sessions/bad').mkdir())
        run('session-id-overflow', lambda r: (r / 'sessions/2147483648').mkdir())
        run('regular-file-session', lambda r: (r / 'sessions/123').write_bytes(b'bad'))
        for name, filename in [
            ('filename-older-does-not-prove-content', 'com.android.tethering@1.apex'),
            ('filename-equal', 'com.android.tethering@361153320.apex'),
            ('filename-newer', 'com.android.tethering@372038420.apex'),
            ('unknown-active-module', 'unknown.module@1.apex'),
            ('unversioned-active', 'com.android.tethering.apex'),
            ('duplicate-version-delimiter', 'com.android.tethering@1@2.apex'),
        ]:
            run(name, lambda r, f=filename: (r / 'active' / f).write_bytes(b'unverified payload'))
        run('retained-not-apex-suffix', lambda r: (r / 'active/com.android.tethering@372038420.apex.A70-held').write_bytes(b'retained'), expected=0)
        run('symlink-active-file', lambda r: (r / 'active/com.android.tethering@1.apex').symlink_to('../factory.tsv'))
        run('directory-active-file', lambda r: (r / 'active/com.android.tethering@1.apex').mkdir())

        def replace_with_link(root, target):
            (root / target).rmdir()
            (root / target).symlink_to('sessions' if target == 'active' else 'active')
        run('symlink-active-directory', lambda r: replace_with_link(r, 'active'))
        run('symlink-sessions-directory', lambda r: replace_with_link(r, 'sessions'))
        run('second-session-root-staged', lambda r: [(r / 'sessions2/456').mkdir(parents=True),
            (r / 'sessions2/456/state').write_bytes(b'\x10\x02')], extra_sessions=True)
        for name, text in [('duplicate-table', 'module\t1\nmodule\t2\n'),
                           ('unterminated-table', 'module\t1'),
                           ('zero-version-table', 'module\t0\n'),
                           ('empty-table', ''), ('invalid-name-table', 'module/bad\t1\n')]:
            run(name, lambda r, t=text: (r / 'factory.tsv').write_text(t))

        retained = [('com.android.adservices@372038020.apex',22716416),
                    ('com.android.ondevicepersonalization@372038020.apex',14999552),
                    ('com.android.os.statsd@372040000.apex',3825664),
                    ('com.android.tzdata@372038420.apex',929792)]
        def retained_set(root):
            for name,size in retained:
                path=root/'active'/name
                with path.open('wb') as f:f.truncate(size)
                path.chmod(0o644);os.chown(path,1000,1000)
        run('reinstall-empty', expected=0, preserve=True)
        run('reinstall-exact-observed-set', retained_set, expected=0, preserve=True)
        def changed(root, action):
            retained_set(root);action(root/'active'/retained[0][0])
        run('reinstall-partial-refused',lambda r:changed(r,lambda p:p.unlink()),preserve=True)
        run('reinstall-size-refused',lambda r:changed(r,lambda p:p.write_bytes(b'x')),preserve=True)
        run('reinstall-owner-refused',lambda r:changed(r,lambda p:os.chown(p,0,0)),preserve=True)
        run('reinstall-mode-refused',lambda r:changed(r,lambda p:p.chmod(0o600)),preserve=True)
        run('reinstall-unknown-file-refused',lambda r:(r/'active/unknown').write_bytes(b'x'),preserve=True)
        run('reinstall-symlink-refused',lambda r:(r/'active'/retained[0][0]).symlink_to('../factory.tsv'),preserve=True)
        run('reinstall-pending-session-refused',lambda r:session(r,b'\x08\x7b\x10\x02'),preserve=True)
        run('reinstall-terminal-session',lambda r:session(r,b'\x08\x7b\x10\x03'),expected=0,preserve=True)
        run('reinstall-secondary-pending-refused',lambda r:[(r/'sessions2/456').mkdir(parents=True),(r/'sessions2/456/state').write_bytes(b'\x10\x02')],extra_sessions=True,preserve=True)

        def old_active(root,name='com.android.tethering@372038420.apex'):
            path=root/'active'/name;path.write_bytes(b'opaque FBE module fixture');path.chmod(0o644);os.chown(path,1000,1000)
            (root/'user-state-sentinel').write_bytes(b'credential and account state unchanged')
        run('ui8-upgrade-empty-preflight',expected=0,upgrade=True)
        run('ui8-upgrade-opaque-module-preflight',old_active,expected=0,upgrade=True)
        run('ui8-upgrade-holds-opaque-module-inode',old_active,expected=0,upgrade=True,apply=True)
        run('ui8-upgrade-holds-all-known-modules',retained_set,expected=0,upgrade=True,apply=True)
        run('ui8-upgrade-unknown-module-refused',lambda r:old_active(r,'unknown.module@1.apex'),upgrade=True,apply=True)
        run('ui8-upgrade-staged-refused',lambda r:(old_active(r),session(r,b'{')),upgrade=True,apply=True)
        run('ui8-upgrade-backup-collision-refused',lambda r:(old_active(r),old_active(r,'com.android.tethering@372038420.apex.A99-held')),upgrade=True,apply=True)
        run('ui8-upgrade-symlink-refused',lambda r:(r/'active/com.android.tethering@1.apex').symlink_to('../factory.tsv'),upgrade=True,apply=True)
        run('ui8-upgrade-wrong-owner-refused',lambda r:(old_active(r),os.chown(r/'active/com.android.tethering@372038420.apex',0,0)),upgrade=True,apply=True)
        run('ui8-upgrade-existing-backup-retained',lambda r:old_active(r,'com.android.tethering@372038420.apex.A67-held'),expected=0,upgrade=True,apply=True)
        run('reinstall-old-backup-retained',lambda r:old_active(r,'com.android.tethering@372038420.apex.A99-held'),expected=0,preserve=True)

        def table_fifo(root):
            (root / 'factory.tsv').unlink()
            os.mkfifo(root / 'factory.tsv')
        run('fifo-table-refused-without-blocking', table_fifo)
        report = {'id': 'A99_MAINLINE_GUARD_TESTS', 'all_passed': True,
                  'scope': 'pinned TWRP ARM64 userspace on Linux VM kernel; no real partitions',
                  'binary_sha256': BINARY_SHA, 'factory_table_sha256': TABLE_SHA,
                  'recovery_sha256': RECOVERY_SHA, 'test_source_sha256': sha(Path(__file__)),
                  'cases': cases, 'case_count': len(cases), 'device_writes': False,
                  'real_recovery_runtime': 'NOT_TESTED',
                  'limits': ['Caller must verify real DATA/CACHE mounts before interpreting absent directories.',
                             'First installation refuses active APEX; identical-system mode preserves only the observed four-entry set without claiming content validation.',
                             'Does not prevent future automatic module updates or validate dirty-upgrade boot.']}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({k: v for k, v in report.items() if k != 'cases'}))


if __name__ == '__main__':
    main()
