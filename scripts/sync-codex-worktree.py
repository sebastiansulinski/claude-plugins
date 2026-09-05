#!/usr/bin/env python3
"""Synchronize the self-contained Codex runtime with the canonical Claude runtime."""

import argparse
from pathlib import Path
import shutil
import stat
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report drift without writing files.")
    arguments = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    source = repository / "worktree/scripts/worktree.sh"
    destination = repository / "plugins/worktree/scripts/worktree.sh"

    if not source.is_file() or source.is_symlink():
        print(f"Canonical runtime is missing or is a symlink: {source}", file=sys.stderr)
        return 1
    if destination.is_symlink():
        print(f"Packaged runtime must not be a symlink: {destination}", file=sys.stderr)
        return 1

    source_mode = stat.S_IMODE(source.stat().st_mode)
    matches = (
        destination.is_file()
        and destination.read_bytes() == source.read_bytes()
        and stat.S_IMODE(destination.stat().st_mode) == source_mode
    )
    if matches:
        print("Codex worktree runtime is synchronized.")
        return 0
    if arguments.check:
        print("Codex worktree runtime is missing or stale; run scripts/sync-codex-worktree.py.", file=sys.stderr)
        return 1

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(source_mode)
    print("Synchronized plugins/worktree/scripts/worktree.sh.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
