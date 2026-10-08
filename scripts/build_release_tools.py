#!/usr/bin/env python3
"""Compile the release's two native installer helpers with the reviewed NDK."""
import argparse,hashlib,json,subprocess,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ndk',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('Fresh output required')
 cc=a.ndk/'toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang'
 report=json.loads((ROOT/'release/tools-build.json').read_text())
 if hashlib.sha256(cc.read_bytes()).hexdigest()!=report['compiler_sha256']:raise ValueError('Use pinned NDK 27.3.13750724 macOS compiler for byte-identical tools')
 for rel,expected in report['source_sha256'].items():
  if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=expected:raise ValueError('Changed source '+rel)
 a.out.mkdir(parents=True)
 for name,rel in {'mainline-guard':'device/s6/native/mainline_reinstall_guard_a99.c','fscrypt-readonly-probe':'device/s6/native/metadata_fscrypt_probe_a82.c'}.items():
  dst=a.out/name;subprocess.run([str(cc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-static','-fno-emulated-tls',str(ROOT/rel),'-o',str(dst)],check=True)
  raw=dst.read_bytes()
  if struct.unpack_from('<H',raw,18)[0]!=183 or hashlib.sha256(raw).hexdigest()!=report['sha256'][name]:raise ValueError('Nonidentical helper '+name)
  print(name,hashlib.sha256(raw).hexdigest())
if __name__=='__main__':main()
