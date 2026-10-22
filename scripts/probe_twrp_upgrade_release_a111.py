#!/usr/bin/env python3
"""Validate every real A111 ZIP payload with original TWRP userspace, no blocks."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,zipfile
from pathlib import Path
SIZES={'system':6534725632,'product':1048576000,'vendor':1379926016}
EXPECTED={'mainline-guard','apex-factory.tsv','fscrypt-readonly-probe','partition-probe','upgrade-access-probe'}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('zip','recovery-root','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();root=a.recovery_root
 if os.geteuid() or a.out.exists() or (root/'dev/block').exists():raise ValueError('Root/fresh output/isolated tools required')
 tools=json.loads((root/'tools-manifest.json').read_text())
 if tools['recovery_sha256']!='cbc6e03563a9229b7034dd775964ef412af94a7074f50b519ce1ccc1fd4f2e16':raise ValueError('Original Recovery differs')
 for row in tools['entries']:
  if not row['path'].startswith('sbin/'):continue
  src=root/row['path']
  if src.is_symlink():h=hashlib.sha256(os.readlink(src).encode()).hexdigest()
  elif src.is_file():h=sha(src)
  elif src.is_dir():continue
  else:raise ValueError('Missing native tool')
  if h!=row['sha256']:raise ValueError('Native tool changed: '+row['path'])
 pin=sha(a.zip);a.out.mkdir(parents=True);total=0
 with zipfile.ZipFile(a.zip) as z:
  embedded=json.loads(z.read('rom/manifest.json'))
  if embedded['rom_manifest']['candidate_id']!='A111-SM-T860-S9-UI85-20261022' or embedded['installer_adaptation_profile']['adaptation']!='A111_FULL_PRODUCTION_IMAGES':raise ValueError('Wrong A111 package')
  if embedded.get('installer_hotfix',{}).get('fixed_guard_sha256')!='4f3f04af10250a0522b4bf2805fe0567fef975da1aea9e24024d86eba8ca8176':raise ValueError('Wrong upgrade-capable guard')
  support=embedded['support_member_sha256']
  if set(support)!={'rom/support/'+n for n in EXPECTED}:raise ValueError('Support membership differs')
  for name,h in support.items():
   if z.namelist().count(name)!=1 or hashlib.sha256(z.read(name)).hexdigest()!=h:raise ValueError('Support changed')
  texts={n:z.read('rom/'+n) for n in ('libupgrade.sh','upgrade.tsv','system.chunks','product.chunks','vendor.chunks')}
  if hashlib.sha256(texts['libupgrade.sh']).hexdigest()!=embedded['installer_library_sha256']:raise ValueError('Library differs')
  for part in SIZES:total+=len(texts[part+'.chunks'].decode().splitlines())
 with tempfile.TemporaryDirectory(prefix='a100-real-zip-',dir=root/'tmp') as folder:
  work=Path(folder);zip_inside='/rom-host/'+a.zip.name
  (root/'rom-host').mkdir(exist_ok=True)
  for name,b in texts.items():(work/name).write_bytes(b)
  inside='/'+str(work.relative_to(root));script=work/'probe.sh'
  script.write_text('set -eu\nset -o pipefail\nPATH=/sbin\nLD_LIBRARY_PATH=/sbin\nexport PATH LD_LIBRARY_PATH\nWORK="'+inside+'"\nZIP="'+zip_inside+'"\n. "$WORK/libupgrade.sh"\nTAB=$(printf "\\t")\nabort(){ printf "%s\\n" "$*" >&2; exit 1; }\nui_print(){ printf "%s\\n" "$*"; }\na71_extract_support\nverify_table system 6534725632\nverify_table product 1048576000\nverify_table vendor 1379926016\nverify_payload\nprintf "A111_REAL_PAYLOAD_PASS\\n"\n')
  argv=['unshare','--mount','--pid','--fork','/bin/sh','-c','mount --bind "$1" "$1" && mount --bind "$3" "$1/rom-host" && mount -o remount,bind,ro "$1/rom-host" && mount -t proc -o ro proc "$1/proc" && exec chroot "$1" /sbin/sh "$2"','a100-native-preflight',str(root),inside+'/probe.sh',str(a.zip.parent)]
  r=subprocess.run(argv,capture_output=True,text=True,timeout=1800,env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LD_LIBRARY_PATH':'/sbin'})
  (a.out/'stdout.txt').write_text(r.stdout);(a.out/'stderr.txt').write_text(r.stderr)
  if r.returncode or 'A111_REAL_PAYLOAD_PASS' not in r.stdout:raise ValueError('Original TWRP preflight failed: '+r.stderr[-700:])
 if sha(a.zip)!=pin:raise ValueError('Package changed')
 report={'zip_sha256':pin,'zip_bytes':a.zip.stat().st_size,'payload_chunks_checked':total,'support_members_checked':len(support),'table_sizes':SIZES,'process_exit':0,'zip_staging':'READONLY_BIND_IN_ISOLATED_NAMESPACE_NO_PAYLOAD_COPY','source_mounts_or_device_blocks':False,'device_writes':False,'full_flash':'NOT_TESTED','script_sha256':sha(Path(__file__))};(a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
