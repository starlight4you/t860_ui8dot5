#!/usr/bin/env python3
"""Export the exact tested A98 SYSTEM/PRODUCT as an A99 phase release.

Linux root; original device and snapshot files are never modified. This does
not relax the stable 256MiB SYSTEM target: this phase build records it as failed
and separately enforces the previously used 64MiB lab margin.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from zipfile import ZipFile,ZIP_DEFLATED
import build_twrp_upgrade as transport
from apply_device_stage_integration_ui85 import inventory
import render_twrp_full_release_a99 as renderer
import release_deflate

PINS = {
    'system': 'c2c249d94e4028ba3c550bb4a51fe2c3397bf80f4f8b9f82ad8236f3ed2340a8',
    'product': 'bd1e4f1598ccfc8b24890e97b3562e1941ebd27c17b284491c8965981db45aa7',
    'boot':'523664a8caf6b403526efa6e3b77e8645cc6f84a7573ff7e39159fa9b36843e9',
    'vendor':'609f5098f0bc469bf3377555beef3ed7e64be6df61dbc260d42f2f4d6f6a0e18',
    'dtbo':'864ca763a1362a77aa929c3e2f147baa70196c31401b52f76bf0f879d7eb99ec',
    'vbmeta':'ca34476b4becde2fb643b04040f19cd1b0e5ea4a3eb6ebeeeeff47dc97d50d54',
}

SIZES={**transport.SIZES,'boot':67108864,'vendor':1379926016,'dtbo':10485760,'vbmeta':65536}
MIN_FREE={**transport.MIN_FREE,'vendor':64*1024**2}

def audit(part, path):
    minimum = 64*1024**2 if part == 'system' else 100*1024**2
    if path.is_symlink() or path.stat().st_size != SIZES[part]:
        raise ValueError('Wrong partition input: '+part)
    if part in ('boot','dtbo','vbmeta'):
        magic=path.open('rb').read(8)
        wanted={'boot':b'ANDROID!','dtbo':bytes.fromhex('d7b7ab1e'),'vbmeta':b'AVB0'}[part]
        if not magic.startswith(wanted):raise ValueError('Hardware header differs')
        return {'bytes':path.stat().st_size,'sha256':transport.sha_file(path),'source':'EXACT_CURRENT_AND_V0481_S6_HARDWARE'}
    proc = subprocess.run(['e2fsck','-fn',str(path)], capture_output=True,text=True)
    if proc.returncode:
        raise ValueError('Readonly filesystem check failed: '+proc.stdout+proc.stderr)
    text = transport.command('dumpe2fs','-h',str(path))
    fields = dict(line.split(':',1) for line in text.splitlines() if ':' in line)
    size = int(fields['Block size']); blocks = int(fields['Block count'])
    free = (int(fields['Free blocks'])-int(fields['Reserved block count']))*size
    features = fields['Filesystem features'].split()
    if size != 4096 or size*blocks != SIZES[part] or free < minimum:
        raise ValueError('Phase capacity/layout failure: '+part)
    if {'64bit','metadata_csum','metadata_csum_seed','orphan_file','bigalloc'} & set(features):
        raise ValueError('Unvalidated S6 ext4 features')
    return {'bytes':path.stat().st_size,'sha256':transport.sha_file(path),
            'free_bytes':free,'phase_minimum_free_bytes':minimum,
            'stable_minimum_free_bytes':MIN_FREE[part],
            'stable_capacity_pass':free>=MIN_FREE[part],
            'e2fsck_exit':proc.returncode,'e2fsck_log':proc.stdout+proc.stderr,
            'ext4_features':features}

ROOT=Path(__file__).resolve().parents[1]
CHUNK_BYTES=transport.CHUNK_BYTES
ZIP32_LIMIT=transport.ZIP32_LIMIT
PROFILE=transport.PROFILE
def zip_entry(name,executable=False):
    info=transport.zip_entry(name,executable)
    info._compresslevel=9
    return info
sha_file=transport.sha_file
a71_support=transport.a71_support

def write_package(output: Path, images: dict[str, Path], manifest: dict,
                  audits: dict, chunk_bytes: int = CHUNK_BYTES, operation: str = 'upgrade',
                  support_provider=None) -> dict:
    """Writer also used with small file fixtures; production CLI uses 64 MiB."""
    if output.exists() or output.with_suffix('.zip.partial').exists():
        raise ValueError('output already exists')
    if chunk_bytes % 4096:
        raise ValueError('chunk size must be block-aligned')
    library, support, adaptation_profile = (support_provider or a71_support)(manifest, operation)
    library_sha = hashlib.sha256(library).hexdigest()
    installer = (ROOT / 'installer/update-binary').read_text()
    if installer.count('@@LIBRARY_SHA@@') != 1:
        raise ValueError('expected one library SHA marker')
    installer = installer.replace('@@LIBRARY_SHA@@', library_sha)
    installer = installer.replace('for entry in upgrade.tsv system.chunks product.chunks; do','for entry in upgrade.tsv system.chunks product.chunks boot.chunks vendor.chunks dtbo.chunks vbmeta.chunks; do')
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix('.zip.partial')
    tables = {}
    previous_limit=zipfile.ZIP64_LIMIT
    zipfile.ZIP64_LIMIT=ZIP32_LIMIT
    try:
        with zipfile.ZipFile(partial,'w',compression=ZIP_DEFLATED,compresslevel=9,allowZip64=False) as archive:
            archive.writestr(zip_entry('META-INF/com/google/android/update-binary', True), installer)
            archive.writestr(zip_entry('META-INF/com/google/android/updater-script'),
                             '# Installation uses the bundled TWRP API 3 shell updater.\n')
            archive.writestr(zip_entry('rom/libupgrade.sh'), library)
            for name, data in support.items():
                archive.writestr(zip_entry('rom/support/' + name, name.endswith('guard')), data)
            for part in ('system','product','boot','vendor','dtbo','vbmeta'):
                path = images[part]
                rows = []
                digest = hashlib.sha256()
                offset = 0
                for index, data, encoded in release_deflate.chunks(path, chunk_bytes):
                        if index != len(rows): raise ValueError('Chunk order differs')
                        member = f'payload/{part}/{index:04d}.img'
                        block_sha = hashlib.sha256(data).hexdigest()
                        rows.append((index, offset // 4096, len(data), block_sha, member))
                        release_deflate.write(archive, zip_entry(member), data, encoded)
                        digest.update(data)
                        offset += len(data)
                        print(f'{part}: {index+1} chunks, compressed ZIP {archive.fp.tell()} bytes', flush=True)
                if digest.hexdigest() != audits[part]['sha256'] or offset != audits[part]['bytes']:
                    raise ValueError(f'{part}: source image changed during packaging')
                tables[part] = rows
                table = ''.join('\t'.join(map(str, row)) + '\n' for row in rows)
                archive.writestr(zip_entry(f'rom/{part}.chunks'), table)
            config = {'format': '1', 'target': 'SM-T860', 'target_sdk': '36',
                      'target_oneui': '80500', 'donor_build': 'X710XXS6EZH3',
                      'data_policy': 'PRESERVE'}
            if adaptation_profile:
                config['format'] = adaptation_profile.get('format', '2')
                if config['format'] not in ('2', '3'):
                    raise ValueError('unreviewed adaptation format')
                config['adaptation'] = adaptation_profile['adaptation']
            if operation == 'restore-a70':
                config['mode'] = 'A70_STABLE_SNAPSHOT'
            for part in tables:
                config[f'{part}.sha256'] = audits[part]['sha256']
                config[f'{part}.chunk_count'] = str(len(tables[part]))
            archive.writestr(zip_entry('rom/upgrade.tsv'),
                             ''.join(f'{key}\t{value}\n' for key, value in config.items()))
            embedded = {'rom_manifest': manifest, 'image_audits': audits,
                        'profile': json.loads(PROFILE.read_text()), 'chunk_bytes': chunk_bytes,
                        'dirty_upgrade_runtime': 'NOT_TESTED', 'hardware_runtime': 'NOT_TESTED',
                        'installer_library_sha256': library_sha}
            embedded['operation'] = operation
            if adaptation_profile:
                embedded['installer_adaptation_profile'] = adaptation_profile
                embedded['support_member_sha256'] = {
                    'rom/support/' + name: hashlib.sha256(data).hexdigest()
                    for name, data in support.items()}
                if support_provider is None:
                    embedded['common_library_sha256'] = sha_file(ROOT / 'installer/libupgrade.sh')
                    embedded['vendor_library_sha256'] = sha_file(ROOT / 'installer/libvendor.sh')
                    embedded['a71_library_template_sha256'] = sha_file(ROOT / 'installer/libupgrade-a71.sh')
                else:
                    embedded['library_sources'] = adaptation_profile['library_sources']
            archive.writestr(zip_entry('rom/manifest.json'), json.dumps(embedded, indent=2) + '\n')
        if partial.stat().st_size > ZIP32_LIMIT:
            raise ValueError('ZIP exceeds pinned TWRP ZIP32 limit; payload/capacity plan required')
        # Check CRC and exact member inventory, not just ZIP central-directory size.
        with ZipFile(partial) as archive:
            failed = archive.testzip()
            if failed:
                raise ValueError(f'ZIP integrity failed: {failed}')
            members = archive.namelist()
            expected = {'META-INF/com/google/android/update-binary',
                        'META-INF/com/google/android/updater-script', 'rom/libupgrade.sh',
                        'rom/system.chunks', 'rom/product.chunks', 'rom/boot.chunks', 'rom/vendor.chunks', 'rom/dtbo.chunks', 'rom/vbmeta.chunks', 'rom/upgrade.tsv', 'rom/manifest.json'}
            expected.update(row[4] for rows in tables.values() for row in rows)
            expected.update('rom/support/' + name for name in support)
            if set(members) != expected or len(members) != len(expected):
                raise ValueError('unexpected or duplicate ZIP entries')
        os.replace(partial, output)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    finally:
        zipfile.ZIP64_LIMIT=previous_limit
    return {'zip_bytes': output.stat().st_size, 'zip_sha256': sha_file(output),
            'chunk_count': {part: len(rows) for part, rows in tables.items()},
            'zip_format': 'ZIP32_NO_ZIP64', 'contains_userdata_payload': False, 'runtime': 'NOT_TESTED',
            'installer_format': adaptation_profile.get('format', '2') if adaptation_profile else '1',
            'installer_library_sha256': library_sha,
            'support_members': sorted('rom/support/' + name for name in support)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--tools',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if os.uname().sysname!='Linux' or os.geteuid() or a.out.exists() or a.out.is_symlink():
        raise ValueError('Linux root and fresh release output required')
    if shutil.disk_usage(a.out.parent).free < 5*1024**3:
        raise ValueError('Insufficient release output space')
    images={part:a.snapshot/(part+'.raw.img') for part in PINS}
    for part,path in images.items():
        if transport.sha_file(path)!=PINS[part]:raise ValueError('Unreviewed snapshot '+part)
    tools={n:(a.tools/n).read_bytes() for n in ('mainline-guard','fscrypt-readonly-probe')}
    if not all(b[:7]==b'\x7fELF\x02\x01\x01' for b in tools.values()):
        raise ValueError('AArch64 ELF support required')
    tool_report=json.loads((a.tools/'report.json').read_text())
    for n,b in tools.items():
        if hashlib.sha256(b).hexdigest()!=tool_report['sha256'][n]:raise ValueError('Support changed')
    audits={part:audit(part,path) for part,path in images.items()}
    transport.check_device_layer(images['system'])
    a.out.mkdir(mode=0o755)
    # Independently inspect whole filesystem metadata and any personal trust
    # additions. No Android DATA or cached runtime files are image inputs.
    with tempfile.TemporaryDirectory(prefix='ui85-a99-export-') as tmp:
        root=Path(tmp)
        for part in ('system','product','vendor'):
            path=images[part]
            mount=root/part; mount.mkdir()
            subprocess.run(['mount','-o','loop,ro,noload',str(path),str(mount)],check=True)
            try:
                tree=inventory(mount)
                (a.out/(part+'-inventory.json')).write_text(json.dumps(tree,sort_keys=True,indent=2)+'\n')
                for name in ('etc/security/adb_keys','system/etc/security/adb_keys'):
                    if name in tree:
                        raise ValueError('Personal ADB trust payload present; prepare a reviewed clean copy before export')
                if part=='product' and any('/apex/' in '/'+n+'/' for n in tree):
                    raise ValueError('PRODUCT APEX requires independent source/target content proof')
                if part=='system':
                    expected={'system/etc/floating_feature.xml':'81d9eaa54326e26de4ff69c31ffca7cd07cb75298fe50b15d258cb40d48e4071',
                              'system/lib64/libsnap_aidl.snap.samsung.so':'4955b47f2ccb4c6c5741fff97df3499d0964dd64d7ff81f1ddbd441f4ee58f77',
                              'system/priv-app/PhotoEditor_AIFull/PhotoEditor_AIFull.apk':'e02149bd0e5b0e6ff7e0ead3166dbfc775cae9773df82006ed90c57f6428d348'}
                    if any(tree.get(n,{}).get('sha256')!=v for n,v in expected.items()):
                        raise ValueError('Live fix closure differs')
            finally:
                subprocess.run(['umount',str(mount)],check=True)
    manifest={'schema':1,'kind':'rom_candidate','candidate_id':'A99-SM-T860-S9-UI85-PHASE-20261008',
              'target':'SM-T860','donor_build':'X710XXS6EZH3','version':'v1.0.0',
              'partitions':{n:{'path':f'{n}.raw.img','bytes':audits[n]['bytes'],'sha256':PINS[n]} for n in images},
              'release_status':'RELEASE',
              'system_files_changed':False,'product_factory_apex_changed':False,
              'data_policy':'PRESERVE_NO_FORMAT_NO_DELETE',
              'hardware_policy':'CLEAN_BOOTSTRAPS_S6_ONLY_UI8_UPGRADE_PRESERVES_HARDWARE_WITH_TWO_TEXT_CONFIG_TRANSACTION',
              'source_inventory_sha256':transport.sha_file(a.out/'system-inventory.json'),
              'image_audits':audits,'runtime_evidence':'A98 JPEG OCR, sketch generation and rotate outpainting passed',
              'new_complete_package_flash_test':'NOT_PERFORMED',
              'first_install':'S6_DWH1_STOCK_PLUS_TWRP_OR_AUDITED_S6_PROJECT_HARDWARE_CLEAN_DATA',
              'data_preserving_reinstall':'EXACT_SAME_TARGET_SYSTEM_ONLY','data_preserving_ui8_upgrade':'SUPPORTED_V0481_ICE_FBE_WITH_OLD_MODULE_INODE_BACKUP','upgrade_runtime_user_report':'USER_CONFIRMED_PASSED_20261008','clean_flash_on_device':'PROHIBITED_BY_USER',
              'known_limits':['SYSTEM below 256MiB stable margin; above 64MiB phase margin',
                 'Document edge detection and perspective correction unavailable',
                 'Full AI/portrait and full hardware validation matrix incomplete',
                 'Galaxy Store application-scoped catalog configuration is DATA state, not included',
                 'Clean-install execution validated only with isolated fixtures; no device DATA format performed'],
              'support_source_sha256':tool_report['source_sha256']}
    (a.out/'rom-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    def support_provider(m,operation):
        if operation!='upgrade':raise ValueError('Wrong operation')
        return renderer.support(m,tools)
    output=a.out/'TabS6-S9-OneUI8.5-v1.0.0-TWRP.zip'
    result=write_package(output,images,manifest,audits,support_provider=support_provider)
    result['version']=manifest['version'];result['full_flash_test']='NOT_PERFORMED'
    (a.out/'package-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    (a.out/(output.name+'.sha256')).write_text(result['zip_sha256']+'  '+output.name+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
