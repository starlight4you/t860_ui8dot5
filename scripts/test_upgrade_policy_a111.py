#!/usr/bin/env python3
"""Exercise final installer control flow without exposing any device blocks."""
import hashlib,json,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ZIP=ROOT/'out/releases/v1.0.3-A111-Cumulative/TabS6-OneUI8.5-v1.0.3-A111-Upgrade-TWRP.zip'
CASES={'normal':(0,['vendor','system','product']),'retry_after_partial':(0,['vendor','system','product']),'preflight':(0,[]),'wrong_model':(90,[]),'bad_payload':(90,[]),'unsafe_modules':(90,[]),'unwritable_target':(90,[]),'wrong_hardware':(90,[]),'post_hardware_failure':(90,['vendor','system','product'])}
HARNESS=r'''
set -eu
set -o pipefail
WORK=$1
ZIP=$2
CASE=$3
. "$WORK/libupgrade.sh"
ui_print(){ printf '%s\n' "$*"; }
abort(){ printf 'ABORT: %s\n' "$*"; exit 90; }
# These calls are forbidden even on a previously modified/partially written source.
check_source_system(){ abort SOURCE_VERSION_GATE_CALLED; }
check_source_identity(){ abort SOURCE_VERSION_GATE_CALLED; }
old_property(){ abort SOURCE_VERSION_GATE_CALLED; }
vendor_guard_state(){ abort SOURCE_TREE_GATE_CALLED; }
getprop(){ [ "$1" = ro.product.model ] || abort UNEXPECTED_PROPERTY_READ; if [ "$CASE" = wrong_model ]; then printf 'SM-T865'; else printf 'SM-T860'; fi; }
check_block(){ case "$1" in system|product|vendor|boot|dtbo|vbmeta) ;; *) abort WRONG_BLOCK;; esac; }
a71_existing_mount(){ return 0; }
a71_extract_support(){ return 0; }
a102_access_preflight(){ return 0; }
verify_payload(){ [ "$CASE" != bad_payload ] || abort BAD_PAYLOAD; }
a71_check_mainline(){ [ "$CASE" != unsafe_modules ] || abort UNSAFE_MODULES; }
unmount_targets(){ [ "$CASE" != unwritable_target ] || abort UNWRITABLE_TARGET; }
hardware_calls=0
check_hardware(){ hardware_calls=$((hardware_calls+1)); [ "$CASE" != wrong_hardware ] || abort WRONG_HARDWARE; if [ "$CASE" = post_hardware_failure ] && [ "$hardware_calls" = 2 ]; then abort POST_HARDWARE; fi; }
write_partition(){ printf '%s\n' "$1" >> "$WORK/writes"; }
UPGRADE_PREFLIGHT_ONLY=
[ "$CASE" != preflight ] || UPGRADE_PREFLIGHT_ONLY=--preflight-only
upgrade_main
[ "$A71_COMPLETE" = 1 ] || abort NOT_COMPLETE
'''
def main():
 rows=[]
 with zipfile.ZipFile(ZIP) as z,tempfile.TemporaryDirectory(prefix='a111-control-') as t:
  root=Path(t)
  library=z.read('rom/libupgrade.sh');assert not any(s in library for s in [b'check_source_system()',b'old_property()',b'system-guard',b'vendor-guard',b'UI8_UPGRADE',b'installed_oneui'])
  for n in ['libupgrade.sh','upgrade.tsv','system.chunks','product.chunks','vendor.chunks']:(root/n).write_bytes(z.read('rom/'+n))
  (root/'test.sh').write_text(HARNESS)
  for case,(code,writes) in CASES.items():
   (root/'writes').write_text('');r=subprocess.run(['/bin/bash',str(root/'test.sh'),str(root),str(ZIP),case],capture_output=True,text=True)
   observed=(root/'writes').read_text().splitlines()
   if r.returncode!=code or observed!=writes:raise ValueError((case,r.returncode,observed,r.stdout,r.stderr))
   assert 'GATE_CALLED' not in r.stdout
   rows.append({'case':case,'exit':code,'partition_write_calls':observed,'pass':True})
 report={'id':'A111_INSTALLER_CONTROL_FLOW','cases':rows,'source_version_or_tree_gate_calls':0,'all_passed':True,'device_blocks_accessed':False,'real_payload_validation':'SEPARATE_ORIGINAL_TWRP_PROBE','test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (ROOT/'docs/audit/cumulative-installer-policy-a111.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
