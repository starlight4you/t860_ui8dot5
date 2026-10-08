#!/usr/bin/env python3
"""Apply reviewed donor-derived device patches to the isolated E2 tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

STAGE = Path('/var/tmp/t860-ui85-capacity-draft-app-preopt')
TARGETS = {'system/bin/surfaceflinger', 'system/etc/init/t860-display-compat.rc',
           'system/framework/services.jar', 'system/lib64/vendor.samsung.hardware.tlc.iccc@1.0.so',
           'system/etc/floating_feature.xml', 'system/cameradata/camera-feature.xml'}
CACHES = {'system/framework/services.jar.prof', 'system/framework/oat/arm64/services.art',
          'system/framework/oat/arm64/services.odex', 'system/framework/oat/arm64/services.vdex'}


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def checked(root, rel):
    rel = Path(rel)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise ValueError('unsafe relative path')
    p = root / rel
    for part in [p, *p.parents]:
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError('symlink component in input/target')
    return p


def meta(p):
    s = p.stat()
    return {'uid': s.st_uid, 'gid': s.st_gid, 'mode': f'{stat.S_IMODE(s.st_mode):04o}',
            'selinux': os.getxattr(p, 'security.selinux').rstrip(b'\0').decode()}


def set_meta(p, m):
    s = p.stat()
    if (s.st_uid, s.st_gid) != (m['uid'], m['gid']):
        os.chown(p, m['uid'], m['gid'])
    if stat.S_IMODE(s.st_mode) != int(m['mode'], 8):
        os.chmod(p, int(m['mode'], 8))
    try:
        label = os.getxattr(p, 'security.selinux').rstrip(b'\0').decode()
    except OSError:
        label = None
    if label != m['selinux']:
        os.setxattr(p, 'security.selinux', m['selinux'].encode())
    if meta(p) != m:
        raise ValueError('metadata readback differs')


def inventory(root):
    rows = {}
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            p = Path(parent) / name
            s = p.lstat()
            row = {'uid': s.st_uid, 'gid': s.st_gid, 'mode': s.st_mode,
                   'xattrs': {n: os.getxattr(p, n, follow_symlinks=False).hex()
                              for n in sorted(os.listxattr(p, follow_symlinks=False))}}
            if stat.S_ISLNK(s.st_mode):
                row['link'] = os.readlink(p)
            elif stat.S_ISREG(s.st_mode):
                row.update(size=s.st_size, sha256=sha(p))
            elif not stat.S_ISDIR(s.st_mode):
                raise ValueError('unexpected special file in stage')
            rows[p.relative_to(root).as_posix()] = row
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ('stage', 'project', 'bundles', 'profile', 'out'):
        p.add_argument('--' + k, type=Path, required=True)
    a = p.parse_args()
    if os.uname().sysname != 'Linux' or os.geteuid() != 0 or a.stage != STAGE:
        raise ValueError('Linux root and exact isolated E2 stage required')
    if a.out.exists() or a.out.resolve().is_relative_to(a.stage) or a.stage.is_symlink():
        raise ValueError('fresh external report required')
    spec = json.loads(a.profile.read_text())
    if spec['kind'] != 'reviewed_device_stage_integration' or spec['flashable'] is not False:
        raise ValueError('wrong integration spec')
    if not (a.stage / 'capacity-stage-log.json').is_file():
        raise ValueError('stage marker absent')
    if {e['path'] for e in spec['files']} != TARGETS or len(spec['files']) != 6:
        raise ValueError('changed target inventory')
    if {e['path'] for e in spec['remove_services_cache']} != CACHES or len(spec['remove_services_cache']) != 4:
        raise ValueError('changed cache inventory')
    for name, digest in spec['bundle_manifests'].items():
        if sha(checked(a.bundles, name + '/probe-manifest.json')) != digest:
            raise ValueError('prepared bundle manifest differs')
    for rel, digest in spec['hardware_tools_sha256'].items():
        if sha(checked(a.project, rel)) != digest:
            raise ValueError('hardware patch tool/profile differs')
    for name, digest in spec['evidence_sha256'].items():
        report = checked(a.project / 'docs/audit', name)
        if sha(report) != digest:
            raise ValueError('reviewed evidence differs')
        data = json.loads(report.read_text())
        if name.endswith('-verification.json') and data.get('all_passed') is not True:
            raise ValueError('verification did not pass')
        if name == 'services-profile-identity-ui85.json' and data['status'] != 'ORIGINAL_PROFILE_IDENTITIES_STALE_FOR_CANDIDATE':
            raise ValueError('missing specific stale profile evidence')
    for rel, digest in spec['stage_guards'].items():
        if sha(checked(a.stage, rel)) != digest:
            raise ValueError('prior B06 integration changed')
    for e in spec['files']:
        src = checked(a.bundles, e['source'])
        dst = checked(a.stage / 'system', e['path'])
        if sha(src) != e['output_sha256'] or src.stat().st_size != e['size']:
            raise ValueError('prepared payload differs')
        if not dst.parent.is_dir():
            raise ValueError('missing target parent')
        if e['original_sha256']:
            if sha(dst) != e['original_sha256'] or meta(dst) != e['metadata']:
                raise ValueError('donor target/metadata differs')
        elif dst.exists():
            raise ValueError('new init already exists')
    for e in spec['remove_services_cache']:
        dst = checked(a.stage / 'system', e['path'])
        if sha(dst) != e['sha256'] or dst.stat().st_size != e['size'] or meta(dst) != e['metadata']:
            raise ValueError('cache source differs')
    print('Inputs verified; recording whole E2 tree before changes.', flush=True)
    before = inventory(a.stage)
    a.out.mkdir(parents=True)
    (a.out / 'before.json').write_text(json.dumps(before, sort_keys=True) + '\n')
    installed, removed, delta = [], [], 0
    for e in spec['files']:
        src = checked(a.bundles, e['source'])
        dst = checked(a.stage / 'system', e['path'])
        old_size = dst.stat().st_size if dst.exists() else 0
        shutil.copyfile(src, dst)
        set_meta(dst, e['metadata'])
        if sha(dst) != e['output_sha256']:
            raise ValueError('installed content readback differs')
        delta += dst.stat().st_size - old_size
        installed.append({'path': 'system/' + e['path'], 'sha256': sha(dst),
                          'size': dst.stat().st_size, 'delta_bytes': dst.stat().st_size - old_size,
                          'metadata': meta(dst)})
    for e in spec['remove_services_cache']:
        checked(a.stage / 'system', e['path']).unlink()
        delta -= e['size']
        removed.append(e)
    print('Components installed; comparing complete content, links and metadata.', flush=True)
    after = inventory(a.stage)
    (a.out / 'after.json').write_text(json.dumps(after, sort_keys=True) + '\n')
    added = set(after) - set(before)
    deleted = set(before) - set(after)
    changed = {k for k in before.keys() & after.keys() if before[k] != after[k]}
    expected_added = {'system/system/etc/init/t860-display-compat.rc'}
    expected_removed = {'system/' + k for k in CACHES}
    expected_changed = {'system/' + k for k in TARGETS} - expected_added
    if (added, deleted, changed) != (expected_added, expected_removed, expected_changed):
        raise ValueError('whole-tree changes differ from reviewed inventory')
    for k in changed:
        left = {x: y for x, y in before[k].items() if x not in ('sha256', 'size')}
        right = {x: y for x, y in after[k].items() if x not in ('sha256', 'size')}
        if left != right:
            raise ValueError('original metadata changed')
    result = {'schema': 1, 'kind': 'device_stage_integration',
              'status': 'STAGED_COMPLETE_TREE_VERIFIED_NOT_BOOT_TESTED',
              'flashable': False, 'runtime': 'NOT_TESTED', 'files': installed,
              'removed_services_cache': removed, 'delta_apparent_bytes': delta,
              'whole_tree': {'before_entries': len(before), 'after_entries': len(after),
                             'added': sorted(added), 'removed': sorted(deleted), 'changed': sorted(changed),
                             'all_other_content_links_metadata_identical': True},
              'profile_sha256': sha(a.profile), 'script_sha256': sha(Path(__file__)),
              'before_inventory_sha256': sha(a.out / 'before.json'),
              'after_inventory_sha256': sha(a.out / 'after.json'),
              'preserved': ['all APKs and trim lists', 'other framework and ART/runtime',
                            'original donor/base tree', 'BOOT/VENDOR/ODM/DATA and device'],
              'remaining': ['T860 identity/init/other hardware bridges', 'split policy/cache IDs/real VINTF',
                            'new ART first-boot compilation and dirty upgrade',
                            'Android display/CE/ICCC/XML feature runtime']}
    (a.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'files': len(installed),
                      'removed_cache_bytes': sum(e['size'] for e in removed), 'delta_bytes': delta}))


if __name__ == '__main__':
    main()
