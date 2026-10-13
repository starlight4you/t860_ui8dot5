#!/usr/bin/env python3
"""Real ARM64 probe tests in isolated original Recovery; no device blocks."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','bundle','out'): p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if os.geteuid() or a.out.exists() or (a.root/'dev/block').exists(): raise ValueError('Root, no blocks, fresh output required')
    if json.loads((a.root/'tools-manifest.json').read_text())['recovery_sha256']!='cbc6e03563a9229b7034dd775964ef412af94a7074f50b519ce1ccc1fd4f2e16': raise ValueError('Wrong Recovery')
    a.out.mkdir(parents=True)
    result=[]
    with tempfile.TemporaryDirectory(prefix='a102-readonly-test-',dir=a.root/'tmp') as tmp:
        work=Path(tmp); inside='/'+work.relative_to(a.root).as_posix()
        probe=work/'probe';shutil.copyfile(a.bundle/'upgrade-access-probe',probe);probe.chmod(0o755)
        with zipfile.ZipFile(a.bundle/'TabS6-Upgrade-Check-A102.zip') as z:
            updater=work/'updater.sh';updater.write_bytes(z.read('META-INF/com/google/android/update-binary'))
            table=work/'factory.tsv';table.write_bytes(z.read('support/apex-factory.tsv'))
            guard=work/'guard';guard.write_bytes(z.read('support/mainline-guard'));guard.chmod(0o755)
        candidate=work/'candidate.sh';shutil.copyfile(a.bundle/'libupgrade-a102-candidate.sh',candidate)
        for script in (updater,candidate):
            r=subprocess.run(['chroot',str(a.root),'/sbin/sh','-n','/'+script.relative_to(a.root).as_posix()],capture_output=True,text=True)
            if r.returncode:raise ValueError('Original shell syntax failed: '+r.stderr)
        available=work/'available';available.mkdir();(available/'public-module-fixture').write_bytes(b'not user data')
        denied=work/'denied';denied.mkdir();denied.chmod(0)
        link=work/'link';link.symlink_to(available)
        file=work/'regular-file';file.write_text('not a directory')
        for name,path,expected,marker in [('readable',available,0,'READABLE'),('absent',work/'missing',0,'ABSENT'),('symlink',link,1,'UNAVAILABLE'),('regular-file',file,1,'UNAVAILABLE'),('permission-denied',denied,1,'errno=13')]:
            prefix=['setpriv','--bounding-set=-dac_override,-dac_read_search'] if name=='permission-denied' else []
            r=subprocess.run(prefix+['chroot',str(a.root),inside+'/probe','/'+path.relative_to(a.root).as_posix()],capture_output=True,text=True)
            if r.returncode!=expected or marker not in r.stdout:raise ValueError(name+' failed: '+r.stdout+r.stderr)
            result.append({'case':name,'exit':r.returncode,'expected_marker':marker,'passed':True})
        denied.chmod(0o700)
        active=work/'active';active.mkdir();sessions=work/'sessions';sessions.mkdir()
        def guard_case(name,expected,marker):
            r=subprocess.run(['chroot',str(a.root),inside+'/guard','--upgrade-preflight',inside+'/factory.tsv',inside+'/active',inside+'/sessions'],capture_output=True,text=True)
            if r.returncode!=expected or marker not in r.stdout+r.stderr:raise ValueError(name+' failed: '+r.stdout+r.stderr)
            result.append({'case':name,'exit':r.returncode,'expected_marker':marker,'passed':True})
        guard_case('empty-module-state',0,'PASS:')
        session=sessions/'123';session.mkdir();(session/'state').write_bytes(b'\x10\x02')
        guard_case('pending-session-refused',1,'staged, unresolved rollback, or unreadable session')
        (session/'state').write_bytes(b'\x10\x04')
        guard_case('applied-session-readable',0,'PASS:')
        (session/'state').unlink();session.rmdir()
        module=active/'com.android.tethering@372038420.apex';module.write_bytes(b'public opaque module fixture');module.chmod(0o644);os.chown(module,1000,1000)
        before=(module.stat().st_ino,module.read_bytes())
        guard_case('preflight-preserves-module-inode',0,'eligible for inode-preserving backup')
        if before!=(module.stat().st_ino,module.read_bytes()) or len(list(active.iterdir()))!=1:raise ValueError('Preflight mutated module')
    report={'id':'A102_ORIGINAL_RECOVERY_READONLY_TESTS','passed':len(result),'cases':result,'updater_and_candidate_shell_syntax':'PASS','device_blocks_present':False,'module_mutations':False}
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__': main()
