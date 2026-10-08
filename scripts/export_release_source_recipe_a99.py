#!/usr/bin/env python3
"""Export immutable, public reproducibility inputs from a verified full ZIP.
No firmware chunks, user DATA, original private logs or device identifiers
are copied to Git; only the installer/support and packing recipe are copied.
"""
import argparse,hashlib,json,platform,zlib,zipfile
from release_deflate import OPTIONS
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--zip',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);a=p.parse_args()
 dst=a.public_root/'release';inputs=dst/'inputs';inputs.mkdir(parents=True,exist_ok=False)
 h=hashlib.sha256()
 with a.zip.open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 entries=[]
 with zipfile.ZipFile(a.zip) as archive:
  embedded=json.loads(archive.read('rom/manifest.json'));manifest=embedded['rom_manifest'];parts=manifest['partitions']
  if len(parts)!=6 or manifest['target']!='SM-T860':raise ValueError('Six-partition T860 release required')
  locations={}
  for part in parts:
   for line in archive.read('rom/'+part+'.chunks').decode().splitlines():
    _,offset,size,sha,member=line.split('\t');locations[member]={'offset':int(offset)*4096,'bytes':int(size),'sha256':sha}
  for info in archive.infolist():
   if info.flag_bits&9 or info.extract_version>=45 or info.extra or info.compress_type!=zipfile.ZIP_DEFLATED:raise ValueError('Unexpected ZIP format')
   row={'name':info.filename,'bytes':info.file_size,'date_time':list(info.date_time),'create_system':info.create_system,'external_attr':info.external_attr}
   if info.filename.startswith('payload/'):
    row.update(locations[info.filename])
   else:
    raw=archive.read(info.filename);row['sha256']=hashlib.sha256(raw).hexdigest()
    target=inputs/info.filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
   entries.append(row)
  audit={'zip_sha256':h.hexdigest(),'zip_bytes':a.zip.stat().st_size,'partition_sha256':{k:v['sha256'] for k,v in parts.items()},'payload_chunks':len(locations),'entries':len(entries),'zip_format':'ZIP32_NO_ZIP64','installer_library_sha256':embedded['installer_library_sha256']}
 recipe={**audit,'schema':1,'partitions':parts,'compression_level':9,'payload_encoder':{'version':'7-Zip 26.01','options':OPTIONS,'format':'STANDARD_DEFLATE_METHOD_8'},'producer_python':platform.python_version()+' '+platform.system()+' '+platform.machine(),'recipe_export_zlib_version':zlib.ZLIB_VERSION,'recipe_export_zlib_runtime_version':zlib.ZLIB_RUNTIME_VERSION,'entries':entries}
 (dst/'packaging.json').write_text(json.dumps(recipe,indent=2)+'\n')
 (dst/'release-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 print(json.dumps(audit))
if __name__=='__main__':main()
