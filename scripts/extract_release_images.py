#!/usr/bin/env python3
"""Extract and verify the six raw partition images from a published complete ZIP."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('zip',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 spec=json.loads((ROOT/'release/packaging.json').read_text());h=hashlib.sha256()
 with a.zip.open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 if h.hexdigest()!=spec['zip_sha256'] or a.out.exists():raise ValueError('Exact release ZIP and fresh output required')
 a.out.mkdir()
 with zipfile.ZipFile(a.zip) as z:
  for part,target in spec['partitions'].items():
   h=hashlib.sha256();path=a.out/(part+'.raw.img')
   with path.open('wb') as dst:
    for row in spec['entries']:
     if row['name'].startswith('payload/'+part+'/'):
      with z.open(row['name']) as src:
       for b in iter(lambda:src.read(8*1024**2),b''):dst.write(b);h.update(b)
   if path.stat().st_size!=target['bytes'] or h.hexdigest()!=target['sha256']:raise ValueError('Extracted image mismatch')
   print(part,h.hexdigest())
if __name__=='__main__':main()
