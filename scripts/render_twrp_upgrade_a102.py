"""Improve A100 upgrade diagnostics without changing its source/safety rules.

This is an installer candidate, not an approved no-DATA upgrade path.
The A100 release archive and all frozen A99 inputs remain unchanged.
"""
import hashlib
from render_twrp_a74_support_ui85 import replace_once

A100_LIBRARY = 'e00a71b7ec3e92a6457ffa4e229b8fec01fea903cea26ee09f7c037669b9e4b2'
OLD_GUARD = 'f0b671505a818808adc788d2524974b8fe3fd6c7365602d6b4a8443394335c66'
FIXED_GUARD = '4f3f04af10250a0522b4bf2805fe0567fef975da1aea9e24024d86eba8ca8176'

HELPERS = r'''
a102_access_preflight() {
    if "$WORK/upgrade-access-probe" /data/apex/active /data/apex/sessions > "$WORK/module-access.txt" 2>&1; then
        return 0
    fi
    while IFS= read -r line; do ui_print "$line"; done < "$WORK/module-access.txt"
    abort 'Required module directories are unreadable/unsafe in this Recovery. No partition writes performed; do not format DATA.'
}
a102_module_abort() {
    evidence=$1
    message=$2
    if [ -f "$WORK/$evidence" ]; then
        while IFS= read -r line; do ui_print "$line"; done < "$WORK/$evidence"
    fi
    abort "$message"
}
'''

def derive(library: bytes, probe: bytes, guard: bytes) -> bytes:
    if hashlib.sha256(library).hexdigest() != A100_LIBRARY:
        raise ValueError('Only the exact released A100 upgrade library is accepted')
    text = library.decode()
    if hashlib.sha256(guard).hexdigest() != FIXED_GUARD:
        raise ValueError('Reviewed upgrade-capable A99 v3 guard required')
    text = replace_once(text, 'mainline-guard\t2239088\t'+OLD_GUARD,
                        'mainline-guard\t'+str(len(guard))+'\t'+FIXED_GUARD)
    text = replace_once(text, "'\nCACHE_BLOCK", '\nupgrade-access-probe\t'+str(len(probe))+'\t'+hashlib.sha256(probe).hexdigest()+"'\nCACHE_BLOCK")
    # Executable and checksum validation uses the existing support extraction.
    anchor = "\ncheck_source_system() {\n    if a99_data_fresh; then abort 'Upgrade ZIP requires"
    text = replace_once(text, anchor, HELPERS+anchor)
    text = replace_once(text, '    a71_extract_support\n    chmod 0700 "$WORK/ui8-release-guard"', '    a71_extract_support\n    chmod 0700 "$WORK/upgrade-access-probe"\n    a102_access_preflight\n    chmod 0700 "$WORK/ui8-release-guard"')
    for old, receipt in [
        ('Pending or unsafe system module state; no updates removed', 'mainline-check.txt'),
        ('Active/session state differs; no updates removed', 'mainline-check.txt'),
        ('Module backup refused; user data not cleared', 'mainline-backup.txt'),
    ]:
        text = replace_once(text, "|| abort '"+old+"'", "|| a102_module_abort "+receipt+" '"+old+"'")
    return text.encode()
