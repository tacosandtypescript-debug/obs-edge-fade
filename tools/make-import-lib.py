#!/usr/bin/env python3
"""Builds an import library for obs.dll from a dumpbin /exports listing.

The prebuilt OBS Studio installation does not ship obs.lib, so a local build
without the full libobs source tree links against the exports of the installed
binary instead.

Usage:
    python tools/make-import-lib.py <dumpbin-exports.txt> <out.lib> <out.def>
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

EXPORT_RE = re.compile(r"^\s+\d+\s+[0-9A-Fa-f]+\s+[0-9A-Fa-f]{8}\s+(\S+)")


def parse_exports(path: Path) -> list[str]:
    names: list[str] = []
    for line in path.read_text(errors="ignore").splitlines():
        match = EXPORT_RE.match(line)
        if not match:
            continue
        name = match.group(1)
        # "name = name" for plain C exports, "name = decorated" otherwise.
        if "=" in name:
            name = name.split("=")[0]
        names.append(name)
    # De-duplicate while keeping order.
    return list(dict.fromkeys(names))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exports")
    parser.add_argument("lib")
    parser.add_argument("def_file")
    args = parser.parse_args()

    names = parse_exports(Path(args.exports))
    if len(names) < 100:
        raise SystemExit(f"only {len(names)} exports parsed from {args.exports}")

    Path(args.def_file).write_text(
        "LIBRARY obs.dll\nEXPORTS\n" + "".join(f"    {n}\n" for n in names),
        encoding="ascii",
    )
    print(f"{args.def_file}: {len(names)} exports")

    result = subprocess.run(
        ["lib", "/nologo", f"/def:{args.def_file}", f"/out:{args.lib}", "/machine:x64"],
        capture_output=True,
        text=True,
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip())
        return result.returncode

    print(f"{args.lib}: created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
