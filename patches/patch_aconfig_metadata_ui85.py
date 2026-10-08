"""A55: pinned persistent flag storage bridge for unchanged S6 hardware."""
import hashlib, struct
from elf_aarch64 import Elf, branch_target

def sha(b): return hashlib.sha256(b).hexdigest()
def native(raw,c):
 n=c['native']
 if len(raw)!=n['bytes'] or sha(raw)!=n['input_sha256']: raise ValueError('Unreviewed native input')
 e=Elf(raw)
 if e.function(n['va'])!=n['function'] or e.word(n['va'])!=0xd503201f: raise ValueError('Function or patch slot differs')
 expected={0x151dc:0x94003ad2,0x151e8:0x540003e1,0x15200:0x94003ac9,0x1520c:0x540002c1,0x15224:0x94003ac0,0x15230:0x540001a1,0x15238:0x70f93362,0x15244:0x528000c3,0x15248:0x94003ab7,0x15254:0x54000081,0x15258:0xf94013e8,0x1525c:0xf9000118,0x15260:0x1400000a}
 if any(e.word(k)!=v for k,v in expected.items()) or e.at(0x78a7,6)!=b'vendor': raise ValueError('Provider calls/error checks/absent vendor slot differ')
 if n['after_word']!='14000009' or branch_target(0x14000009,n['va'])!=n['target_va']: raise ValueError('Invalid target')
 out=bytearray(raw);struct.pack_into('<I',out,e.offset(n['va'],4),0x14000009)
 if sha(out)!=n['output_sha256']: raise ValueError('Unexpected native output')
 return bytes(out)
def prepare(path,raw,c):
 cfg=next(x for x in c['files'] if x['path']==path)
 if sha(raw)!=cfg['before_sha256']: raise ValueError('Source differs: '+path)
 if path.endswith('libaconfigd_rust.dylib.so'): return native(raw,c)
 s=raw.decode()
 if path.endswith('/hw/init.rc'):
  marker='on post-fs\n'
  if s.count(marker)!=1 or '/cache/t860-metadata' in s: raise ValueError('Init trigger differs')
  s=s.replace(marker,marker+'    # A55: S6 has CACHE but no metadata partition; establish persistent backing.\n    mkdir /cache/t860-metadata 0755 root root\n    mount none /cache/t860-metadata /metadata bind\n    restorecon_recursive /metadata\n\n')
 elif path.endswith('/aconfigd.rc'):
  early='on early-init\n    mkdir /metadata/aconfig 0775 root system\n    mkdir /metadata/aconfig/flags 0770 root system\n    mkdir /metadata/aconfig/maps 0775 root system\n    mkdir /metadata/aconfig/boot 0775 root system\n    exec_start early_system_aconfigd_platform_init\n\n'
  if s.count(early)!=1 or s.count('    exec_start system_aconfigd_platform_init\n')!=1: raise ValueError('Aconfig actions differ')
  s=s.replace(early,'# A55: initialize after S6 CACHE-backed metadata is mounted in root post-fs.\n\n').replace('    exec_start system_aconfigd_platform_init\n','    exec_start early_system_aconfigd_platform_init\n    exec_start system_aconfigd_platform_init\n')
 elif path.endswith('/plat_file_contexts'):
  rules=[line for line in s.splitlines() if line.startswith('/metadata')]
  if len(rules)!=20 or '/cache/t860-metadata' in s: raise ValueError('Metadata contexts differ')
  s+='\n# A55: alias labels match /metadata through the CACHE backing bind mount.\n'+'\n'.join(line.replace('/metadata','/cache/t860-metadata',1) for line in rules)+'\n'
 else: raise ValueError('Unreviewed target')
 return s.encode()
