#!/usr/bin/env python3
"""Install pinned T860 VNDK30 APEX and close X710 mapping/30.0 declarations.

Only accepts a copied, labelled Linux staging tree. The donor mount and old
working images are inputs for comparison, never patch targets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


MAPPING_REL = Path("system/system_ext/etc/selinux/mapping/30.0.cil")
APEX_REL = Path("system/system_ext/apex/com.android.vndk.v30.apex")
V33_REL = Path("system/system_ext/apex/com.android.vndk.v33.apex")
LABEL = b"u:object_r:system_file:s0"
DECL = re.compile(rb"^\(typeattribute ([^ )]+)\)$", re.MULTILINE)
EXPAND = re.compile(rb"^\(expandtypeattribute \(([^ )]+)\) (?:true|false)\)$", re.MULTILINE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch {path}: {actual} != {expected}")


def xattr(path: Path, name: str) -> bytes:
    return os.getxattr(path, name, follow_symlinks=False)


def copy_metadata(source: Path, target: Path) -> None:
    stat = source.stat()
    os.chown(target, stat.st_uid, stat.st_gid)
    os.chmod(target, stat.st_mode & 0o7777)
    for name in os.listxattr(source, follow_symlinks=False):
        os.setxattr(target, name, xattr(source, name), follow_symlinks=False)


def temp_in(parent: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix=".t860-vndk30-", dir=parent)
    os.close(fd)
    return Path(name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--apex", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    if spec.get("patch_id") != "B04" or spec.get("classification") != "DEVICE_REQUIRED":
        raise ValueError("unexpected VNDK30 patch spec")
    if (spec.get("selinux_context") != LABEL.decode() or
            spec.get("owner") != "0:0" or spec.get("file_mode") != "0644"):
        raise ValueError("unexpected owner/mode/SELinux contract")

    if os.uname().sysname != "Linux" or os.geteuid() != 0:
        raise ValueError("requires root on Linux for owner and SELinux xattr preservation")
    stage = args.stage.resolve(strict=True)
    stage_marker = ((stage / "capacity-stage-log.json").is_file() or
                    (stage / "rebase-stage.json").is_file())
    if not str(stage).startswith("/var/tmp/t860-") or not stage_marker:
        raise ValueError("stage must be an isolated /var/tmp/t860-* copy with a stage marker")
    if args.out.resolve().is_relative_to(stage):
        raise ValueError("audit output must be outside the staging tree")
    mount_options = subprocess.check_output(
        ["findmnt", "-no", "OPTIONS", "-T", str(stage)], text=True
    ).strip().split(",")
    if "ro" in mount_options:
        raise ValueError("staging filesystem is read-only")

    mapping = stage / MAPPING_REL
    target = stage / APEX_REL
    v33 = stage / V33_REL
    for path in (mapping, target, v33):
        if not path.parent.resolve(strict=True).is_relative_to(stage):
            raise ValueError(f"staging path escapes stage: {path}")
    for path in (mapping, v33, args.apex):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing or symlinked input: {path}")
    if target.exists() or target.is_symlink():
        raise ValueError(f"refusing to replace an existing VNDK30 APEX: {target}")
    require_sha(mapping, spec["mapping_input_sha256"])
    require_sha(args.apex, spec["apex_sha256"])
    for path in (mapping, v33):
        stat = path.stat()
        if (stat.st_uid, stat.st_gid, stat.st_mode & 0o7777) != (0, 0, 0o644):
            raise ValueError(f"unexpected owner/mode: {path}")
    if xattr(mapping, "security.selinux") != LABEL or xattr(v33, "security.selinux") != LABEL:
        raise ValueError("unexpected donor SELinux label")
    if "com.android.vndk.v30" not in subprocess.check_output(["unzip", "-p", str(args.apex), "apex_manifest.pb"]).decode("latin1"):
        raise ValueError("APEX manifest does not name com.android.vndk.v30")

    original = mapping.read_bytes()
    declared = set(DECL.findall(original))
    expanded = set(EXPAND.findall(original))
    missing = sorted(expanded - declared)
    if len(missing) != spec["missing_typeattributes"]:
        raise ValueError(f"mapping symbol count changed: {len(missing)} != {spec['missing_typeattributes']}")
    patched = b"".join(b"(typeattribute " + name + b")\n" for name in missing) + original
    if hashlib.sha256(patched).hexdigest() != spec["mapping_output_sha256"]:
        raise ValueError("mapping output hash does not match pinned patch")
    if set(EXPAND.findall(patched)) - set(DECL.findall(patched)):
        raise ValueError("mapping symbol closure failed")

    mapping_tmp = temp_in(mapping.parent)
    apex_tmp = temp_in(target.parent)
    published = False
    try:
        mapping_tmp.write_bytes(patched)
        copy_metadata(mapping, mapping_tmp)
        shutil.copyfile(args.apex, apex_tmp)
        copy_metadata(v33, apex_tmp)
        require_sha(apex_tmp, spec["apex_sha256"])
        if xattr(mapping_tmp, "security.selinux") != LABEL or xattr(apex_tmp, "security.selinux") != LABEL:
            raise ValueError("staged SELinux label mismatch")
        os.replace(apex_tmp, target)
        published = True
        os.replace(mapping_tmp, mapping)
        published = False
    finally:
        mapping_tmp.unlink(missing_ok=True)
        apex_tmp.unlink(missing_ok=True)
        if published:
            target.unlink(missing_ok=True)

    result = {
        "patch": "B04", "status": "isolated_stage_only",
        "apex_sha256": sha256(target),
        "mapping_input_sha256": spec["mapping_input_sha256"],
        "mapping_output_sha256": sha256(mapping),
        "inserted_typeattributes": len(missing),
        "selinux_context": LABEL.decode(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
