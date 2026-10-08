#!/usr/bin/env python3
"""A71 packaged-library command tests on files with original TWRP tools.

Block discovery and VENDOR inventory are modeled; real dd, ZIP extraction,
source hashing, Mainline guard, policy writes, rollback and ordering execute.
Run as root within a private Linux mount namespace with the fixed root bound
to itself and its own proc mount. No device nodes or real partitions exist.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--recovery-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--operation', choices=['upgrade','restore-a70'], default='upgrade')
    ap.add_argument('--installer-version', choices=['a71', 'a74', 'a99'], default='a71')
    a = ap.parse_args()
    recovery = a.recovery_root.resolve(strict=True)
    if os.geteuid() or (recovery / 'dev/block').exists() or a.out.exists():
        raise ValueError('isolated root/chroot without block nodes and fresh output required')
    tools = json.loads((recovery / 'tools-manifest.json').read_text())
    if tools['recovery_sha256'] != 'cbc6e03563a9229b7034dd775964ef412af94a7074f50b519ce1ccc1fd4f2e16':
        raise ValueError('fixed original Recovery required')
    spec = importlib.util.spec_from_file_location('transport', ROOT / 'scripts/build_twrp_upgrade.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    a99 = a.installer_version == 'a99'
    a74 = a.installer_version in ('a74','a99')
    if a74:
        sys.path.insert(0, str(ROOT / 'scripts'))
        from render_twrp_a74_support_ui85 import a74_support, CURRENT_A71
    results = []
    def inside(p): return '/' + p.relative_to(recovery).as_posix()
    with tempfile.TemporaryDirectory(prefix='a71-installer-test-', dir=recovery / 'tmp') as temporary:
        root = Path(temporary)
        images = {}
        for name, size in [('system', 40960), ('product', 8192)]:
            images[name] = root / ('new-' + name)
            images[name].write_bytes(('NEW-' + name).encode().ljust(size, b'\0'))
        audits = {n: {'bytes': p.stat().st_size, 'sha256': m.sha_file(p)} for n, p in images.items()}
        manifest = {'kind': 'NONFLASH_FIXTURE', 'candidate_id': 'A71-X710-EZH3-T860-UI85-REPAIRED',
                    'source_inventory_sha256': 'e21e7efaaa1e1d06154cda4dc63ae31c1e6d5f887f9b8929c0535304607f6df7'}
        manifest['support_stage_reference_sha256'] = manifest['source_inventory_sha256']
        if a74:
            manifest.update(candidate_id='A74-X710-EZH3-T860-UI85-FCM4-SDK30',
                            source_inventory_sha256='bf2f94d72b890db7397605f518800169cd9680424d0c366722f6db7a42fb4931',
                            support_stage_reference_sha256='bf2f94d72b890db7397605f518800169cd9680424d0c366722f6db7a42fb4931')
        if a99:
            from render_twrp_release_a99 import support as a99_support, SOURCE_SYSTEM
            tools_root=ROOT/'out/patch-probes/A99-release-tools-v3'
            a99_tools={n:(tools_root/n).read_bytes() for n in ('mainline-guard','fscrypt-readonly-probe')}
            manifest.update(partitions={'system':{'sha256':SOURCE_SYSTEM}},system_files_changed=False,product_factory_apex_changed=False)
            def a74_support(manifest, operation):return a99_support(manifest,a99_tools)
        package = root / 'NONFLASH-FIXTURE.zip'
        m.write_package(package, images, manifest, audits, operation=a.operation,
                        support_provider=a74_support if a74 else None)
        with ZipFile(package) as z:
            library = z.read('rom/libupgrade.sh')
        production_library_sha = __import__('hashlib').sha256(library).hexdigest()
        if a99:
            if library.count(SOURCE_SYSTEM.encode())!=1:raise ValueError('Target fixture constant ambiguous')
            library=library.replace(SOURCE_SYSTEM.encode(),audits['system']['sha256'].encode())
        if a99:library=library.replace(b'a71_extract_support() {',b'fixture_extract_support() {')
        if a.operation == 'restore-a70':
            # Only the two compiled target constants in the independent final
            # fragment use fixture hashes; transaction/control flow is intact.
            prefix, final = library.rsplit(b'# Independent recovery entry', 1)
            for part, value in [('system','226ac43e6d2bb9b504c1459ee074a31eb7f0ea752772793d099e6f1c9db1817b'),
                                ('product','3131ac9d1d7080731952d47d7abb11ee2feaeb63a3446858313917caaf1e4b29')]:
                if final.count(value.encode())!=1: raise AssertionError('restore constant scope changed')
                final=final.replace(value.encode(),audits[part]['sha256'].encode())
            library=prefix+b'# Independent recovery entry'+final
        cases = ['success-baseline', 'success-adapted', 'success-a46-source', 'success-a70-source', 'preflight-baseline', 'preflight-adapted',
                 'wrong-device', 'bad-source-hash', 'duplicate-oneui', 'bad-sdk', 'bad-oneui',
                 'retry-product', 'bad-retry-hash', 'bad-boot', 'bad-vendor',
                 'bad-payload', 'missing-support', 'corrupt-support', 'staged-session',
                 'older-active-apex', 'data-not-mounted', 'wrong-data-mount-root',
                 'wrong-data-block', 'wrong-cache-type', 'mount-probe-tool-error', 'duplicate-cache-mount', 'invalid-mode',
                 'policy-write-error', 'policy-readback-error', 'interrupt-policy-write',
                 'system-write-error', 'system-readback-error', 'product-write-error']
        if a.operation == 'restore-a70':
            cases=[c for c in cases if c not in {'success-a46-source','success-a70-source','bad-source-hash',
                'duplicate-oneui','bad-sdk','bad-oneui','retry-product','bad-retry-hash'}]
            cases+=['already-restored','wrong-restore-mode','wrong-restore-system-sha','wrong-restore-product-sha']
        if a74:
            cases += ['success-sdk30-baseline', 'success-sdk30-adapted', 'preflight-sdk30',
                      'bad-matrix' if a.operation == 'upgrade' else 'bad-matrix-metadata',
                      'matrix-write-error', 'matrix-readback-error', 'interrupt-matrix-write']
            if a.operation == 'upgrade':
                cases += ['success-a71-source', 'retry-product-sdk30']
            else:
                cases += ['damaged-configs-restore']
        if a99:
            cases.remove('older-active-apex')
            cases+=['success-clean-data-target-system','success-clean-system','preflight-clean-system','ui8-active-module-backup','clean-system-with-data-refused','metadata-checkpoint-refused']
        for case in cases:
            work = root / case; work.mkdir()
            payload = package
            if case in {'bad-payload', 'missing-support', 'corrupt-support'}:
                payload = work / 'NONFLASH-FIXTURE.zip'
                with ZipFile(package) as src, ZipFile(payload, 'w', compression=ZIP_DEFLATED) as dst:
                    for item in src.infolist():
                        if case == 'missing-support' and item.filename == 'rom/support/mainline-guard': continue
                        data = src.read(item.filename)
                        if (case == 'bad-payload' and item.filename == 'payload/system/0000.img'
                                or case == 'corrupt-support' and item.filename == ('rom/support/vendor-guard-sdk30' if a74 else 'rom/support/vendor-guard')):
                            data = b'X' + data[1:]
                        dst.writestr(item, data)
            with ZipFile(payload) as z:
                for n in ['upgrade.tsv', 'system.chunks', 'product.chunks']:
                    (work / n).write_bytes(z.read('rom/' + n))
            if case.startswith('wrong-restore-'):
                cfg=work/'upgrade.tsv';text=cfg.read_text()
                if case=='wrong-restore-mode': text=text.replace('A70_STABLE_SNAPSHOT','UNKNOWN')
                else:
                    part='system' if case=='wrong-restore-system-sha' else 'product'
                    text=text.replace(audits[part]['sha256'],'0'*64)
                cfg.write_text(text)
            for name, size in [('system', 40960), ('product', 8192), ('boot', 4096), ('vendor', 8192), ('userdata', 4096)]:
                (work / name).write_bytes(('OLD-' + name).encode().ljust(size, b'\0'))
            if case in {'retry-product', 'retry-product-sdk30','success-clean-data-target-system'}: (work / 'system').write_bytes(images['system'].read_bytes())
            if case == 'already-restored':
                for n in images: (work/n).write_bytes(images[n].read_bytes())
            before = {n: m.sha_file(work / n) for n in ['system', 'product', 'boot', 'vendor', 'userdata']}
            case_library = library
            if case == 'success-a71-source':
                if case_library.count(CURRENT_A71.encode()) != 1:
                    raise AssertionError('A71 source fixture constant scope differs')
                case_library = case_library.replace(CURRENT_A71.encode(), before['system'].encode())
            (work / 'libupgrade.sh').write_bytes(case_library)
            source = work / 'source-system/system'; source.mkdir(parents=True)
            oneui = '80500' if case in {'retry-product', 'retry-product-sdk30', 'bad-retry-hash', 'success-a70-source', 'success-a71-source','success-clean-data-target-system'} else ('70000' if case == 'bad-oneui' else '80000')
            (source / 'build.prop').write_text('ro.product.system.model=SM-T860\n' +
                f'ro.build.version.sdk={"35" if case == "bad-sdk" else "36"}\nro.build.version.oneui={oneui}\n' +
                ('ro.build.version.oneui=80000\n' if case == 'duplicate-oneui' else ''))
            if a99 and case in {'success-clean-system','preflight-clean-system','clean-system-with-data-refused'}:
                (source/'build.prop').unlink();source.rmdir()
            vendor = work / 'source-vendor'; (vendor / 'etc/seccomp_policy').mkdir(parents=True)
            policy = vendor / 'etc/seccomp_policy/samsung.software.media.c2-base-policy'
            prebuilt = ROOT / ('device/s6/prebuilts/installer-a74' if a74 else 'device/s6/prebuilts/installer-a71')
            original = (prebuilt / 'vendor-before-policy').read_bytes()
            adapted = (prebuilt / 'vendor-after-policy').read_bytes()
            policy.write_bytes(adapted if case in {'success-adapted', 'preflight-adapted', 'success-sdk30-adapted', 'preflight-sdk30', 'retry-product-sdk30'} else original)
            matrix = None
            if a74:
                (vendor / 'etc/vintf').mkdir()
                matrix = vendor / 'etc/vintf/compatibility_matrix.xml'
                matrix28 = (prebuilt / 'vendor-matrix28').read_bytes(); matrix30 = (prebuilt / 'vendor-matrix30').read_bytes()
                matrix.write_bytes(matrix30 if case in {'success-sdk30-baseline','success-sdk30-adapted','preflight-sdk30','retry-product-sdk30'} else matrix28)
                if case in {'bad-matrix', 'damaged-configs-restore'}:
                    matrix.write_bytes(b'<compatibility-')
                if case == 'bad-matrix-metadata': matrix.chmod(0o600)
                if case == 'damaged-configs-restore': policy.write_bytes(b'mremap:')
                initial_matrix = matrix.read_bytes(); matrix_inode = matrix.stat().st_ino
            policy.chmod(0o644); initial_policy = policy.read_bytes(); inode_before = policy.stat().st_ino
            (vendor / 'preserved-HAL-fixture').write_bytes(b'unchanged hardware fixture')
            data = work / 'data-fixture'; data.mkdir(); (data / 'apex/active').mkdir(parents=True)
            cache = work / 'cache-fixture'; cache.mkdir()
            if not a99:(cache / 't860-metadata/apex/sessions').mkdir(parents=True)
            if a99:
                if case not in {'success-clean-system','preflight-clean-system','success-clean-data-target-system'}:
                    (data/'system').mkdir();(data/'system/locksettings-fixture').write_bytes(b'preserved user state')
                if case in {'retry-product','retry-product-sdk30'}:
                    (data/'unencrypted/t860-metadata').mkdir(parents=True);(data/'unencrypted').chmod(0o700);(data/'unencrypted/t860-metadata').chmod(0o755)
                if case=='ui8-active-module-backup':
                    path=data/'apex/active/com.android.tethering@372038420.apex';path.write_bytes(b'opaque encrypted module');path.chmod(0o644);os.chown(path,1000,1000)
                if case=='metadata-checkpoint-refused':
                    (data/'unencrypted/t860-metadata/vold').mkdir(parents=True);(data/'unencrypted/t860-metadata/vold/checkpoint').write_bytes(b'pending')
            if case == 'staged-session':
                session = cache / ('apex/sessions/123' if a99 else 't860-metadata/apex/sessions/123'); session.mkdir(parents=True); (session / 'state').write_bytes(b'\x10\x02')
            if case == 'older-active-apex': (data / 'apex/active/com.android.tethering@1.apex').write_bytes(b'unverified')
            before_data = {str(p.relative_to(data)): m.sha_file(p) for p in data.rglob('*') if p.is_file()}
            before_cache = {str(p.relative_to(cache)): m.sha_file(p) for p in cache.rglob('*') if p.is_file()}
            work_inside = inside(work)
            (work / 'fake-mounts').write_text(
                ('' if case == 'data-not-mounted' else f'{work_inside}/{"vendor" if case == "wrong-data-block" else "userdata"} /data f2fs rw 0 0\n') +
                f'{work_inside}/cache-device /cache {"f2fs" if case == "wrong-cache-type" else "ext4"} rw 0 0\n' +
                (f'{work_inside}/cache-device /cache ext4 rw 0 0\n' if case == 'duplicate-cache-mount' else ''))
            (work / 'fake-mountinfo').write_text(
                f'9 8 0:1 {"/wrong" if case == "wrong-data-mount-root" else "/"} /data rw - f2fs {work_inside}/userdata rw\n' +
                f'10 8 0:2 / /cache rw - ext4 {work_inside}/cache-device rw\n')
            (work / 'cache-device').write_bytes(b'cache block fixture')
            mode = '--preflight-only' if case.startswith('preflight') else ('--bad-mode' if case == 'invalid-mode' else '')
            harness = work / 'run.sh'
            vendor_model = f'''vendor_guard_state() {{
 {'return 1' if case in {'bad-vendor','bad-matrix-metadata'} else ':'}
 h=$(hash_file "$VENDOR_MOUNT/$VENDOR_POLICY_REL")
 case "$h" in e529d80729976c2ef41f6831820da5f387b7cdbd44f8b1b33d0e7cf9cd1462b8) media=BASELINE ;; efae1217c1fd598fb80f390a510c857d7adc3ff8018dc3a2571c7d32e7e3bfcc) media=ADAPTED ;; *) return 1 ;; esac
 h=$(hash_file "$VENDOR_MOUNT/$VENDOR_MATRIX_REL")
 case "$h" in da6aa90c2c2bdc06208ec8f3342735df0358836ddddb72d6e183b49bff8a79ee) sdk=SDK28 ;; d3b80d5fa526f1cf005e0dcfd3c1747bb10e351664d648cc3c18690134129258) sdk=SDK30 ;; *) return 1 ;; esac
 case "$1:$media" in any:*|baseline:BASELINE|adapted:ADAPTED) printf '%s\\n' "${{sdk}}_${{media}}" ;; *) return 1 ;; esac
}}
vendor_recovery_eligible() {{
 {'return 1' if case in {'bad-vendor','bad-matrix-metadata'} else '[ "$(command cat "$VENDOR_MOUNT/preserved-HAL-fixture")" = "unchanged hardware fixture" ]'}
}}
''' if a74 else ''
            matrix_fault = f'''case "$1" in "$WORK/vendor-matrix28"|"$WORK/vendor-matrix30")
 printf 'matrix-write\\n' >> "$WORK/events"
 if [ ! -f "$WORK/matrix-fault-used" ]; then
  {'command touch "$WORK/matrix-fault-used"; return 1' if case == 'matrix-write-error' else ':'}
  {'command touch "$WORK/matrix-fault-used"; kill -TERM $$; return 1' if case == 'interrupt-matrix-write' else ':'}
  {'command touch "$WORK/matrix-fault-used"; printf BROKEN; return 0' if case == 'matrix-readback-error' else ':'}
 fi
 ;; esac
''' if a74 else ''
            awk_fault = '''case "$*" in *'/proc/mounts') case "$1" in *'/cache'*) return 42 ;; esac ;; esac''' if case == 'mount-probe-tool-error' else ':'
            harness.write_text(f'''set -eu
set -o pipefail
PATH=/sbin; LD_LIBRARY_PATH=/sbin; export PATH LD_LIBRARY_PATH
WORK='{work_inside}'; ZIP='{inside(payload)}'; SOURCE_MOUNT="$WORK/source-system"
set -- 3 1 "$ZIP" '{mode}'
. "$WORK/libupgrade.sh"
SYSTEM_BLOCK="$WORK/system"; PRODUCT_BLOCK="$WORK/product"
BOOT_BLOCK="$WORK/boot"; VENDOR_BLOCK="$WORK/vendor"
SYSTEM_BYTES=40960; PRODUCT_BYTES=8192; BOOT_BYTES=4096; VENDOR_BYTES=8192
DATA_BLOCK="$WORK/userdata"; CACHE_BLOCK="$WORK/cache-device"
A71_SOURCE_SYSTEM_SHA={'0'*64 if case in {'bad-source-hash','success-a46-source'} else before['system']}
A71_SOURCE_A46_SHA={before['system'] if case == 'success-a46-source' else '0'*64}
A71_SOURCE_A70_SHA={before['system'] if case == 'success-a70-source' else '0'*64}
BOOT_SHA={'0'*64 if case == 'bad-boot' else before['boot']}
exec 3>&1
ui_print() {{ printf 'ui_print %s\\nui_print\\n' "$*" >&3; }}
abort() {{ ui_print "ERROR: $*"; exit 1; }}
trap cleanup EXIT
trap 'abort "Interrupted"' HUP INT TERM
getprop() {{ printf '%s\\n' {'SM-X710' if case == 'wrong-device' else 'SM-T860'}; }}
require_block() {{ [ -f "$1" ] || abort 'Fixture block missing'; }}
check_block() {{ require_block "$2"; }}
readlink() {{
 case "$*" in '-f /dev/block/by-name/userdata') printf '%s\\n' "$DATA_BLOCK" ;; *) command readlink "$@" ;; esac
}}
awk() {{
 {awk_fault}
 case "$*" in
  *'/proc/mounts')
   case "$#" in 2) command awk "$1" "$WORK/fake-mounts" ;; 4) command awk "$1" "$2" "$3" "$WORK/fake-mounts" ;; *) return 99 ;; esac ;;
  *'/proc/self/mountinfo') command awk "$1" "$2" "$3" "$WORK/fake-mountinfo" ;;
  *) command awk "$@" ;;
 esac
}}
a71_extract_support() {{ fixture_extract_support; printf '%s\\n' '#!/sbin/sh' 'exit 0' > \"$WORK/fscrypt-readonly-probe\"; chmod 0700 \"$WORK/fscrypt-readonly-probe\"; }}
mkdir() {{ if [ "$*" = "$SOURCE_MOUNT" ]; then return 0; fi; command mkdir "$@"; }}
rmdir() {{ if [ "$*" = "$SOURCE_MOUNT" ]; then return 0; fi; command rmdir "$@"; }}
mount() {{ printf 'mount %s\\n' "$*" >> "$WORK/events"; return 0; }}
umount() {{ printf 'umount %s\\n' "$*" >> "$WORK/events"; return 0; }}
rm() {{
 if [ "$*" = "-rf $WORK" ]; then printf 'cleanup-request\\n' >> "$WORK/events"; return 0; fi
 command rm "$@"
}}
{'check_source_identity() { abort "Restore must not inspect broken SOURCE"; }' if a.operation=='restore-a70' else (':' if a99 else 'check_source_system() { check_source_identity; }')}
vendor_guard_state() {{
 {'return 1' if case == 'bad-vendor' else ':'}
 h=$(hash_file "$VENDOR_MOUNT/$VENDOR_POLICY_REL")
 case "$h" in "$VENDOR_BEFORE_SHA") state=BASELINE ;; "$VENDOR_AFTER_SHA") state=ADAPTED ;; *) return 1 ;; esac
 case "$1:$state" in any:*|baseline:BASELINE|adapted:ADAPTED) printf '%s\\n' "$state" ;; *) return 1 ;; esac
}}
{vendor_model}
cat() {{
 {matrix_fault}
 case "$1" in "$WORK/vendor-after-policy")
  printf 'policy-write\\n' >> "$WORK/events"
  {'return 1' if case == 'policy-write-error' else ':'}
  {'kill -TERM $$; return 1' if case == 'interrupt-policy-write' else ':'}
  {'printf BROKEN; return 0' if case == 'policy-readback-error' else ':'}
  ;; esac
 command cat "$@"
}}
write_raw() {{
 destination=''
 for arg in "$@"; do case "$arg" in of=*) destination=${{arg#of=}} ;; esac; done
 case "$destination" in "$SYSTEM_BLOCK"|"$PRODUCT_BLOCK") ;; *) abort 'Unexpected write target' ;; esac
 printf 'partition-write %s\\n' "$destination" >> "$WORK/events"
 {'return 1' if case == 'system-write-error' else ':'}
 {'[ "$destination" != "$PRODUCT_BLOCK" ] || return 1' if case == 'product-write-error' else ':'}
 command toybox dd "$@"
 {'printf X | command toybox dd of="$destination" bs=1 count=1 conv=notrunc 2>/dev/null' if case == 'system-readback-error' else ':'}
}}
upgrade_main
''')
            for point, fixture in [('data', data), ('cache', cache)]:
                destination = recovery / point; destination.mkdir(exist_ok=True)
                if any(destination.iterdir()): raise ValueError('chroot fixture mount point must be empty')
                subprocess.run(['mount', '--bind', str(fixture), str(destination)], check=True)
            try:
                r = subprocess.run(['chroot', str(recovery), '/sbin/sh', inside(harness)],
                    env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LD_LIBRARY_PATH':'/sbin'}, capture_output=True, text=True, timeout=20)
            finally:
                for point in ['cache', 'data']: subprocess.run(['umount', str(recovery / point)], check=True)
            events = (work / 'events').read_text().splitlines() if (work / 'events').exists() else []
            writes = [s for s in events if s.startswith('partition-write ')]
            succeeded = case in {'success-baseline','success-adapted','success-a46-source','success-a70-source','preflight-baseline','preflight-adapted','retry-product','already-restored',
                                 'success-sdk30-baseline','success-sdk30-adapted','preflight-sdk30','success-a71-source','retry-product-sdk30','damaged-configs-restore','success-clean-system','preflight-clean-system','ui8-active-module-backup','success-clean-data-target-system'}
            if bool(r.returncode == 0) != succeeded:
                raise AssertionError(f'{case}: {r.returncode}\n{r.stdout}\n{r.stderr}')
            after = {n: m.sha_file(work / n) for n in before}
            if any(before[n] != after[n] for n in ['boot','vendor','userdata']): raise AssertionError('hardware/DATA changed')
            if policy.stat().st_ino != inode_before or (vendor / 'preserved-HAL-fixture').read_bytes() != b'unchanged hardware fixture': raise AssertionError('vendor inode/hardware changed')
            if a99 and case=='ui8-active-module-backup' and succeeded:
                before_data={n+('.A99-held' if n.endswith('.apex') else ''):v for n,v in before_data.items()}
            if before_data != {str(p.relative_to(data)):m.sha_file(p) for p in data.rglob('*') if p.is_file()} or before_cache != {str(p.relative_to(cache)):m.sha_file(p) for p in cache.rglob('*') if p.is_file()}: raise AssertionError('module/session fixtures changed')
            if succeeded and not case.startswith('preflight'):
                if after['system'] != audits['system']['sha256'] or after['product'] != audits['product']['sha256'] or policy.read_bytes() != adapted: raise AssertionError('success readback mismatch')
                if len(writes) != (1 if case in {'retry-product','retry-product-sdk30','success-clean-data-target-system'} else 2): raise AssertionError('write count mismatch')
            elif case not in {'system-write-error','system-readback-error','product-write-error'}:
                if writes or before['system'] != after['system'] or before['product'] != after['product']: raise AssertionError('early write')
            if case in {'system-write-error','system-readback-error'} and (len(writes)!=1 or before['product']!=after['product']): raise AssertionError('continued after SYSTEM failure')
            if case == 'product-write-error' and (len(writes)!=2 or after['system']!=audits['system']['sha256'] or before['product']!=after['product']): raise AssertionError('unexpected PRODUCT failure state')
            if not succeeded and policy.read_bytes() != initial_policy:
                raise AssertionError(f'{case}: policy restoration failed\n{r.stdout}\n{r.stderr}\n{events}')
            if a74:
                expected_matrix = (matrix30 if a.operation == 'upgrade' else matrix28) if succeeded and not case.startswith('preflight') else initial_matrix
                if matrix.read_bytes() != expected_matrix or matrix.stat().st_ino != matrix_inode:
                    raise AssertionError(f'{case}: matrix target/rollback/inode failed\n{r.stdout}\n{r.stderr}\n{events}')
                if (case.startswith('preflight') or not succeeded and case not in {'matrix-write-error','matrix-readback-error','interrupt-matrix-write','policy-write-error','policy-readback-error','interrupt-policy-write','system-write-error','system-readback-error','product-write-error'}) and 'matrix-write' in events:
                    raise AssertionError('matrix written before successful preflight')
                if 'matrix-write' in events and writes and events.index('matrix-write') > events.index(writes[0]):
                    raise AssertionError('matrix must precede partition writes')
            if case.startswith('preflight') and (policy.read_bytes() != initial_policy or 'policy-write' in events): raise AssertionError('preflight wrote policy')
            if 'policy-write' in events and writes and events.index('policy-write') > events.index(writes[0]): raise AssertionError('wrong write order')
            results.append({'case':case,'pass':True,'exit':r.returncode,'partition_write_calls':len(writes),
                'policy_changed_on_success_only':True,'hardware_userdata_modules_sessions_preserved':True})
        report = {'id':'A99_DUAL_INSTALLER_TESTS' if a99 else 'A74_FORMAT3_INSTALLER_TESTS' if a74 else 'A71_FORMAT2_INSTALLER_TESTS','all_passed':True,'case_count':len(results),'cases':results,
            'library_sha256':m.sha_file(root / 'success-baseline/libupgrade.sh'),
            'production_library_sha256':production_library_sha,'operation':a.operation,
            'fixture_restore_target_constants':a.operation=='restore-a70',
            'fixture_a71_source_constant':a74 and a.operation=='upgrade',
            'scope':'original TWRP tools/Linux namespace; real ZIP/SHA/dd/Mainline guard and policy transaction on fixtures; VENDOR inventory/block/mount discovery and fscrypt ioctl discovery modeled',
            'recovery_sha256':tools['recovery_sha256'],'test_source_sha256':m.sha_file(Path(__file__)),
            'actual_device_upgrade':'NOT_TESTED','device_writes':False}
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='cases'}))


if __name__ == '__main__': main()
