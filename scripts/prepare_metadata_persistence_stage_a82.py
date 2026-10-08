#!/usr/bin/env python3
"""Integrate reviewed A82 metadata texts into an independent A81 COW child."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
from apply_device_stage_integration_ui85 import checked, inventory, sha
SOURCE=Path('/var/tmp/ui85-a81-mainline-freeze-stage-v1/stage')
DEST=Path('/var/tmp/ui85-a82-metadata-stage-v1')
BASE_SHA='fe2db1a7dd4b777f6c644b2527f18177a5e308d67ae512376b7aed06a9713424'
REPORT_SHA='0fa61c20bc46e0e4b05ceb6995bc9fe1fc44d60c67cae8680237d56b710338f7'
HELPER_SHA='9dba3310b9c60734fd65554f119293ab569bdc6344269990341f1961cb1ca712'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if (os.uname().sysname != 'Linux' or os.geteuid() != 0 or a.out != DEST
            or a.out.exists() or not os.path.ismount(SOURCE)):
        raise ValueError('Root Linux, reviewed A81 parent and fresh A82 COW required')
    helper = Path(__file__).with_name('apply_device_stage_integration_ui85.py')
    if sha(helper) != HELPER_SHA or sha(a.baseline) != BASE_SHA:
        raise ValueError('Frozen inventory/helper differs')
    if sha(a.candidate/'report.json') != REPORT_SHA:
        raise ValueError('Frozen XML candidate report differs')
    report = json.loads((a.candidate/'report.json').read_text())
    if report['id']!='A82_PRIVATE_DATA_METADATA_CANDIDATE' or len(report['files'])!=4:
        raise ValueError('Reviewed four-text metadata candidate required')
    before=inventory(SOURCE)
    if before!=json.loads(a.baseline.read_text()) or len(before)!=8129:
        raise ValueError('Complete A81 parent identity differs')
    expected=copy.deepcopy(before)
    changes=[]
    for row in report['files']:
        target='system/'+row['path']
        original=before[target]
        payload=checked(a.candidate,'files/'+row['path'])
        restore=checked(a.candidate,'restore/'+row['path'])
        if (sha(payload)!=row['after_sha256'] or sha(restore)!=row['before_sha256']
                or original['sha256']!=row['before_sha256']
                or original['uid']!=0 or original['gid']!=0 or original['mode']!=0o100644):
            raise ValueError('Existing text/source/metadata differs: '+target)
        expected[target].update(sha256=sha(payload),size=payload.stat().st_size)
        changes.append(target)
    lowers = [Path('/var/tmp/ui85-a81-mainline-freeze-stage-v1/upper'),
              Path('/var/tmp/ui85-a80-native-product-stage-v2/upper'),
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
        for row,target_path in zip(report['files'],changes):
            original=before[target_path]
            target=checked(stage,target_path)
            payload=checked(a.candidate,'files/'+row['path'])
            target.write_bytes(payload.read_bytes())
            os.chown(target,original['uid'],original['gid'])
            os.chmod(target,original['mode'] & 0o7777)
            for name in os.listxattr(target):
                if name not in original['xattrs']: os.removexattr(target,name)
            for name,value in original['xattrs'].items():
                os.setxattr(target,name,bytes.fromhex(value))
            os.utime(target,(1640995200,1640995200))
        after = inventory(stage)
        if after != expected or inventory(SOURCE) != before:
            raise ValueError('Unexpected complete tree or parent mutation')
        (a.out/'stage-before.json').write_bytes(a.baseline.read_bytes())
        (a.out/'stage-after.json').write_text(json.dumps(after, indent=2, sort_keys=True)+'\n')
        evidence = {'schema': 1, 'id': 'A82_PRIVATE_DATA_METADATA_COW',
            'status': 'COW_STAGE_WHOLE_TREE_VERIFIED', 'stage': str(stage),
            'before_inventory_sha256': BASE_SHA,
            'after_inventory_sha256': sha(a.out/'stage-after.json'), 'entries': len(after),
            'candidate_report_sha256': REPORT_SHA, 'script_sha256': sha(Path(__file__)),
            'overlay_options': options, 'changed_existing_files': changes,
            'files_added': 0, 'files_removed': 0, 'original_a81_unchanged': True,
            'all_other_content_links_metadata_identical': True,
            'classification': 'DEVICE_REQUIRED_VERSION_SPECIFIC_METADATA_PERSISTENCE',
            'device_mutations': False, 'flashable': False, 'release': 'NOT_PASSED',
            'limits': ['DATA format removes backing; ordinary app/cache clears do not',
                       'DSU/future donor require renewed fstab and boot-stage review',
                       'Installer must handle new DATA metadata before full ROM release']}
        (a.out/'report.json').write_text(json.dumps(evidence, indent=2)+'\n')
        print(json.dumps(evidence), flush=True)
    except BaseException:
        if mounted:
            subprocess.run(['umount', stage], check=True)
        raise

if __name__ == '__main__':
    main()
