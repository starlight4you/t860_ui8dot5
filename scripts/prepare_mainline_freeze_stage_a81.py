#!/usr/bin/env python3
"""Integrate the authorized A81 XML into a verified, independent A80 COW child."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess

from apply_device_stage_integration_ui85 import checked, inventory, sha

SOURCE = Path('/var/tmp/ui85-a80-native-product-stage-v2/stage')
DEST = Path('/var/tmp/ui85-a81-mainline-freeze-stage-v1')
TARGET = 'product/etc/sysconfig/google-staged-installer-whitelist.xml'
BASE_SHA = '9cc35ef78d6a75150bbcbec194f6bb3587e1880bb5f70e2fd197581d3c44a259'
REPORT_SHA = '67c36d886aa2d621641c12ac16865ff59a0708813a53f0341d10b9e5322bb6a5'
SERVICES_SHA = '91e2a7ce17f25a84c36e70a958aa523274eb394c7f3da4f30051364871f23d22'
HELPER_SHA = '9dba3310b9c60734fd65554f119293ab569bdc6344269990341f1961cb1ca712'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if (os.uname().sysname != 'Linux' or os.geteuid() != 0 or a.out != DEST
            or a.out.exists() or not os.path.ismount(SOURCE)):
        raise ValueError('Root Linux, reviewed mounted parent and fresh named COW required')
    helper = Path(__file__).with_name('apply_device_stage_integration_ui85.py')
    if sha(helper) != HELPER_SHA or sha(a.baseline) != BASE_SHA:
        raise ValueError('Frozen inventory/helper differs')
    if sha(a.candidate/'report.json') != REPORT_SHA:
        raise ValueError('Frozen XML candidate report differs')
    report = json.loads((a.candidate/'report.json').read_text())
    payload = checked(a.candidate, TARGET)
    restore = checked(a.candidate, 'restore/'+TARGET)
    if (report['id'] != 'A81' or report['reviewed_services_sha256'] != SERVICES_SHA
            or sha(payload) != report['candidate_sha256']
            or sha(restore) != report['source_sha256'] or payload.stat().st_size != 218
            or restore.stat().st_size != 309):
        raise ValueError('Reviewed single XML bytes differ')
    before = inventory(SOURCE)
    if before != json.loads(a.baseline.read_text()) or len(before) != 8129:
        raise ValueError('Complete A80 parent identity differs')
    original = before[TARGET]
    if (original['sha256'] != report['source_sha256'] or original['size'] != 309
            or before['system/system/framework/services.jar']['sha256'] != SERVICES_SHA
            or original['uid'] != 0 or original['gid'] != 0 or original['mode'] != 0o100644
            or bytes.fromhex(original['xattrs']['security.selinux']).rstrip(b'\0')
               != b'u:object_r:system_file:s0'):
        raise ValueError('Current XML/framework/metadata differs')
    expected = copy.deepcopy(before)
    expected[TARGET].update(sha256=sha(payload), size=218)
    lowers = [Path('/var/tmp/ui85-a80-native-product-stage-v2/upper'),
              Path('/var/tmp/ui85-a79-mainline-stage-v1/upper'),
              Path('/var/tmp/ui85-a73-fcm4-stage-v1/upper'),
              Path('/var/tmp/t860-ui85-capacity-draft-app-preopt')]
    if any(not x.is_dir() or x.is_symlink() for x in lowers):
        raise ValueError('Reviewed flattened lower directories unavailable')
    a.out.mkdir(mode=0o700)
    for name in ('stage', 'upper', 'work'):
        (a.out/name).mkdir()
    stage = a.out/'stage'
    options = 'lowerdir='+':'.join(map(str, lowers))+f',upperdir={a.out}/upper,workdir={a.out}/work'
    mounted = False
    try:
        subprocess.run(['mount', '-t', 'overlay', 'overlay', '-o', options, stage], check=True)
        mounted = True
        if inventory(stage) != before:
            raise ValueError('Initial COW view differs')
        target = checked(stage, TARGET)
        target.write_bytes(payload.read_bytes())
        os.chown(target, original['uid'], original['gid'])
        os.chmod(target, original['mode'] & 0o7777)
        for name in os.listxattr(target):
            if name not in original['xattrs']:
                os.removexattr(target, name)
        for name, value in original['xattrs'].items():
            os.setxattr(target, name, bytes.fromhex(value))
        os.utime(target, (1640995200, 1640995200))
        after = inventory(stage)
        if after != expected or inventory(SOURCE) != before:
            raise ValueError('Unexpected complete tree or parent mutation')
        (a.out/'stage-before.json').write_bytes(a.baseline.read_bytes())
        (a.out/'stage-after.json').write_text(json.dumps(after, indent=2, sort_keys=True)+'\n')
        evidence = {'schema': 1, 'id': 'A81_MAINLINE_FREEZE_COW',
            'status': 'COW_STAGE_WHOLE_TREE_VERIFIED', 'stage': str(stage),
            'before_inventory_sha256': BASE_SHA,
            'after_inventory_sha256': sha(a.out/'stage-after.json'), 'entries': len(after),
            'candidate_report_sha256': REPORT_SHA, 'script_sha256': sha(Path(__file__)),
            'overlay_options': options, 'changed_existing_files': [TARGET],
            'files_added': 0, 'files_removed': 0, 'original_a80_unchanged': True,
            'all_other_content_links_metadata_identical': True,
            'classification': 'WORKAROUND_USER_SELECTED_SELECTIVE_GOOGLE_INSTALLER_FREEZE',
            'device_mutations': False, 'flashable': False, 'release': 'NOT_PASSED',
            'limits': ['Does not prove Google backend refusal or freeze ordinary module APK updates',
                       'Does not certify A79 updated network module compatibility',
                       'Future donor requires renewed framework and XML review']}
        (a.out/'report.json').write_text(json.dumps(evidence, indent=2)+'\n')
        print(json.dumps(evidence), flush=True)
    except BaseException:
        if mounted:
            subprocess.run(['umount', stage], check=True)
        raise

if __name__ == '__main__':
    main()
