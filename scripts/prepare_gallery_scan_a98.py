#!/usr/bin/env python3
"""Prepare a pinned, reversible capability correction; never write to the device."""
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = 'SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO'
TOKEN = 'smart_scan.samsung.v2'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def prepare(data, spec):
    if len(data) != spec['source_size'] or sha(data) != spec['source_sha256']:
        raise ValueError('Unreviewed feature source; inspect it before preparing a new profile')
    tree = ET.fromstring(data)
    nodes = tree.findall(KEY)
    if len(nodes) != 1 or nodes[0].text.split(',').count(TOKEN) != 1:
        raise ValueError('Expected exactly one capability token in one XML node')
    pat = rb'(<'+KEY.encode()+rb'>)([^<]*)(</'+KEY.encode()+rb'>)'
    matches = list(re.finditer(pat, data))
    if len(matches) != 1:
        raise ValueError('Unique plain XML node required')
    m = matches[0]
    tokens = m.group(2).split(b',')
    corrected = b','.join(t for t in tokens if t != TOKEN.encode())
    result = data[:m.start(2)] + corrected + data[m.end(2):]
    final = ET.fromstring(result)
    if [n.tag for n in tree] != [n.tag for n in final]:
        raise ValueError('Node topology changed')
    for before, after in zip(tree, final):
        if before.tag != KEY and ET.tostring(before) != ET.tostring(after):
            raise ValueError('Other feature changed')
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    spec = json.loads((ROOT/'device/s6/gallery-scan-ui85-a98.json').read_text())
    if a.source.is_symlink() or a.out.exists() or not a.out.resolve().is_relative_to(ROOT/'out/patch-probes'):
        raise ValueError('Regular source and fresh scoped output required')
    original = a.source.read_bytes()
    candidate = prepare(original, spec)
    a.out.mkdir(parents=True)
    (a.out/'original-floating_feature.xml').write_bytes(original)
    (a.out/'floating_feature.xml').write_bytes(candidate)
    report = {'id': spec['id'], 'source_sha256': sha(original), 'candidate_sha256': sha(candidate),
              'source_size': len(original), 'candidate_size': len(candidate), 'removed_token': TOKEN,
              'file': 'system/etc/floating_feature.xml', 'reason': spec['reason'],
              'gallery_apk_sha256': spec['gallery_apk_sha256'], 'smartscan_sha256': spec['smartscan_sha256'],
              'generator_sha256': sha(Path(__file__).read_bytes()), 'status': 'PREPARED_NOT_DEPLOYED',
              'limitation': 'Document edge detection/rectification remains unavailable; OCR must be tested separately'}
    (a.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
