#!/usr/bin/env python3
"""Prepare a minimal T860 camera topology edit on the exact X710 XML.

This patch intentionally does not import old One UI 7/8 XML wholesale. A new
donor hash or altered tag makes it stop for review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--values", type=Path, default=Path(__file__).resolve().parents[1]
                        / "device/s6/camera_feature_values.json")
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        parser.error("output must be new and different from input")
    values = json.loads(args.values.read_text())
    before = args.input.read_bytes()
    if sha(before) != values["source_sha256"]:
        raise ValueError("camera XML hash differs from reviewed donor")
    text = before.decode("utf-8")
    ET.fromstring(text)
    for item in values["replacements"]:
        name, attr = item["name"], item["attribute"]
        pattern = re.compile(rf'<local\s+name="{re.escape(name)}"[^>]*?/>')
        matches = list(pattern.finditer(text))
        if len(matches) != 1:
            raise ValueError(f"{name}: expected exactly one tag, got {len(matches)}")
        tag = matches[0].group()
        old = f'{attr}="{item["from"]}"'
        if tag.count(old) != 1:
            raise ValueError(f"{name}: expected attribute {old!r} exactly once")
        new_tag = tag.replace(old, f'{attr}="{item["to"]}"', 1)
        text = text[:matches[0].start()] + new_tag + text[matches[0].end():]

    lines = []
    for item in values["insertions"]:
        name = item["name"]
        if f'name="{name}"' in text:
            raise ValueError(f"{name}: donor already declares this tag")
        lines.append(f'    <local name="{name}" value="{item["value"]}"/>')
    wide = "    <!-- T860 logical ultrawide ID 2; HAL physical ID 50 -->\n" + "\n".join(lines) + "\n\n"
    anchor = "    <!-- Zoom features -->"
    if text.count(anchor) != 1:
        raise ValueError("camera XML zoom anchor is not unique")
    text = text.replace(anchor, wide + anchor, 1)

    root = ET.fromstring(text)
    names = [x.attrib["name"] for x in root.findall("local")]
    for item in values["replacements"] + values["insertions"]:
        if names.count(item["name"]) != 1:
            raise ValueError(f"{item['name']}: duplicate/missing after patch")
    after = text.encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(after)
    print(f"input_sha256={sha(before)}")
    print(f"output_sha256={sha(after)}")
    print(f"replacements={len(values['replacements'])} insertions={len(values['insertions'])}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"camera feature patch rejected: {exc}", file=sys.stderr)
        raise SystemExit(1)
