#!/usr/bin/env python3
"""Apply reviewed T860 XML value substitutions to an X710 floating feature file.

The donor is the input. The output must be a new staging file. A changed donor
value or XML structure is a hard stop so this cannot silently patch One UI 9.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="pristine X710 XML")
    parser.add_argument("output", type=Path, help="new staging XML")
    parser.add_argument(
        "--values",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "device/s6/floating_feature_values.json",
    )
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        parser.error("output must be a new path distinct from input")

    manifest = json.loads(args.values.read_text(encoding="utf-8"))
    before = args.input.read_bytes()
    if digest(before) != manifest["source_sha256"]:
        raise ValueError(
            f"source SHA-256 differs from reviewed {manifest['source_build']} XML"
        )
    text = before.decode("utf-8")
    ET.fromstring(text)
    for tag, change in manifest["changes"].items():
        pattern = re.compile(rf"(<{re.escape(tag)}>)([^<]*)(</{re.escape(tag)}>)")
        matches = list(pattern.finditer(text))
        if len(matches) != 1:
            raise ValueError(f"{tag}: expected one XML element, found {len(matches)}")
        actual = matches[0].group(2)
        if actual != change["from"]:
            raise ValueError(
                f"{tag}: donor value {actual!r} differs from reviewed {change['from']!r}"
            )
        text = pattern.sub(lambda match: match.group(1) + change["to"] + match.group(3), text, count=1)

    ET.fromstring(text)
    after = text.encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(after)
    print(f"input_sha256={digest(before)}")
    print(f"output_sha256={digest(after)}")
    print(f"changed_tags={len(manifest['changes'])}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"floating feature patch rejected: {exc}", file=sys.stderr)
        raise SystemExit(1)
