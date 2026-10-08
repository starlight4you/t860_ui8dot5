#!/usr/bin/env python3
"""A59: capacity/error-specific compatibility using new-donor code only."""
import argparse,binascii,hashlib,json,struct
from pathlib import Path
from zipfile import ZipFile
import dex041 as d

def sha(x):return hashlib.sha256(x).hexdigest()
def prepare(raw,c):
 if c['id']!='A59' or c['kind']!='kgta_unavailable_remote_lock_compat' or c['init_backend_error']!=-1006 or sha(raw)!=c['input_sha256']:raise ValueError('Exact reviewed input required')
 z=d.find_stored_member(raw,'classes.dex');payload=raw[z.data_off:z.data_off+z.size]
 if binascii.crc32(payload)&0xffffffff!=z.crc:raise ValueError('Input ZIP CRC')
 x=d.DexContainer(payload);m=x.find_method(c['target_class'],c['target_method'],c['target_descriptor']);s=m.section;u=m.units()
 old=payload[m.insns_off:m.insns_off+2*len(u)]
 if sha(old)!=c['before_code_sha256'] or (m.registers_size,len(u),m.tries_size,d.u16(x.data,m.code_off+2))!=(16,120,1,15):raise ValueError('Method code shape differs')
 # Existing normal body ends in return-void; the typed handler starts at95.
 t=m.insns_off+len(u)*2
 if u[94]!=0x000e or u[95]!=0x010d or bytes(x.data[t:t+13])!=bytes.fromhex('000000005e0001000101b20e5f') or s.type(0x732)!='Landroid/os/RemoteException;':raise ValueError('Try/catch shape differs')
 def method(ref):
  ids=[i for i in range(s.method_count) if s.method_id(i)==ref]
  if len(ids)!=1 or ids[0]>65535:raise ValueError('Method reference differs')
  return ids[0]
 def field(ref):
  ids=[i for i in range(s.field_count) if s.field_id(i)==ref]
  if len(ids)!=1 or ids[0]>65535:raise ValueError('Field reference differs')
  return ids[0]
 native=method(('Lcom/samsung/android/knoxguard/service/KnoxGuardNative;','getTAState','()I'))
 flag=field(('Lcom/samsung/android/knoxguard/service/utils/Constants;','IS_SUPPORT_KGTA','Z'))
 stack=method(('Landroid/os/RemoteException;','printStackTrace','()V'))
 # p0=v1, p1(type)=v2, p2(lock)=v3, v0 is the only local register.
 prefix=[0x3012,0x2033,17,0x0338,15,0x0063,flag,0x0039,11,0x0071,native,0,0x000a,0x00d0,1006,0x0039,3,0x0312]
 new=prefix+u[:95]+[0x010d,0x106e,stack,1,0x000e]
 new += [0]*(len(u)-len(new))
 if len(new)!=len(u):raise ValueError('Code would grow')
 for i,v in enumerate(new):d.put_u16(x.data,m.insns_off+2*i,v)
 d.put_u32(x.data,m.code_off+8,0) # old per-method address table cannot describe moved code
 d.put_u32(x.data,t,18);x.data[t+12]=113
 for sec in x.sections:sec.update_signature_and_checksum();sec.verify_signature_and_checksum()
 patched=bytes(x.data)
 allowed=[(m.insns_off,m.insns_off+240),(m.code_off+8,m.code_off+12),(t,t+4),(t+12,t+13)]+[(s.base+8,s.base+32) for s in x.sections]
 if len(patched)!=len(payload) or any(a!=b and not any(lo<=i<hi for lo,hi in allowed) for i,(a,b) in enumerate(zip(payload,patched))):raise ValueError('Unexpected DEX mutation')
 v=d.DexContainer(patched);out=v.find_method(c['target_class'],c['target_method'],c['target_descriptor'])
 if out.units()[18:113]!=u[:95] or out.units()[:18]!=prefix:raise ValueError('Original normal body differs')
 # Execute actual emitted words, independently compare the four-condition contract.
 cases=0
 def execute(kind,locking,support,state):
  regs=[None]*16;regs[2]=kind;regs[3]=int(locking);pc=0;calls=0
  while pc<18:
   word=prefix[pc];op=word&255
   if op==0x12:regs[(word>>8)&15]=((word>>12)+8)%16-8;pc+=1
   elif op in (0x33,0x38,0x39):
    a=(word>>8)&15
    yes=regs[a]!=regs[word>>12] if op==0x33 else (regs[a]==0 if op==0x38 else regs[a]!=0)
    pc=pc+prefix[pc+1] if yes else pc+2
   elif op==0x63:
    if prefix[pc+1]!=flag:raise ValueError('Wrong capability field')
    regs[word>>8]=int(support);pc+=2
   elif op==0x71:
    if prefix[pc+1]!=native or prefix[pc+2]:raise ValueError('Wrong query')
    calls+=1;pc+=3
   elif op==0x0a:regs[word>>8]=state;pc+=1
   elif op==0xd0:
    a=(word>>8)&15;b=word>>12;value=regs[b]+prefix[pc+1];regs[a]=(value+2**31)%2**32-2**31;pc+=2
   else:raise ValueError('Unexpected emitted opcode')
  if pc!=18:raise ValueError('Branch outside original flow')
  return bool(regs[3]),calls
 for kind in range(-1,8):
  for lock in (False,True):
   for support in (False,True):
    for state in [-2147483648,-1007,-1006,-1005,-1000,-1,*range(0,7),2147483647]:
     actual,calls=execute(kind,lock,support,state)
     expected=False if kind==3 and lock and not support and state==-1006 else lock
     if actual!=expected or calls!=int(kind==3 and lock and not support):raise ValueError('Conditional semantics differ')
     cases+=1
 result=bytearray(raw);result[z.data_off:z.data_off+z.size]=patched;crc=binascii.crc32(patched)&0xffffffff;d.put_u32(result,z.local_crc_off,crc);d.put_u32(result,z.central_crc_off,crc)
 permitted=[(z.data_off+lo,z.data_off+hi) for lo,hi in allowed]+[(z.local_crc_off,z.local_crc_off+4),(z.central_crc_off,z.central_crc_off+4)]
 if any(a!=b and not any(lo<=i<hi for lo,hi in permitted) for i,(a,b) in enumerate(zip(raw,result))):raise ValueError('Other JAR bytes changed')
 if sha(result)!=c['output_sha256']:raise ValueError('Independently disassembled output differs')
 report={'id':'A59','input_jar_sha256':sha(raw),'output_jar_sha256':sha(result),'method':m.label(),'input_code_sha256':sha(old),'output_code_sha256':sha(patched[m.insns_off:m.insns_off+240]),'normal_flow_95_units_identical':True,'prefix_units':18,'condition_cases_passed':cases,'other_errors_and_valid_states_unchanged':True,'caller_permission_and_static_ta_lock_unchanged':True,'ta_state_property_unmodified':True,'catch_type_unchanged':True,'try_instruction_count_unchanged':94,'debug_cleared_only_for_target_method':True,'other_jar_bytes_identical':True,'runtime':'NOT_TESTED','release':'NOT_PASSED'}
 return bytes(result),report

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('input','profile','output','report'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or a.report.exists() or a.output.resolve()==a.report.resolve():raise ValueError('Fresh distinct output/report required')
 raw,r=prepare(a.input.read_bytes(),json.loads(a.profile.read_text()))
 r['profile_sha256']=sha(a.profile.read_bytes());r['patcher_sha256']=sha(Path(__file__).read_bytes());r['parser_sha256']=sha(Path(d.__file__).read_bytes())
 for f in (a.output,a.report):f.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('xb') as f:f.write(raw)
 with ZipFile(a.output) as z:
  if z.testzip():raise ValueError('Output ZIP CRC failure')
 a.report.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
