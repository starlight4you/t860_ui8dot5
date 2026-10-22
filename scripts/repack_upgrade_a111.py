#!/usr/bin/env python3
"""Repack cumulative SYSTEM/PRODUCT/VENDOR with no installed-version checks."""
import copy,hashlib,json,struct,zipfile
from pathlib import Path
import release_deflate
from render_cumulative_a111 import support
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 srcdir=ROOT/'out/releases/v1.0.2-A109-Cumulative';source=srcdir/'TabS6-OneUI8.5-v1.0.2-A109-Upgrade-TWRP.zip'
 images=ROOT/'t860-ui8/out/a111-cumulative-images-v1';out=ROOT/'out/releases/v1.0.3-A111-Cumulative';target=out/'TabS6-OneUI8.5-v1.0.3-A111-Upgrade-TWRP.zip'
 assert not target.exists() and sha(source)=='f977e101705687a7acd5b1cfd8f80f45b64ee06a415aa6aa8f0ad6b5f08e1eec'
 closure=json.loads((images/'change-closure.json').read_text()); assert closure['id']=='A111_CUMULATIVE_IMAGE_CLOSURE' and not closure['adb_root']
 for part in ('system','vendor'):assert sha(images/(part+'.raw.img'))==closure['partitions'][part]['sha256']
 library,extras=support(source)
 with zipfile.ZipFile(source) as src,source.open('rb') as encoded,(images/'system.raw.img').open('rb') as image:
  m=json.loads(src.read('rom/manifest.json'));updater=src.read('META-INF/com/google/android/update-binary').decode()
  updater=updater.replace('for entry in upgrade.tsv system.chunks product.chunks;', 'for entry in upgrade.tsv system.chunks product.chunks vendor.chunks;')
  updater=updater.replace('371ae95aacec25aae496e9d2796c967c8253b847e980cbbca16ce31690e61daa',digest(library))
  table=[];chunks={}
  for line in src.read('rom/system.chunks').decode().splitlines():
   i,o,n,h,name=line.split('\t'); image.seek(int(o)*4096);b=image.read(int(n));assert len(b)==int(n);table.append('\t'.join([i,o,n,digest(b),name]));chunks[name]=(int(o)*4096,int(n),h)
  tsv=src.read('rom/upgrade.tsv').decode().replace('format\t3','format\t4').replace('A109_S6_CUMULATIVE_FILES','A111_FULL_PRODUCTION_IMAGES').replace('f1a177ad169cff6630027ff774975d49b5fbed31dfd86ee89e598e32037e2353',closure['partitions']['system']['sha256'])
  vendor_table=[];vendor_prepared=[]
  # Retain encoded vendor blocks in bounded temporary files, not process memory.
  cache=images/'vendor-deflate';cache.mkdir()
  for i,raw,compressed in release_deflate.chunks(images/'vendor.raw.img',64*1024**2,workers=3):
   p=cache/('%04d.deflate'%i);p.write_bytes(compressed);n='payload/vendor/%04d.img'%i
   vendor_table.append('\t'.join(map(str,[i,i*16384,len(raw),digest(raw),n])));vendor_prepared.append((n,p,len(raw)))
  tsv+='vendor.sha256\t'+closure['partitions']['vendor']['sha256']+'\nvendor.chunk_count\t'+str(len(vendor_table))+'\n'
  m['rom_manifest'].update(candidate_id='A111-SM-T860-S9-UI85-20261022',version='v1.0.3-A111',source_inventory_sha256=closure['closure']['system']['inventory_sha256'],cumulative_change_closure=closure,hardware_policy='FULL_SYSTEM_PRODUCT_VENDOR_IMAGES_KEEP_BOOT_DTBO_VBMETA_RECOVERY')
  m['rom_manifest']['partitions']['system']=closure['partitions']['system'];m['rom_manifest']['partitions']['vendor']=closure['partitions']['vendor']
  m['image_audits']['system'].update(sha256=closure['partitions']['system']['sha256']);m['image_audits']['vendor']=closure['partitions']['vendor']
  m['installer_library_sha256']=digest(library);m['support_member_sha256']={'rom/support/'+n:digest(b) for n,b in extras.items()}
  m['installer_adaptation_profile']={'id':'A111_CUMULATIVE_NO_SOURCE_VERSION_CHECK','adaptation':'A111_FULL_PRODUCTION_IMAGES','source_version_check':False,'source_tree_whitelist':False,'supported_upgrade_source':'ONE_UI_8_5_ONLY','data_policy':'PRESERVE','vendor_policy':'REPLACE_FULL_IMAGE','adb_root':False}
  m['profile']={'id':'A111_UPGRADE_UI85_ONLY','vendor_scope':'FULL_PRODUCTION_VENDOR_IMAGE','target_vendor_inventory_sha256':closure['closure']['vendor']['inventory_sha256']};m['cumulative_integration']={'id':'A111','included':closure['included'],'excluded':closure['excluded'],'source_or_data_guards_removed':'SOURCE_VERSION_AND_SOURCE_TREE_ONLY','data_module_access_and_pending_checks_retained':True,'kernel_changed':False,'adb_root':False}
  m.pop('library_sources',None)
  changes={'META-INF/com/google/android/update-binary':updater.encode(),'rom/libupgrade.sh':library,'rom/upgrade.tsv':tsv.encode(),'rom/system.chunks':('\n'.join(table)+'\n').encode(),'rom/vendor.chunks':('\n'.join(vendor_table)+'\n').encode(),'rom/manifest.json':(json.dumps(m,indent=2)+'\n').encode()}
  oldlimit=zipfile.ZIP64_LIMIT;zipfile.ZIP64_LIMIT=2**32-1
  try:
   with zipfile.ZipFile(target.with_suffix('.zip.partial'),'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9,allowZip64=True) as dst:
    changed=[]
    for info in src.infolist():
     n=info.filename
     if n.startswith('rom/support/'):continue
     if n in changes:dst.writestr(info,changes.pop(n));continue
     raw=src.read(info)
     if n in chunks:
      offset,size,pin=chunks[n];assert digest(raw)==pin;image.seek(offset);new=image.read(size)
      if new!=raw:
       release_deflate.write(dst,info,new,release_deflate.compress(new,release_deflate.encoder()));changed.append(n);continue
     encoded.seek(info.header_offset);header=encoded.read(30);assert header[:4]==b'PK\x03\x04';a,b=struct.unpack_from('<HH',header,26);encoded.seek(a+b,1);compressed=encoded.read(info.compress_size)
     release_deflate.write(dst,info,raw,compressed)
    for n,b in changes.items():dst.writestr(n,b)
    for n,b in extras.items():dst.writestr('rom/support/'+n,b)
    with (images/'vendor.raw.img').open('rb') as vendor:
     for n,p,size in vendor_prepared:
      raw=vendor.read(size);info=zipfile.ZipInfo(n,date_time=(2022,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;release_deflate.write(dst,info,raw,p.read_bytes())
   target.with_suffix('.zip.partial').rename(target)
  finally:zipfile.ZIP64_LIMIT=oldlimit
 with zipfile.ZipFile(target) as z:
  assert len(z.namelist())==len(set(z.namelist())) and z.testzip() is None
  for part in ['system','product','vendor']:
   h=hashlib.sha256()
   for line in z.read('rom/'+part+'.chunks').decode().splitlines():
    _,_,n,pin,name=line.split('\t');raw=z.read(name);assert len(raw)==int(n) and digest(raw)==pin;h.update(raw)
   assert h.hexdigest()==m['image_audits'][part]['sha256']
 report={'id':'A111_CUMULATIVE_UPGRADE_PACKAGE','zip_sha256':sha(target),'zip_bytes':target.stat().st_size,'changed_system_chunks':changed,'source_version_check':False,'source_tree_whitelist':False,'adb_root':False,'partitions_written':['system','product','vendor'],'data_preserved':True,'all_chunk_and_crc_checks':'PASS','zip64':target.stat().st_size>=2**32,'full_flash':'NOT_PERFORMED'}
 (out/'package-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
