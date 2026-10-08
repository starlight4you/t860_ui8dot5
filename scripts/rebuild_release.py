#!/usr/bin/env python3
"""Rebuild the fixed release ZIP from exact six partition images and public installer inputs.
No device access, formatting or image mutation. Firmware must be supplied locally.
"""
import argparse,hashlib,json,os,zipfile
import release_deflate
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 
 for part in ('system','product','boot','vendor','dtbo','vbmeta'):p.add_argument('--'+part,type=Path,required=True)
 p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();program=release_deflate.encoder();spec=json.loads((ROOT/'release/packaging.json').read_text());images={part:getattr(a,part) for part in ('system','product','boot','vendor','dtbo','vbmeta')}
 if a.out.exists():raise ValueError('Fresh output required')
 for part,image in images.items():
  target=spec['partitions'][part]
  if image.is_symlink() or image.stat().st_size!=target['bytes'] or sha(image)!=target['sha256']:raise ValueError('Exact released image required: '+part)
 partial=a.out.with_suffix('.partial');previous=zipfile.ZIP64_LIMIT;zipfile.ZIP64_LIMIT=2**32-1
 def prepare(row):
  name=row['name']
  if name.startswith('payload/'):
   with images[name.split('/')[1]].open('rb') as f:f.seek(row['offset']);raw=f.read(row['bytes'])
  else:raw=(ROOT/'release/inputs'/name).read_bytes()
  if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Changed input '+name)
  encoded=release_deflate.compress(raw,program) if name.startswith('payload/') else None
  return row,raw,encoded
 def prepared():
  rows=iter(spec['entries'])
  with ThreadPoolExecutor(max_workers=4) as pool:
   pending=deque()
   for _ in range(4):
    row=next(rows,None)
    if row is not None:pending.append(pool.submit(prepare,row))
   while pending:
    yield pending.popleft().result()
    row=next(rows,None)
    if row is not None:pending.append(pool.submit(prepare,row))
 try:
  with zipfile.ZipFile(partial,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=spec['compression_level'],allowZip64=False) as z:
   for row,raw,encoded in prepared():
    name=row['name'];info=zipfile.ZipInfo(name,tuple(row['date_time']));info.create_system=row['create_system'];info.external_attr=row['external_attr'];info.compress_type=zipfile.ZIP_DEFLATED;info._compresslevel=spec['compression_level']
    if name.startswith('payload/'):
     release_deflate.write(z,info,raw,encoded)
    else:z.writestr(info,raw)
    print(name,flush=True)
  if partial.stat().st_size>=2**32:raise ValueError('Pinned TWRP requires ZIP32')
  with zipfile.ZipFile(partial) as z:
   if z.testzip():raise ValueError('ZIP CRC failure')
  digest=sha(partial)
  if digest!=spec['zip_sha256']:raise ValueError('Nonidentical archive; use the pinned Python/zlib/7-Zip environment recorded in packaging.json. Images were not modified.')
  os.rename(partial,a.out);print(digest+'  '+a.out.name)
 finally:
  zipfile.ZIP64_LIMIT=previous
  partial.unlink(missing_ok=True)
if __name__=='__main__':main()
