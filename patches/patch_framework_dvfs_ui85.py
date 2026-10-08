#!/usr/bin/env python3
"""Rebuild only new donor Samsung classes6 with reviewed S6 DVFS logic.

Rationale: docs/DVFS_REBASE_AUDIT.md. No old framework/APK runtime is copied.
Output is a compatibility probe; this script never edits a ROM staging tree.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import struct
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_vendor_java_api_ui85 import index_archive,members,sections
from dex041 import read_uleb,u16,u32


def sha(raw):return hashlib.sha256(raw).hexdigest()


def run(argv):
 p=subprocess.run([str(x) for x in argv],capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stderr[-5000:])
 return p.stdout


def method_span(text,name,descriptor):
 pattern=re.compile(r'^\.method [^\n]*\b'+re.escape(name+descriptor)+r'\n.*?^\.end method$',re.M|re.S)
 spans=list(pattern.finditer(text))
 if len(spans)!=1:raise ValueError('method source not unique: '+name+descriptor)
 return spans[0]


def canonical(text):
 """Preserve symbolic instructions/debug/metadata; normalize generated labels."""
 result=[];labels={}
 for line in text.splitlines():
  line=line.strip()
  if not line or line.startswith('#'):continue
  # DEX permits omitted trailing static values: they become the typed default.
  # smali trims explicit defaults; preserve all other encoded values exactly.
  field=re.fullmatch(r'(\.field [^=]+):([^\s]+)(?: = (.*))?',line)
  if field and 'static' in field[1].split()[1:-1]:
   desc,value=field[2],field[3]
   defaults={'Z':'false','B':'0x0t','S':'0x0s','C':"'\\u0000'",'I':'0x0',
             'J':'0x0L','F':'0.0f','D':'0.0'}
   default='null' if desc.startswith(('L','[')) else defaults.get(desc)
   if value is not None and value==default:line=field[1]+':'+desc
  if line.startswith('.method '):labels={}
  if not line.startswith('const-string'):
   def label(m):
    if m[0] not in labels:labels[m[0]]=':label_'+str(len(labels))
    return labels[m[0]]
   line=re.sub(r':(?:cond|goto|pswitch|sswitch|try_start|try_end|catchall|catch|array)_\w+\b',label,line)
  line=line.replace('const-string/jumbo ','const-string ')
  result.append(line)
 return '\n'.join(result)


def without_targets(text,targets):
 for name,desc in targets:
  span=method_span(text,name,desc);text=text[:span.start()]+text[span.end():]
 return canonical(text)


def preserve_hidden_api_domains(original_jar,assembled):
 """Restore every old member's raw flags that this smali version cannot emit.

 The fixed standalone output puts hiddenapi last before map_list. Replace only
 that tail, preserving all preceding section offsets and existing definitions.
 No weakening of public/core-platform domain bits is permitted.
 """
 old,_,_=index_archive(original_jar,'framework.jar')
 sec=next(sections(assembled));raw=bytearray(assembled);mo=u32(raw,0x34)
 rows=[list(struct.unpack_from('<HHII',raw,mo+4+12*i)) for i in range(u32(raw,mo))]
 h=[r for r in rows if r[0]==0xf000]
 if len(h)!=1 or h[0][2]!=1 or rows[-2][0]!=0xf000 or rows[-1]!=[0x1000,0,1,mo] or mo+4+len(rows)*12!=len(raw):
  raise ValueError('unreviewed hiddenapi/map tail layout')
 start=h[0][3];end=start+u32(raw,start)
 if end>mo or mo-end>3 or any(raw[end:mo]):raise ValueError('unreviewed hiddenapi tail padding')
 if u32(raw,0x2c) or u32(raw,0x30):raise ValueError('linked DEX not supported')
 def leb(value):
  out=bytearray()
  while True:
   b=value&127;value>>=7;out.append(b|(128 if value else 0))
   if not value:return out
 table=bytearray(4+sec.class_count*4);restored=0
 for ci in range(sec.class_count):
  cd=sec.class_off+ci*32;owner=sec.type(u32(raw,cd));cls=old[owner];members(cls);off=u32(raw,cd+24)
  if not off:continue
  counts=[]
  for _ in range(4):v,off=read_uleb(raw,off);counts.append(v)
  flag_values=[]
  delta=u32(raw,start+4+ci*4);cursor=start+delta if delta else None
  for category,count in enumerate(counts):
   idx=0
   for _ in range(count):
    diff,off=read_uleb(raw,off);idx+=diff
    access,off=read_uleb(raw,off)
    if category<2:
     current_owner,name,desc=sec.field_id(idx);member=cls['fields'].get((name,desc))
    else:
     _,off=read_uleb(raw,off);current_owner,name,desc=sec.method_id(idx);member=cls['methods'].get((name,desc))
    if current_owner!=owner:raise ValueError('member owner mismatch')
    existing=0
    if cursor is not None:existing,cursor=read_uleb(raw,cursor)
    if member is not None:
     if member['access']!=access or member['hiddenapi_raw'] is None:raise ValueError('original definition/flags differ')
     value=member['hiddenapi_raw']
     if value!=existing:
      if value^existing!=0x20:raise ValueError('unreviewed assembler flag difference')
      restored+=1
    else:
     if owner!='Lcom/samsung/android/os/SemDvfsManager;' or (name,desc) not in {('addS6SsrmAliases','([II)[I'),('normalizeS6SsrmFrequency','(II)I')} or existing!=2:
      raise ValueError('unreviewed added member/flags')
     value=existing
    flag_values.append(value)
  if any(flag_values):
   struct.pack_into('<I',table,4+ci*4,len(table))
   for value in flag_values:table.extend(leb(value))
 struct.pack_into('<I',table,0,len(table))
 output=raw[:start]+table
 output.extend(b'\0'*((-len(output))%4));new_map=len(output)
 for r in rows:
  if r[0]==0x1000:r[3]=new_map
 output.extend(struct.pack('<I',len(rows)))
 for row in rows:output.extend(struct.pack('<HHII',*row))
 struct.pack_into('<I',output,0x20,len(output));struct.pack_into('<I',output,0x34,new_map)
 struct.pack_into('<I',output,0x68,len(output)-u32(output,0x6c))
 # sections() verifies checksums, so repair with the format's checksum rules.
 import zlib
 output[12:32]=hashlib.sha1(output[32:]).digest()
 struct.pack_into('<I',output,8,zlib.adler32(output[12:])&0xffffffff)
 tuple(sections(bytes(output)))
 return bytes(output),{'original_raw_flags_restored':restored,'old_hiddenapi_bytes':end-start,
                       'new_hiddenapi_bytes':len(table),'preceding_data_offsets_unchanged':True}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--allow-unpinned-output',action='store_true');a=p.parse_args()
 if a.out.exists() or not a.out.resolve().is_relative_to(ROOT/'out/patch-probes'):raise ValueError('fresh compatibility probe output required')
 contract_path=ROOT/'device/s6/dvfs-ui85.json';c=json.loads(contract_path.read_text())
 if not c['output_jar_sha256'] and not a.allow_unpinned_output:raise ValueError('independent output pin not established')
 base=a.inputs/'files/system/system';jar=base/'framework/framework.jar';apk=base/'priv-app/SamsungDeviceHealthManagerService/SamsungDeviceHealthManagerService.apk';floating=base/'etc/floating_feature.xml'
 for path,pin in [(jar,c['input_jar_sha256']),(apk,c['sdhms_apk_sha256']),(floating,c['floating_feature_sha256'])]:
  if sha(path.read_bytes())!=pin:raise ValueError('exact reviewed source required: '+str(path))
 if sha((ROOT/'docs/audit/dvfs-policy-ui85.json').read_bytes())!=c['policy_audit_sha256']:raise ValueError('policy provenance differs')
 template=ROOT/'patches/dvfs/ssrm_helpers.smali.in';text=template.read_text()
 if sha(template.read_bytes())!=c['helper_template_sha256']:raise ValueError('helper template differs')
 tools=[ROOT/'t860-ui8/tools/smali'/n for n in ['baksmali-3.0.6-fat.jar','smali-3.0.6-fat.jar']]
 pins=['4b8da1c41385db9aa690f314163e61a915e292b6e21a2f3c14192d556042fce8','484973a6cf08d1e94c327cdfa49dd05180fd2cd4ec67f593f7d6c2881428f28a']
 if [sha(t.read_bytes()) for t in tools]!=pins:raise ValueError('decoder/assembler differs')
 with ZipFile(jar) as z:
  infos=z.infolist();originals={i.filename:z.read(i.filename) for i in infos}
  if z.testzip() or len(originals)!=len(infos):raise ValueError('invalid input JAR')
 raw=originals[c['dex_member']]
 if sha(raw)!=c['input_dex_sha256'] or raw[:8]!=b'dex\n039\0':raise ValueError('reviewed standalone DEX039 required')
 s=next(sections(raw))
 if s.class_count!=c['input_dex_classes']:raise ValueError('input class scope differs')
 for spec in c['methods']:
  m=s.method(spec['owner'],spec['name'],spec['descriptor'])
  if not m or m.access_flags!=spec['access_flags'] or m.registers_size!=spec['registers'] or m.tries_size or sha(raw[m.insns_off:m.insns_off+m.insns_size*2])!=spec['code_sha256']:raise ValueError('input method definition differs')
 a.out.mkdir(parents=True);work=a.out/'work';work.mkdir();dex_in=work/'original.dex';dex_in.write_bytes(raw)
 before=work/'before';after=work/'after';dex_out=work/'patched.dex'
 run(['java','-Xmx3g','-jar',tools[0],'disassemble','--jobs','1','--api','36','-o',before,dex_in])
 originals_smali={p.relative_to(before).as_posix():p.read_text() for p in before.rglob('*.smali')}
 if len(originals_smali)!=c['input_dex_classes']:raise ValueError('decoder class scope differs')
 manager=before/'com/samsung/android/os/SemDvfsManager.smali';hyper=before/'com/samsung/android/os/SemDvfsHyPerManager.smali'
 for kind,prefix in [('CPUFreqMax','CPU'),('GPUFreqMax','GPU')]:
  values=c['aliases'][kind]
  if not values or any(v<=0 for v in values) or sorted(set(values),reverse=True)!=values:raise ValueError('invalid policy alias list')
  text=text.replace('@'+prefix+'_COUNT@',hex(len(values))).replace('@'+prefix+'_VALUES@','\n'.join('        '+hex(v) for v in values))
 if '@' in text:raise ValueError('unexpanded template')
 mt=manager.read_text();ht=hyper.read_text()
 if 'addS6SsrmAliases' in mt or 'normalizeS6SsrmFrequency' in mt:raise ValueError('already patched')
 for desc,register in [('()[I','v0'),('(I)[I','p1')]:
  span=method_span(mt,'getSupportedFrequencyForSsrm',desc);body=span[0]
  needle='    return-object p0';
  if body.count(needle)!= (2 if desc=='()[I' else 1):raise ValueError('unreviewed getter return shape')
  at=body.rfind(needle);replacement='    invoke-static {p0, '+register+'}, Lcom/samsung/android/os/SemDvfsManager;->addS6SsrmAliases([II)[I\n\n    move-result-object p0\n\n'+needle
  body=body[:at]+replacement+body[at+len(needle):];mt=mt[:span.start()]+body+mt[span.end():]
 marker='\n\n# virtual methods\n'
 if mt.count(marker)!=1:raise ValueError('class layout changed')
 mt=mt.replace(marker,'\n\n'+text+marker,1)
 span=method_span(ht,'setDvfsValue','(I)V');body=span[0];needle='    iget-object v0, p0, Lcom/samsung/android/os/SemDvfsHyPerManager;->acquireHash:Ljava/util/HashMap;'
 if body.count(needle)!=1:raise ValueError('unreviewed request insertion shape')
 body=body.replace(needle,'    invoke-virtual {p0, p1, v0}, Lcom/samsung/android/os/SemDvfsManager;->normalizeS6SsrmFrequency(II)I\n\n    move-result p1\n\n'+needle,1)
 ht=ht[:span.start()]+body+ht[span.end():];manager.write_text(mt);hyper.write_text(ht)
 run(['java','-Xmx3g','-jar',tools[1],'assemble','--api','29','--jobs','1','-o',dex_out,before])
 patched=dex_out.read_bytes()
 if patched[:8]!=b'dex\n040\0':raise ValueError('unexpected standalone output DEX version')
 patched,flag_report=preserve_hidden_api_domains(jar,patched)
 dex_out.write_bytes(patched)
 run(['java','-Xmx3g','-jar',tools[0],'disassemble','--jobs','1','--api','36','-o',after,dex_out])
 rebuilt_smali={p.relative_to(after).as_posix():p.read_text() for p in after.rglob('*.smali')}
 if set(rebuilt_smali)!=set(originals_smali):raise ValueError('class set changed')
 exceptions={manager.relative_to(before).as_posix(): [('getSupportedFrequencyForSsrm','()[I'),('getSupportedFrequencyForSsrm','(I)[I')],hyper.relative_to(before).as_posix():[('setDvfsValue','(I)V')]}
 for name,old in originals_smali.items():
  new=rebuilt_smali[name]
  if name not in exceptions:
   if canonical(old)!=canonical(new):raise ValueError('unchanged class/debug/metadata differs: '+name)
  else:
   extra=[('addS6SsrmAliases','([II)[I'),('normalizeS6SsrmFrequency','(II)I')] if name==manager.relative_to(before).as_posix() else []
   if without_targets(old,exceptions[name])!=without_targets(new,exceptions[name]+extra):raise ValueError('other target-class members changed')
 output=a.out/'system/framework/framework.jar';output.parent.mkdir(parents=True)
 with ZipFile(output,'w',allowZip64=False) as z:
  for info in infos:z.writestr(info,patched if info.filename==c['dex_member'] else originals[info.filename])
 with ZipFile(output) as z:
  if z.testzip() or z.namelist()!=[i.filename for i in infos]:raise ValueError('output ZIP layout differs')
  if any(z.read(n)!=b for n,b in originals.items() if n!=c['dex_member']):raise ValueError('other JAR entry changed')
 old_index,_,_=index_archive(jar,'framework.jar');new_index,_,_=index_archive(output,'framework.jar')
 if set(old_index)!=set(new_index):raise ValueError('full JAR class set changed')
 checked_members=0
 for name,old in old_index.items():
  new=new_index[name];members(old);members(new)
  for k in ['parent','interfaces','access','fields']:
   if old[k]!=new[k]:raise ValueError('original class/field access/hidden API metadata differs: '+name)
  for key,value in old['methods'].items():
   if value!=new['methods'].get(key):raise ValueError('original method flags/definition differs: '+name+str(key))
   checked_members+=1
  expected={('addS6SsrmAliases','([II)[I'),('normalizeS6SsrmFrequency','(II)I')} if name=='Lcom/samsung/android/os/SemDvfsManager;' else set()
  if set(new['methods'])-set(old['methods'])!=expected:raise ValueError('unexpected added member')
 result={'schema':1,'kind':'compatibility_probe','id':c['id'],'status':'PREPARED_NOT_APPLIED_NOT_RUNTIME_TESTED','input_jar_sha256':sha(jar.read_bytes()),'output_jar_sha256':sha(output.read_bytes()),'input_dex_sha256':sha(raw),'output_dex_sha256':sha(patched),'size_delta':output.stat().st_size-jar.stat().st_size,'dex_size_delta':len(patched)-len(raw),'classes':len(originals_smali),'unchanged_classes_symbolic_code_debug_metadata_checked':len(originals_smali)-2,'all_original_method_metadata_checked':checked_members,'hiddenapi_preservation':flag_report,'all_other_jar_entries_byte_identical':True,'contract_sha256':sha(contract_path.read_bytes()),'script_sha256':sha(Path(__file__).read_bytes()),'definition_helper_sha256':sha((ROOT/'scripts/audit_vendor_java_api_ui85.py').read_bytes()),'tool_sha256':dict(zip([t.name for t in tools],pins)),'files':[{'path':'system/framework/framework.jar','size':output.stat().st_size,'sha256':sha(output.read_bytes()),'image_metadata_required':{k:c[k] for k in ['owner','group','mode','selinux']}}],'firmware_stage_modified':False,'device_writes':False,'runtime':'NOT_TESTED','limits':c['limits']}
 if c['output_jar_sha256'] and result['output_jar_sha256']!=c['output_jar_sha256']:raise ValueError('independent output pin differs')
 (a.out/'probe-manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
