#!/usr/bin/env python3
"""Correct the inherited S9 hardware-light capability using the S6 baseline."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
BEFORE='2b34cd66c344805006b3efe2e656dcd98af0064df12d3992322ef06d26b4a3fd'
KEY='SEC_FLOATING_FEATURE_LCD_CONFIG_SELFMASK_VERSION'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 raw=a.input.read_bytes();old=f'<{KEY}>1</{KEY}>'.encode();new=f'<{KEY}>0</{KEY}>'.encode()
 if hashlib.sha256(raw).hexdigest()!=BEFORE or raw.count(old)!=1 or a.out.exists():raise ValueError('Exact reviewed input and fresh output required')
 result=raw.replace(old,new);tree=ET.fromstring(result)
 if tree.findtext(KEY)!='0' or sum(x!=y for x,y in zip(raw,result))!=1 or len(raw)!=len(result):raise ValueError('One byte XML capability correction required')
 a.out.mkdir(parents=True);(a.out/'floating_feature.xml').write_bytes(result)
 report={'id':'A66','classification':'DEVICE_REQUIRED','reason':'docs/BIOMETRIC_RUNTIME_UI85_A65.md','path':'system/etc/floating_feature.xml','before_sha256':BEFORE,'after_sha256':hashlib.sha256(result).hexdigest(),'bytes':len(result),'changed_bytes':1,'feature':KEY,'before_value':'1','after_value':'0','runtime':'NOT_TESTED','apk_or_authentication_changed':False}
 (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
