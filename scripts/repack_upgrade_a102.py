#!/usr/bin/env python3
"""Fix only the released A100 upgrade installer; reuse exact compressed images."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile
import release_deflate
import render_twrp_upgrade_a102 as renderer

ROOT=Path(__file__).resolve().parents[1]
SOURCE_SHA='601fc2b993bddad88344cced5c73335ed7be7e44da2cbdc6cf043a3a4e6a9bbf'
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def digest(data): return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','probe','guard','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists() or sha(a.source)!=SOURCE_SHA:raise ValueError('Fresh output and exact released ZIP required')
    guard=a.guard.read_bytes();probe=a.probe.read_bytes()
    if digest(probe)!='027ca8d7b174c589e18bde6569e422e7f2ba21cebe22502840550339e08ef41e':raise ValueError('Access probe differs')
    a.out.mkdir(parents=True)
    target=a.out/'TabS6-OneUI8.5-v1.0.1-A102-Upgrade-TWRP.zip';partial=target.with_suffix('.zip.partial')
    blocks={};counts={};parts={name:hashlib.sha256() for name in ('system','product')}
    with zipfile.ZipFile(a.source) as src, a.source.open('rb') as stream:
        oldlib=src.read('rom/libupgrade.sh');newlib=renderer.derive(oldlib,probe,guard)
        newlib=newlib.replace(b'v1.0.1 A100 data-preserving upgrade',b'v1.0.1 A102 data-preserving upgrade').replace(b'A100_UPGRADE_PREFLIGHT_PASS:',b'A102_UPGRADE_PREFLIGHT_PASS:').replace(b'A100 upgrade verified.',b'A102 upgrade verified.')
        library_sha=digest(newlib)
        updater=src.read('META-INF/com/google/android/update-binary')
        if updater.count(renderer.A100_LIBRARY.encode())!=1:raise ValueError('Updater pin differs')
        updater=updater.replace(renderer.A100_LIBRARY.encode(),library_sha.encode())
        manifest=json.loads(src.read('rom/manifest.json'))
        for part in parts:
            table=src.read('rom/'+part+'.chunks').decode().splitlines()
            counts[part]=len(table)
            for line in table:
                index,offset,size,h,name=line.split('\t');blocks[name]=(part,int(size),h)
        manifest['installer_library_sha256']=library_sha
        manifest['support_member_sha256']['rom/support/mainline-guard']=digest(guard)
        manifest['support_member_sha256']['rom/support/upgrade-access-probe']=digest(probe)
        spec=manifest['installer_adaptation_profile']
        spec['id']='A102_UPGRADE_GUARD_CAPABILITY_FIX'
        spec['library_sources']['scripts/render_twrp_upgrade_a102.py']=sha(ROOT/'scripts/render_twrp_upgrade_a102.py')
        manifest['library_sources']=spec['library_sources']
        manifest['installer_hotfix']={'id':'A102','from_package_sha256':SOURCE_SHA,'original_guard_sha256':renderer.OLD_GUARD,'fixed_guard_sha256':digest(guard),'payload_images_changed':False,'source_guard_removed':False,'data_access_or_session_guard_bypassed':False}
        changed={'META-INF/com/google/android/update-binary':updater,'rom/libupgrade.sh':newlib,'rom/support/mainline-guard':guard,'rom/manifest.json':(json.dumps(manifest,indent=2)+'\n').encode()}
        limit=zipfile.ZIP64_LIMIT;zipfile.ZIP64_LIMIT=2**32-1
        try:
            with zipfile.ZipFile(partial,'w',compression=zipfile.ZIP_DEFLATED,allowZip64=False) as dst:
                for info in src.infolist():
                    if info.filename in changed:
                        dst.writestr(info,changed[info.filename]);continue
                    raw=src.read(info)
                    if info.filename in blocks:
                        part,size,h=blocks[info.filename]
                        if len(raw)!=size or digest(raw)!=h:raise ValueError('Payload differs: '+info.filename)
                        parts[part].update(raw)
                        stream.seek(info.header_offset);header=stream.read(30)
                        if header[:4]!=b'PK\x03\x04' or info.compress_type!=zipfile.ZIP_DEFLATED:raise ValueError('Wrong local header')
                        name_size,extra_size=struct.unpack_from('<HH',header,26);stream.seek(name_size+extra_size,1)
                        encoded=stream.read(info.compress_size)
                        if len(encoded)!=info.compress_size:raise ValueError('Truncated compressed stream')
                        release_deflate.write(dst,info,raw,encoded)
                        print('Copied verified payload '+info.filename,flush=True)
                    else:dst.writestr(info,raw)
                dst.writestr('rom/support/upgrade-access-probe',probe)
            for part,h in parts.items():
                if h.hexdigest()!=manifest['image_audits'][part]['sha256']:raise ValueError('Complete partition differs')
            with zipfile.ZipFile(partial) as check:
                if check.testzip():raise ValueError('Output CRC failed')
                for name,expected in manifest['support_member_sha256'].items():
                    if digest(check.read(name))!=expected:raise ValueError('Output support differs')
            partial.rename(target)
        finally:zipfile.ZIP64_LIMIT=limit
    report={'id':'A102_INSTALLER_HOTFIX','source_zip_sha256':SOURCE_SHA,'zip_sha256':sha(target),'zip_bytes':target.stat().st_size,'installer_library_sha256':library_sha,'payload_chunks_verified':counts,'complete_image_sha256':{part:h.hexdigest() for part,h in parts.items()},'changed_existing_members':sorted(changed),'added_member':'rom/support/upgrade-access-probe','data_payloads':False,'source_checks_removed':False,'full_flash_runtime':'NOT_TESTED'}
    (a.out/'package-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.out/'SHA256SUMS').write_text(report['zip_sha256']+'  '+target.name+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
