#!/usr/bin/env python3

import os
import shutil
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: scrub-rust-target.py TARGET_DIR NAME [NAME ...]", file=sys.stderr)
        return 2

    root = Path(sys.argv[1])
    names = tuple(name.casefold() for name in sys.argv[2:])
    if not root.is_dir():
        return 0

    removed = 0
    for current, directories, files in os.walk(root, topdown=False):
        current_path = Path(current)
        for file_name in files:
            if any(name in file_name.casefold() for name in names):
                (current_path / file_name).unlink(missing_ok=True)
                removed += 1
        for directory_name in directories:
            if any(name in directory_name.casefold() for name in names):
                shutil.rmtree(current_path / directory_name, ignore_errors=True)
                removed += 1

    print(f"removed {removed} first-party cache entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
