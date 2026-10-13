#!/usr/bin/env python3
"""Validate every real A102 ZIP payload with original TWRP userspace, no blocks."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,zipfile
from pathlib import Path
SIZES={'system':6534725632,'product':1048576000}
EXPECTED={'upgrade-access-probe','vendor-guard-sdk28','vendor-guard-sdk30','vendor-config-recovery-guard','mainline-guard','vendor-before-policy','vendor-after-policy','vendor-matrix28','vendor-matrix30','apex-factory.tsv','fscrypt-readonly-probe','ui8-release-guard','ui8-a46-guard','stock-vendor-guard','a99-system-guard','partition-probe','a100-system-guard','a100-vendor-guard','a100-vendor-recovery-guard','a100-sdm-before','a100-sdm-after'}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('zip','recovery-root','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();root=a.recovery_root
 if os.geteuid() or a.out.exists() or (root/'dev/block').exists() or a.zip.stat().st_size>=2**32:raise ValueError('Root/fresh output/isolated ZIP32 required')
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
  if embedded['rom_manifest']['candidate_id']!='A100-SM-T860-S9-UI85-20261012' or embedded['installer_adaptation_profile']['adaptation']!='A100_THREE_S6_FILES':raise ValueError('Wrong A100 package')
  if embedded.get('installer_hotfix',{}).get('fixed_guard_sha256')!='4f3f04af10250a0522b4bf2805fe0567fef975da1aea9e24024d86eba8ca8176':raise ValueError('Wrong upgrade-capable guard')
  support=embedded['support_member_sha256']
  if set(support)!={'rom/support/'+n for n in EXPECTED}:raise ValueError('Support membership differs')
  for name,h in support.items():
   if z.namelist().count(name)!=1 or hashlib.sha256(z.read(name)).hexdigest()!=h:raise ValueError('Support changed')
  texts={n:z.read('rom/'+n) for n in ('libupgrade.sh','upgrade.tsv','system.chunks','product.chunks')}
  if hashlib.sha256(texts['libupgrade.sh']).hexdigest()!=embedded['installer_library_sha256']:raise ValueError('Library differs')
  for part in SIZES:total+=len(texts[part+'.chunks'].decode().splitlines())
 with tempfile.TemporaryDirectory(prefix='a100-real-zip-',dir=root/'tmp') as folder:
  work=Path(folder);shutil.copyfile(a.zip,work/'candidate.zip')
  if sha(work/'candidate.zip')!=pin:raise ValueError('Temporary copy differs')
  for name,b in texts.items():(work/name).write_bytes(b)
  inside='/'+str(work.relative_to(root));script=work/'probe.sh'
  script.write_text('set -eu\nset -o pipefail\nPATH=/sbin\nLD_LIBRARY_PATH=/sbin\nexport PATH LD_LIBRARY_PATH\nWORK="'+inside+'"\nZIP="$WORK/candidate.zip"\n. "$WORK/libupgrade.sh"\nTAB=$(printf "\\t")\nabort(){ printf "%s\\n" "$*" >&2; exit 1; }\nui_print(){ printf "%s\\n" "$*"; }\na71_extract_support\nverify_table system 6534725632\nverify_table product 1048576000\nverify_payload\nprintf "A102_REAL_PAYLOAD_PASS\\n"\n')
  argv=['unshare','--mount','--pid','--fork','/bin/sh','-c','mount --bind "$1" "$1" && mount -t proc -o ro proc "$1/proc" && exec chroot "$1" /sbin/sh "$2"','a100-native-preflight',str(root),inside+'/probe.sh']
  r=subprocess.run(argv,capture_output=True,text=True,timeout=1800,env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LD_LIBRARY_PATH':'/sbin'})
  (a.out/'stdout.txt').write_text(r.stdout);(a.out/'stderr.txt').write_text(r.stderr)
  if r.returncode or 'A102_REAL_PAYLOAD_PASS' not in r.stdout:raise ValueError('Original TWRP preflight failed: '+r.stderr[-700:])
 if sha(a.zip)!=pin:raise ValueError('Package changed')
 report={'zip_sha256':pin,'zip_bytes':a.zip.stat().st_size,'payload_chunks_checked':total,'support_members_checked':len(support),'table_sizes':SIZES,'process_exit':0,'source_mounts_or_device_blocks':False,'device_writes':False,'full_flash':'NOT_TESTED','script_sha256':sha(Path(__file__))};(a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
