#!/sbin/sh
# Read-only T860 check. Only /tmp is written; optional CACHE mount is ro,noload.
# No flashing, module rename, SELinux changes, decryption, or automatic reboot.
set -eu
PATH=/sbin
LD_LIBRARY_PATH=/sbin
export PATH LD_LIBRARY_PATH
API=$1
OUTFD=$2
ZIP=$3
case "$API" in 3) ;; *) exit 2;; esac
case "$OUTFD" in ''|*[!0-9]*) exit 2;; esac
WORK=/tmp/t860-upgrade-check-a102-$$
umask 077
mkdir "$WORK"
OWN_CACHE=0
finish() {
    if [ "$OWN_CACHE" = 1 ]; then umount "$WORK/cache" || true; fi
}
trap finish EXIT
say() { printf 'ui_print %s\nui_print\n' "$*" > "/proc/self/fd/$OUTFD"; }
show() { while IFS= read -r line; do say "$line"; done < "$1"; }
say 'T860 A102 read-only upgrade check / 只读升级检查'
say 'This ZIP does not install a ROM or change DATA.'
[ "$(getprop ro.product.model)" = SM-T860 ] || { say 'Wrong device model'; exit 1; }
[ "$(id -u)" = 0 ] || { say 'Recovery root required'; exit 1; }
@@EXTRACT@@
# Validate the existing DATA mount before reading diagnostic directories.
data_count=$(awk '$2=="/data" {n++} END {print n+0}' /proc/mounts)
[ "$data_count" = 1 ] || { say 'DATA is not mounted exactly once; do not format it.'; exit 1; }
data_source=$(awk '$2=="/data" {print $1}' /proc/mounts)
data_type=$(awk '$2=="/data" {print $3}' /proc/mounts)
data_root=$(awk '$5=="/data" {n++; r=$4} END {if(n!=1)exit 1; print r}' /proc/self/mountinfo)
[ "$(readlink -f "$data_source")" = /dev/block/sda30 ] && [ "$data_type" = f2fs ] && [ "$data_root" = / ] || { say 'Unexpected DATA mount'; exit 1; }
say "SELinux: $(getenforce) (unchanged)"
# Ordinary encrypted DATA may be unavailable while module metadata is readable.
"$WORK/upgrade-access-probe" /data/system /data/apex/active /data/apex/sessions \
    /data/unencrypted /data/unencrypted/t860-metadata/apex/sessions \
    /metadata/apex/sessions > "$WORK/access.txt" 2>&1 || true
show "$WORK/access.txt"
cache_count=$(awk '$2=="/cache" {n++} END {print n+0}' /proc/mounts)
case "$cache_count" in
    0)
        mkdir "$WORK/cache"
        mount -t ext4 -o ro,noload /dev/block/sda27 "$WORK/cache" || { say 'Cannot inspect CACHE read-only'; exit 1; }
        OWN_CACHE=1; CACHE_ROOT=$WORK/cache;;
    1)
        cache_source=$(awk '$2=="/cache" {print $1}' /proc/mounts)
        cache_type=$(awk '$2=="/cache" {print $3}' /proc/mounts)
        cache_root=$(awk '$5=="/cache" {n++; r=$4} END {if(n!=1)exit 1; print r}' /proc/self/mountinfo)
        [ "$(readlink -f "$cache_source")" = /dev/block/sda27 ] && [ "$cache_type" = ext4 ] && [ "$cache_root" = / ] || { say 'Unexpected CACHE mount'; exit 1; }
        CACHE_ROOT=/cache;;
    *) say 'Ambiguous CACHE mounts'; exit 1;;
esac
result=0
"$WORK/mainline-guard-a100" --upgrade-preflight "$WORK/apex-factory.tsv" /data/apex/active \
    /data/apex/sessions "$CACHE_ROOT/apex/sessions" "$CACHE_ROOT/metadata/apex/sessions" \
    /metadata/apex/sessions > "$WORK/released-guard-check.txt" 2>&1 || result=$?
say "Released A100 guard exit=$result (known parameter mismatch)"
show "$WORK/released-guard-check.txt"
result=0
"$WORK/mainline-guard" --upgrade-preflight "$WORK/apex-factory.tsv" /data/apex/active \
    /data/apex/sessions "$CACHE_ROOT/apex/sessions" "$CACHE_ROOT/metadata/apex/sessions" \
    /metadata/apex/sessions > "$WORK/mainline-check.txt" 2>&1 || result=$?
say "UI8 module guard exit=$result"
show "$WORK/mainline-check.txt"
"$WORK/upgrade-access-probe" "$CACHE_ROOT/apex/sessions" "$CACHE_ROOT/metadata/apex/sessions" \
    "$CACHE_ROOT/t860-metadata/apex/sessions" "$CACHE_ROOT/t860-metadata-a82-legacy-retained/apex/sessions" \
    > "$WORK/cache-access.txt" 2>&1 || true
show "$WORK/cache-access.txt"
say "Check complete. Details: $WORK"
say 'Result diagnoses modules only; it does not approve an upgrade.'
say '可拍下以上模块报错；无需读取内部存储或格式化 DATA。'
