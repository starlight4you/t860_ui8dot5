"""Build a small installer with no installed ROM version or source-tree whitelist."""
import hashlib,re,zipfile
from pathlib import Path

def digest(b):return hashlib.sha256(b).hexdigest()
def function(text,name):
 rows=re.findall(r'^'+re.escape(name)+r'\(\) \{.*?^\}',text,re.M|re.S)
 if not rows:raise ValueError('Missing function '+name)
 return rows[-1]
def support(source):
 with zipfile.ZipFile(source) as z:
  old=z.read('rom/libupgrade.sh').decode()
  assert digest(old.encode())=='371ae95aacec25aae496e9d2796c967c8253b847e980cbbca16ce31690e61daa'
  names=['mainline-guard','apex-factory.tsv','fscrypt-readonly-probe','partition-probe','upgrade-access-probe']
  extras={n:z.read('rom/support/'+n) for n in names}
 text=old[:old.index('old_property() {')]
 text=text[:text.index('check_preserved_hardware() {')]
 text+='\nDTBO_BLOCK=/dev/block/sda19\nDTBO_BYTES=10485760\nDTBO_SHA=864ca763a1362a77aa929c3e2f147baa70196c31401b52f76bf0f879d7eb99ec\nVBMETA_BLOCK=/dev/block/sdd22\nVBMETA_BYTES=65536\nCACHE_BLOCK=/dev/block/sda27\nCACHE_BYTES=419430400\nDATA_BLOCK=/dev/block/sda30\nCACHE_MOUNT=$WORK/source-cache\nCACHE_OWN_MOUNT=0\nA71_COMPLETE=0\nA99_SOURCE_MODE=IDENTICAL_REINSTALL\nUPGRADE_PREFLIGHT_ONLY=${4:-}\n'
 text+="A111_SUPPORT_ROWS='"+'\n'.join(n+'\t'+str(len(b))+'\t'+digest(b) for n,b in extras.items())+"'\n"
 for n in ['verify_table','extract_chunk','verify_payload','write_partition','a71_existing_mount','a102_access_preflight','a102_module_abort','a99_check_vbmeta_source']:
  f=function(old,n)
  if n=='verify_payload':f=f.replace('for part in system product;', 'for part in system product vendor;')
  text+=f+'\n'
 mainline=function(old,'a71_check_mainline')
 start=mainline.index('    if [ "$A99_SOURCE_MODE" = IDENTICAL_REINSTALL ]; then')
 end=mainline.index('    if [ "$CACHE_OWN_MOUNT" = 1 ]; then',start)
 branch=mainline[start:end];keep=branch[branch.index('        for p in /data /data/unencrypted'):branch.index('\n    else\n')]
 keep=keep.replace("Reviewed compatible SYSTEM update: current DATA metadata and existing active modules preserved.","Current DATA metadata and compatible active modules preserved.")
 mainline=mainline[:start]+keep+'\n'+mainline[end:]
 text+=mainline+'\n'+(Path(__file__).resolve().parents[1]/'installer/libupgrade-a111.sh').read_text()
 assert not any(s in text for s in ['old_property','check_source_identity','check_source_system','system-guard','vendor-guard','installed_oneui','UI8_UPGRADE'])
 return text.encode(),extras
